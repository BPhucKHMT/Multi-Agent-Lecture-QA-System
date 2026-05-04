"""Tutor Agent cho câu hỏi cần truy hồi bài giảng.

Module này là worker RAG chính trong LangGraph workflow. Agent nhận query từ
Supervisor, lấy context qua RAG core, gọi answer chain để sinh JSON response và
backfill metadata citation nếu LLM trả thiếu trường nguồn.

Response của agent phải giữ contract chung: `text`, các mảng citation
`video_url/title/timestamp`, `confidence` và `type` để backend/frontend xử lý
thống nhất.
"""

import json
import logging
import re
import time

from src.rag_core import resource_manager
from src.rag_core.state import State


logger = logging.getLogger(__name__)


def _build_tutor_error_response(text: str) -> dict:
    """Tạo response lỗi theo cùng schema với response RAG thành công."""
    return {
        "text": text,
        "video_url": [],
        "title": [],
        "filename": [],
        "start_timestamp": [],
        "end_timestamp": [],
        "confidence": [],
        "type": "error",
    }


def _extract_tutor_json_payload(raw):
    """Parse JSON từ output LLM, kể cả khi model bọc trong markdown fence."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    fenced = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            pass

    obj_match = re.search(r"(\{[\s\S]*\})", text)
    if obj_match:
        try:
            parsed = json.loads(obj_match.group(1))
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    return None


def _extract_cited_indices(text: str) -> list[int]:
    """Lấy danh sách chỉ số citation `[n]` đang xuất hiện trong câu trả lời."""
    return sorted({int(match) for match in re.findall(r"\[(\d+)\]", text or "")})


def _ensure_list_slot(data: dict, key: str, index: int, value: str) -> None:
    current = data.get(key)
    if not isinstance(current, list):
        current = []
    while len(current) <= index:
        current.append("")
    if not current[index] and value:
        current[index] = value
    data[key] = current


def _sync_citation_metadata_from_context(data: dict, context: str) -> dict:
    """Backfill metadata cho citation [n] từ context docs nếu LLM trả thiếu."""
    if not isinstance(data, dict):
        return data

    try:
        docs = json.loads(context) if isinstance(context, str) else []
    except Exception:
        return data

    if not isinstance(docs, list):
        return data

    for index in _extract_cited_indices(str(data.get("text", ""))):
        if index >= len(docs) or not isinstance(docs[index], dict):
            continue
        doc = docs[index]
        _ensure_list_slot(data, "video_url", index, str(doc.get("video_url", "")))
        _ensure_list_slot(data, "title", index, str(doc.get("title", "")))
        _ensure_list_slot(data, "filename", index, str(doc.get("filename", "")))
        _ensure_list_slot(
            data, "start_timestamp", index, str(doc.get("start_timestamp", ""))
        )
        _ensure_list_slot(
            data, "end_timestamp", index, str(doc.get("end_timestamp", ""))
        )
        _ensure_list_slot(data, "confidence", index, "medium")

    return data


def get_rag_chain():
    """Trả answer chain hiện tại để giữ tương thích với call site cũ."""
    return resource_manager.get_tutor_chain()


async def node_tutor(state: State):
    """Chạy Tutor node: lấy query, retrieval context, sinh answer và chuẩn hóa citation."""
    messages = state.get("messages", [])
    if not messages:
        print(f"Nội dung người dùng gửi {messages}")
        return {"response": {}}

    # Format chat history cho prompt
    history_str = ""
    for m in messages[:-1]:
        role = "User" if m.type == "human" else "Assistant"
        history_str += f"{role}: {m.content}\n"

    last_message = messages[-1]
    query = ""

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call["name"] in ["AskTutor", "Retrieve"]:
                query = tool_call["args"].get("query", "")
                break

    if not query:
        for m in reversed(messages):
            if m.type == "human":
                query = m.content
                break
        if not query:
            query = last_message.content

    try:
        # BƯỚC 1: RETRIEVAL (Có truyền history_str để rewrite query)
        rag_core = resource_manager.get_rag_core()
        # In ra màn hình console câu query
        print(f"Query to RAG: {query}")
        
        from langchain_core.runnables import RunnableLambda
        async def fetch_context(params: dict) -> str:
            return await params["rag_core"].get_context(params["query"], chat_history=params["history_str"])
            
        context_chain = RunnableLambda(fetch_context).with_config(run_name="retrieve_context")
        context_start = time.perf_counter()
        context = await context_chain.ainvoke({"rag_core": rag_core, "query": query, "history_str": history_str})
        context_elapsed = time.perf_counter() - context_start
        logger.info(
            "[TUTOR_TIMING] context_chain=%.2fs context_chars=%d",
            context_elapsed,
            len(context),
        )

        # BƯỚC 2: GENERATION (Có truyền history_str vào prompt cuối)
        answer_chain = rag_core.get_answer_chain()
        generation_start = time.perf_counter()
        rag_result = await answer_chain.ainvoke(
            {"context": context, "question": query, "chat_history": history_str}
        )
        generation_elapsed = time.perf_counter() - generation_start
        logger.info("[TUTOR_TIMING] answer_generation=%.2fs", generation_elapsed)

        raw_content = (
            rag_result.content if hasattr(rag_result, "content") else str(rag_result)
        )
        repaired = _extract_tutor_json_payload(raw_content)

        if not repaired:
            if not raw_content.strip():
                return {
                    "response": _build_tutor_error_response(
                        "Mô hình trả về output rỗng."
                    )
                }
            return {"response": _build_tutor_error_response("Không parse được JSON.")}

        data = repaired
        data = _sync_citation_metadata_from_context(data, context)
        data["type"] = "rag"
        return {"response": data}

    except Exception as e:
        return {"response": _build_tutor_error_response(f"Lỗi: {e}")}
