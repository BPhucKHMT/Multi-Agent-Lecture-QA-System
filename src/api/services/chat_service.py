from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List
import json as json_lib
import os
import builtins
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from src.rag_core.lang_graph_rag import call_agent
from src.shared.config import get_path

from src.api.schemas import ChatRequest, ChatResponse


# In-memory conversation store
conversations_store: Dict[str, Dict[str, Any]] = {}
MAX_STREAM_HISTORY_MESSAGES = int(os.getenv("PUQ_MAX_STREAM_HISTORY_MESSAGES", "8"))
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}


def _safe_stream_log(message: str) -> None:
    try:
        builtins.print(message)
    except UnicodeEncodeError:
        builtins.print(
            message.encode("ascii", errors="backslashreplace").decode("ascii")
        )


def _stream_error_response(message: str) -> Dict[str, Any]:
    return {
        "text": message,
        "video_url": [],
        "title": [],
        "filename": [],
        "start_timestamp": [],
        "end_timestamp": [],
        "confidence": [],
        "type": "error",
    }


def _extract_stream_token_content(chunk: Any) -> str:
    if chunk is None:
        return ""
    if isinstance(chunk, str):
        return chunk
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    if isinstance(chunk, dict):
        dict_content = chunk.get("content")
        if isinstance(dict_content, str):
            return dict_content
    return ""


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def _normalize_video_title(stem: str) -> str:
    cleaned = re.sub(r"\.f\d+$", "", stem, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\d+\s*-\s*", "", cleaned)
    return cleaned.strip()


def _estimate_token_count_from_text(text: str) -> int:
    stripped = str(text or "")
    if not stripped:
        return 0
    return (len(stripped) + 3) // 4


@lru_cache(maxsize=1)
def _load_video_metadata_map() -> Dict[str, Dict[str, str]]:
    """Load metadata mapping from artifacts/videos/*/metadata.json."""
    videos_root = Path(get_path("videos_dir"))
    mapping: Dict[str, Dict[str, str]] = {}
    if not videos_root.exists() or not videos_root.is_dir():
        return mapping

    for metadata_file in videos_root.glob("*/metadata.json"):
        course_name = metadata_file.parent.name
        try:
            payload = json_lib.loads(metadata_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        for video in payload.get("videos", []):
            title = str(video.get("title", "")).strip()
            video_url = str(video.get("url", "")).strip()
            video_id = str(video.get("video_id", "")).strip()
            if not title:
                continue

            normalized_title = _normalize_text(_normalize_video_title(title))
            if not normalized_title:
                continue

            key = f"{course_name.lower()}::{normalized_title}"
            mapping[key] = {
                "video_url": video_url,
                "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                if video_id
                else "",
            }

    return mapping


@lru_cache(maxsize=1)
def _build_video_index() -> List[Dict[str, Any]]:
    """Tạo index video cho search/pagination, ưu tiên metadata để phản hồi nhanh."""
    videos_root = Path(get_path("videos_dir"))
    if not videos_root.exists() or not videos_root.is_dir():
        return []

    deduped: Dict[str, Dict[str, Any]] = {}

    # Fast path: đọc trực tiếp metadata.json trong artifacts/videos/*
    for metadata_file in videos_root.glob("*/metadata.json"):
        course_name = metadata_file.parent.name
        try:
            payload = json_lib.loads(metadata_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        for video in payload.get("videos", []):
            title = str(video.get("title", "")).strip()
            video_id = str(video.get("video_id", "")).strip()
            video_url = str(video.get("url", "")).strip()
            if not title:
                continue

            normalized_title = _normalize_video_title(title)
            dedupe_key = f"{course_name.lower()}::{_normalize_text(normalized_title)}"
            deduped[dedupe_key] = {
                "id": f"{course_name.lower()}::{video_id or _normalize_text(normalized_title)}",
                "video_id": video_id,
                "title": normalized_title,
                "course": course_name,
                "file_name": f"{video_id}.mp4" if video_id else normalized_title,
                "relative_path": "",
                "file_size_mb": 0.0,
                "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                if video_id
                else "",
                "video_url": video_url,
                "_search_key": _normalize_text(
                    f"{normalized_title} {course_name} {video_id}"
                ),
            }

    if deduped:
        return sorted(
            deduped.values(),
            key=lambda item: (item["course"].lower(), item["title"].lower()),
        )

    # Fallback path: quét file local nếu metadata không có.
    metadata_map = _load_video_metadata_map()

    for file_path in videos_root.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        relative_path = file_path.relative_to(videos_root).as_posix()
        course = relative_path.split("/")[0] if "/" in relative_path else "General"
        normalized_title = _normalize_video_title(file_path.stem)
        dedupe_key = f"{course.lower()}::{normalized_title.lower()}"
        metadata_key = f"{course.lower()}::{_normalize_text(normalized_title)}"
        metadata = metadata_map.get(metadata_key, {})
        file_size = file_path.stat().st_size

        current = deduped.get(dedupe_key)
        if current is None or file_size > current["_size_bytes"]:
            deduped[dedupe_key] = {
                "id": dedupe_key,
                "video_id": "",
                "title": normalized_title,
                "course": course,
                "file_name": file_path.name,
                "relative_path": relative_path,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "thumbnail_url": metadata.get("thumbnail_url", ""),
                "video_url": metadata.get("video_url", ""),
                "_size_bytes": file_size,
                "_search_key": _normalize_text(
                    f"{normalized_title} {course} {file_path.name}"
                ),
            }

    return sorted(
        deduped.values(),
        key=lambda item: (item["course"].lower(), item["title"].lower()),
    )


def list_local_videos(
    query: str = "", page: int = 1, page_size: int = 20
) -> Dict[str, Any]:
    """Trả danh sách video local từ artifacts/videos cho Summary Hub (search + pagination)."""
    all_videos = _build_video_index()
    if not all_videos:
        return {
            "total": 0,
            "page": 1,
            "page_size": page_size,
            "total_pages": 0,
            "query": query,
            "videos": [],
        }

    query_text = _normalize_text(query)
    if query_text:
        all_videos = [
            item for item in all_videos if query_text in item.get("_search_key", "")
        ]

    total = len(all_videos)
    safe_page_size = max(1, min(page_size, 100))
    safe_page = max(1, page)
    total_pages = (total + safe_page_size - 1) // safe_page_size if total > 0 else 0
    if total_pages > 0 and safe_page > total_pages:
        safe_page = total_pages

    start_index = (safe_page - 1) * safe_page_size
    end_index = start_index + safe_page_size
    page_items = all_videos[start_index:end_index]
    videos = [
        {key: value for key, value in item.items() if not key.startswith("_")}
        for item in page_items
    ]

    return {
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "total_pages": total_pages,
        "query": query,
        "videos": videos,
    }


@lru_cache(maxsize=1)
def _build_transcript_index() -> Dict[str, str]:
    """Map video_id -> transcript path từ artifacts/data."""
    data_root = Path(get_path("data_dir"))
    index: Dict[str, str] = {}
    if not data_root.exists() or not data_root.is_dir():
        return index

    for course_dir in data_root.iterdir():
        if not course_dir.is_dir():
            continue
        for sub_dir_name in ("processed_transcripts", "transcripts"):
            transcript_dir = course_dir / sub_dir_name
            if not transcript_dir.exists() or not transcript_dir.is_dir():
                continue
            for transcript_file in transcript_dir.glob("*.txt"):
                video_id = transcript_file.stem
                # Ưu tiên processed_transcripts nếu cùng video_id
                if video_id not in index or sub_dir_name == "processed_transcripts":
                    index[video_id] = str(transcript_file)

    return index


def process_chat(request: ChatRequest) -> ChatResponse:
    """Xử lý hội thoại, gọi RAG và lưu lịch sử trong bộ nhớ."""
    doc = conversations_store.get(request.conversation_id)
    if not doc:
        now = datetime.now().isoformat()
        doc = {
            "conversation_id": request.conversation_id,
            "title": "Cuộc trò chuyện mới",
            "messages": [{"role": "assistant", "content": "Bạn muốn hỏi gì hôm nay?"}],
            "created_at": now,
            "updated_at": now,
        }
        conversations_store[request.conversation_id] = doc

    messages = doc.get("messages", [])
    messages.append({"role": "user", "content": request.user_message})

    chat_history = []
    for message in messages:
        content = message["content"]
        # Đảm bảo tương thích với kết quả trả về đa dạng của mạng Supervisor
        if isinstance(content, dict):
            content = content.get("text", str(content))
        chat_history.append({"role": message["role"], "content": content})

    response = call_agent(chat_history)

    messages.append({"role": "assistant", "content": response})

    title = doc["title"]
    if title == "Cuộc trò chuyện mới" and len(messages) > 1:
        first_user_msg = next(
            (msg["content"] for msg in messages if msg["role"] == "user"), ""
        )
        if isinstance(first_user_msg, str):
            title = first_user_msg[:35] + ("..." if len(first_user_msg) > 35 else "")

    now = datetime.now().isoformat()
    doc["title"] = title
    doc["messages"] = messages
    doc["updated_at"] = now
    conversations_store[request.conversation_id] = doc

    return ChatResponse(
        conversation_id=request.conversation_id,
        response=response,
        updated_at=now,
    )


class JsonStreamCleaner:
    """Hỗ trợ bóc tách nội dung text sạch từ một luồng JSON dở dang."""

    def __init__(self):
        self.buffer = ""
        self.is_json = False
        self.is_plain_text = False
        self.target_keys = ['"text"', '"goal"', '"content"']
        self.capture_start_idx = -1
        self.raw_cursor = 0
        self.pending_escape = ""
        self.capture_done = False

    def process_token(self, token: str) -> str:
        if self.is_plain_text:
            return token
        if self.capture_done:
            return ""

        self.buffer += token

        # 1. Tìm điểm bắt đầu JSON
        if not self.is_json:
            start_bracket_idx = self.buffer.find("{")
            if start_bracket_idx != -1:
                self.is_json = True
                self.buffer = self.buffer[start_bracket_idx:]
            else:
                # Nếu không phải JSON, trả lại token như là plain text
                self.is_plain_text = True
                return token

        # 2. Tìm key mục tiêu (text, content, goal)
        if self.capture_start_idx == -1:
            for key in self.target_keys:
                key_idx = self.buffer.find(key)
                if key_idx != -1:
                    colon_idx = self.buffer.find(":", key_idx + len(key))
                    if colon_idx != -1:
                        quote_idx = self.buffer.find('"', colon_idx + 1)
                        if quote_idx != -1:
                            self.capture_start_idx = quote_idx + 1
                            break
            if self.capture_start_idx == -1:
                return ""

        # 3. Trích xuất và giải mã nội dung
        extracted_raw = self.buffer[self.capture_start_idx :]
        return self._decode_text_delta(extracted_raw)

    def _decode_text_delta(self, extracted_raw: str) -> str:
        """Giải mã từng phần value JSON string mà không chờ object hoàn chỉnh."""
        out = []
        i = self.raw_cursor

        while i < len(extracted_raw):
            char = extracted_raw[i]

            if self.pending_escape:
                self.pending_escape += char
                if self.pending_escape.startswith("\\u"):
                    if len(self.pending_escape) < 6:
                        i += 1
                        continue
                    try:
                        out.append(chr(int(self.pending_escape[2:6], 16)))
                    except ValueError:
                        out.append(self.pending_escape)
                    self.pending_escape = ""
                    i += 1
                    continue

                escape_char = self.pending_escape[1]
                escape_map = {
                    '"': '"',
                    "\\": "\\",
                    "/": "/",
                    "b": "\b",
                    "f": "\f",
                    "n": "\n",
                    "r": "\r",
                    "t": "\t",
                }
                out.append(escape_map.get(escape_char, self.pending_escape))
                self.pending_escape = ""
                i += 1
                continue

            if char == "\\":
                self.pending_escape = "\\"
                i += 1
                continue
            if char == '"':
                self.capture_done = True
                i += 1
                break

            out.append(char)
            i += 1

        self.raw_cursor = i
        return "".join(out)


def _extract_stream_context(event: dict) -> list:
    """Trích xuất danh sách video từ event data nếu có."""
    data = event.get("data", {})
    output = data.get("output")
    if not output:
        return []

    # Nếu là output của lambda get_context trong OfflineRag
    if isinstance(output, str) and output.startswith("["):
        try:
            data = json_lib.loads(output)
            # Chỉ chấp nhận nếu là danh sách các object có page_content (đặc thù của context docs)
            if (
                isinstance(data, list)
                and len(data) > 0
                and isinstance(data[0], dict)
                and ("page_content" in data[0] or "content" in data[0])
            ):
                return data
            return []
        except:
            return []
    return []


async def generate_stream(
    conversation_id: str, request_messages: list, user_message: str
) -> AsyncGenerator[str, None]:
    """Yield SSE chunks: token realtime + metadata cuối + [DONE]."""
    import time
    from src.rag_core.lang_graph_rag import workflow
    from langchain_core.messages import HumanMessage, AIMessage

    # Ensure conversation exists in store
    doc = conversations_store.get(conversation_id)
    if not doc:
        now = datetime.now().isoformat()
        doc = {
            "conversation_id": conversation_id,
            "title": "Cuộc trò chuyện mới",
            "messages": [{"role": "assistant", "content": "Bạn muốn hỏi gì hôm nay?"}],
            "created_at": now,
            "updated_at": now,
        }
        conversations_store[conversation_id] = doc

    # Add user message to doc (history)
    messages = doc.get("messages", [])
    messages.append({"role": "user", "content": user_message})

    history_slice = (
        request_messages[-MAX_STREAM_HISTORY_MESSAGES:]
        if MAX_STREAM_HISTORY_MESSAGES > 0
        else request_messages
    )

    # Build langchain messages từ lịch sử hội thoại
    langchain_messages = []
    for msg in history_slice:
        content = msg["content"]
        if isinstance(content, dict):
            content = content.get("text", str(content))
        if msg["role"] == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif msg["role"] == "assistant":
            langchain_messages.append(AIMessage(content=content))

    # Append tin nhắn mới nhất của user
    langchain_messages.append(HumanMessage(content=user_message))

    initial_state = {"messages": langchain_messages}

    response = {
        "text": "Lỗi: Không nhận được phản hồi từ AI.",
        "video_url": [],
        "title": [],
        "filename": [],
        "start_timestamp": [],
        "end_timestamp": [],
        "confidence": [],
        "type": "error",
    }

    stream_start_time = time.time()
    total_input_tokens = 0
    total_output_tokens = 0
    node_token_usage: Dict[str, Dict[str, int]] = {}

    _safe_stream_log(
        f"[stream] START user_message={user_message[:120]!r} "
        f"history_total={len(request_messages)} history_used={len(history_slice)}"
    )

    cleaner = JsonStreamCleaner()

    STATUS_MAPPING = {
        "supervisor": "🤔 Đang phân tích yêu cầu của bạn...",
        "tutor": "📚 Đang truy hồi tri thức từ bài giảng...",
        "quiz": "📝 Đang soạn thảo câu hỏi trắc nghiệm...",
        "coding": "💻 Đang xử lý logic lập trình...",
        "math": "🔢 Đang thực hiện tính toán và chứng minh...",
        "direct": "💬 Đang chuẩn bị câu trả lời...",
    }

    try:
        # Phase 1: Stream từng text token từ LLM
        async for event in workflow.astream_events(initial_state, version="v2"):
            node_name = event.get("metadata", {}).get("langgraph_node", "")
            event_type = event.get("event")

            # Gửi trạng thái node nếu có mapping
            if event_type == "on_chain_start" and node_name in STATUS_MAPPING:
                yield f"data: {json_lib.dumps({'type': 'status', 'status': STATUS_MAPPING[node_name]})}\n\n"

            # Gửi Context sớm nếu bắt được kết quả từ retriever/lambda (chỉ bước retrieve_context)
            if event_type == "on_chain_end":
                # Chỉ lấy dữ liệu từ bước được định danh là retrieve_context
                if event.get("name") == "retrieve_context":
                    context_docs = _extract_stream_context(event)
                    if context_docs:
                        yield f"data: {json_lib.dumps({'type': 'context', 'docs': context_docs})}\n\n"

            if event_type == "on_chat_model_stream":
                node_name = event.get("metadata", {}).get("langgraph_node", "")
                allowed_nodes = [
                    "tutor",
                    "math",
                    "quiz",
                    "coding",
                    "direct",
                    "derive",
                    "generate",
                    "quiz_gen",
                ]

                tags = event.get("tags", [])
                content = event["data"]["chunk"].content

                if node_name not in allowed_nodes:
                    continue

                if "final_answer" not in tags and "final_answer_json" not in tags:
                    continue

                token_text = _extract_stream_token_content(
                    event.get("data", {}).get("chunk")
                )
                if token_text:
                    clean_token = cleaner.process_token(token_text)
                    if clean_token:
                        yield f"data: {json_lib.dumps({'type': 'token', 'content': clean_token})}\n\n"
                continue
            elif event_type == "on_chat_model_end":
                try:
                    output = event.get("data", {}).get("output")
                    if (
                        output
                        and hasattr(output, "usage_metadata")
                        and output.usage_metadata
                    ):
                        input_tokens = output.usage_metadata.get("input_tokens", 0)
                        output_tokens = output.usage_metadata.get("output_tokens", 0)
                        total_input_tokens += input_tokens
                        total_output_tokens += output_tokens
                        bucket = node_token_usage.setdefault(
                            node_name or "unknown", {"input": 0, "output": 0}
                        )
                        bucket["input"] += input_tokens
                        bucket["output"] += output_tokens
                except:
                    pass

            # Bắt kết quả cuối cùng của node xử lý (Chỉ log của các node thực thi chính)
            if event_type == "on_chain_end" and node_name in [
                "tutor",
                "math",
                "quiz",
                "coding",
                "direct",
            ]:
                output = event.get("data", {}).get("output")
                if isinstance(output, dict) and "response" in output:
                    response = output.get("response")
                    _safe_stream_log(
                        f"[stream] NODE_END node={node_name} response_preview="
                    )
                    _safe_stream_log(
                        (
                            response.get("text", "")[:120]
                            if isinstance(response, dict)
                            else str(response)[:120]
                        )
                    )

        if not isinstance(response, dict) or not str(response.get("text", "")).strip():
            _safe_stream_log(
                f"[stream] WARN empty/invalid response payload: {response!r}"
            )
            response = _stream_error_response(
                "Lỗi streaming: Không nhận được metadata phản hồi cuối."
            )
    except Exception as error:
        _safe_stream_log(f"[stream] ERROR {error!r}")
        print(error)
        response = _stream_error_response(f"Lỗi streaming: {str(error)}")

    stream_elapsed = time.time() - stream_start_time
    _safe_stream_log(
        f"[PERFORMANCE LOG] [STREAM] Tổng thời gian AI Workflow: {stream_elapsed:.2f}s | "
        f"Tổng Token Input: {total_input_tokens} | "
        f"Tổng Token Output: {total_output_tokens}"
    )
    _safe_stream_log(
        f"[TOKEN METRICS] mode=stream input={total_input_tokens} "
        f"output={total_output_tokens} total={total_input_tokens + total_output_tokens}"
    )
    visible_text = (
        response.get("text", "") if isinstance(response, dict) else str(response or "")
    )
    visible_chars = len(str(visible_text or ""))
    visible_tokens_estimate = _estimate_token_count_from_text(visible_text)
    node_breakdown = (
        ", ".join(
            f"{node}:in={usage['input']},out={usage['output']}"
            for node, usage in sorted(node_token_usage.items())
        )
        or "none"
    )
    _safe_stream_log(
        f"[TOKEN BREAKDOWN] per_node={node_breakdown} "
        f"visible_chars={visible_chars} visible_tokens_estimate={visible_tokens_estimate}"
    )
    # Save assistant message to store
    messages.append({"role": "assistant", "content": response})

    title = doc["title"]
    if title == "Cuộc trò chuyện mới" and len(messages) > 1:
        first_user_msg = next(
            (msg["content"] for msg in messages if msg["role"] == "user"), ""
        )
        if isinstance(first_user_msg, str):
            title = first_user_msg[:35] + ("..." if len(first_user_msg) > 35 else "")

    now = datetime.now().isoformat()
    doc["title"] = title
    doc["messages"] = messages
    doc["updated_at"] = now
    conversations_store[conversation_id] = doc

    yield f"data: {json_lib.dumps({'type': 'metadata', 'conversation_id': conversation_id, 'response': response})}\n\n"
    yield "data: [DONE]\n\n"
