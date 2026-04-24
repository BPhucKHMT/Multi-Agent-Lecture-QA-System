import json
import re
from src.rag_core.state import State
from src.rag_core import resource_manager


def _build_tutor_error_response(text: str) -> dict:
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


def get_rag_chain():
    return resource_manager.get_tutor_chain()

async def node_tutor(state: State):
    """
    Node Tutor chịu trách nhiệm trả lời câu hỏi bằng RAG.
    Quy trình: 1. Retrieval (ngầm) -> 2. Generation (stream)
    """
    messages = state.get("messages", [])
    if not messages:
        return {"response": {}}
        
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
        # BƯỚC 1: RETRIEVAL (Cực kỳ quan trọng: Bước này chạy ngầm, không phát sinh stream tokens)
        rag_core = resource_manager.get_rag_core()
        context = await rag_core.get_context(query)
        
        # BƯỚC 2: GENERATION (Chỉ bước này mới phát sinh stream tokens với tag final_answer)
        answer_chain = rag_core.get_answer_chain()
        rag_result = await answer_chain.ainvoke({"context": context, "question": query})
        
        raw_content = rag_result.content if hasattr(rag_result, "content") else str(rag_result)
        repaired = _extract_tutor_json_payload(raw_content)
        
        if not repaired:
            if not raw_content.strip():
                return {"response": _build_tutor_error_response("Mô hình trả về output rỗng.")}
            return {"response": _build_tutor_error_response("Không parse được JSON.")}
            
        data = repaired
        data["type"] = "rag"
        return {"response": data}
        
    except Exception as e:
        return {"response": _build_tutor_error_response(f"Lỗi: {e}")}
