import re
import unicodedata
import json
import logging
from typing import TypedDict, List
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.generation.llm_model import get_llm
from src.rag_core.tools.sandbox import execute_python_code
from src.rag_core.agents.coding import extract_code

logger = logging.getLogger(__name__)

# --- Models cho Structured Math Output ---

class MathStepModel(BaseModel):
    title: str = Field(description="Tiêu đề của bước giải (ví dụ: 'Phân tích đa thức', 'Giải phương trình bậc 2')")
    content: str = Field(description="Nội dung chi tiết của bước giải, sử dụng LaTeX chuẩn bọc trong $...$ hoặc $$...$$")

class MathDataModel(BaseModel):
    text: str = Field(description="Toàn bộ nội dung bài giải dưới dạng Markdown hoàn chỉnh (Mục tiêu, Các bước giải, Kết luận). Đây là phần được stream cho người dùng nên cần viết chi tiết và hay.")
    goal: str = Field(description="Mô tả ngắn gọn bài toán cần giải")
    steps: List[MathStepModel] = Field(description="Danh sách các bước giải chi tiết để lưu trữ")

class MathState(TypedDict):
    query: str
    sympy_code: str
    math_result: str
    is_success: bool
    response: dict


# --- Hỗ trợ xử lý text và fallback ---

def _fallback_math_data(query: str) -> dict:
    fallback_text = f"## 🎯 Mục tiêu\nGiải bài toán: ${query}$\n\n## 📝 Các bước giải\n1. Xác định yêu cầu bài toán.\n2. Áp dụng phương pháp toán học phù hợp.\n3. Tính toán kết quả."
    return {
        "text": fallback_text,
        "goal": f"Giải bài toán: {query}",
        "steps": [
            {"title": "Xác định mục tiêu", "content": f"Yêu cầu bài toán là giải: ${query}$"},
            {"title": "Phương pháp tiếp cận", "content": "Áp dụng định lý và các công thức toán học cơ bản."},
            {"title": "Kết luận", "content": "Thực hiện tính toán chi tiết."}
        ]
    }

def _extract_json_from_llm(text: str):
    if not text: return None
    try:
        # Tìm block ```json
        match = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            return json.loads(match.group(1))
        # Quét thử JSON raw
        match = re.search(r"(\{[\s\S]*\})", text)
        if match:
             # Kiểm tra xem có đóng ngoặc chưa, nếu chưa thì thử fix nhẹ (cho streaming case)
            raw_json = match.group(1)
            return json.loads(raw_json)
    except Exception as e:
        logger.warning(f"Failed to extract JSON from math LLM output: {e}")
    return None

def _clean_verification_text(math_result: str) -> str:
    if not math_result: return "Chưa có dữ liệu kiểm chứng."
    text = unicodedata.normalize("NFC", str(math_result)).strip()
    if not text or "undefined" in text.lower():
        return "Kiểm chứng tự động chưa trả kết quả hợp lệ."
    
    # Format lại kết quả Sympy 
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:15])


# --- Các Node trong Math Graph ---

async def generate_sympy_code(state: MathState):
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template("""
Bạn là chuyên gia Sympy. 
Hãy viết DUY NHẤT mã Python Sympy để giải bài toán sau: {query}
Yêu cầu:
- Chỉ trả về block ```python ... ```.
- Không có text giải thích.
- Phải print() kết quả cuối cùng.
""")
    res = await llm.ainvoke(prompt.format(query=state.get("query", "")))
    code = extract_code(res.content)
    return {"sympy_code": code}

def verify_sympy(state: MathState):
    code = state.get("sympy_code", "")
    if not code:
        return {"is_success": False, "math_result": "Không tìm thấy mã Sympy."}
    res = execute_python_code(code)
    if res["success"]:
        return {"is_success": True, "math_result": res["stdout"]}
    else:
        return {"is_success": False, "math_result": res["stderr"]}

async def generate_derivation(state: MathState):
    query = state.get("query", "")
    math_result = state.get("math_result", "")
    is_success = state.get("is_success", False)
    
    llm = get_llm()
    parser = JsonOutputParser(pydantic_object=MathDataModel)
    
    prompt = ChatPromptTemplate.from_template("""
Bạn là giảng viên toán cao cấp tại UIT. Hãy tạo bài giải chi tiết dưới dạng JSON.
Học sinh yêu cầu: {query}
Kết quả máy tính: {math_result}

HƯỚNG DẪN:
1. 'text': PHẢI ĐẶT LÊN ĐẦU JSON. Đây là nội dung quan trọng nhất để stream cho người dùng.
   - Hãy viết như một bài viết blog/bài giải chuyên nghiệp.
   - Trình bày đẹp bằng Markdown và LaTeX ($...$ hoặc $$...$$).
   - Biến đổi các kết quả khô khan từ máy tính ({math_result}) thành các công thức toán học dễ hiểu (Vd: Eq(x, 1) -> $x = 1$).
   - Cấu trúc: ## 🎯 Mục tiêu -> ## 📝 Các bước giải chi tiết -> ## ✅ Kiểm chứng kết quả.
2. 'goal' & 'steps': Dùng để lưu trữ cấu trúc.

ĐỊNH DẠNG JSON:
{format_instructions}
""")
    
    try:
        res = await llm.ainvoke(
            prompt.format(
                query=query,
                math_result=math_result if is_success else "Hãy tự giải chi tiết.",
                format_instructions=parser.get_format_instructions()
            ),
                config={"tags": ["final_answer_json"]}
        )

        
        content = res.content if hasattr(res, "content") else str(res)
        math_data_parsed = _extract_json_from_llm(content)
        if not math_data_parsed:
            math_data = _fallback_math_data(query)
        else:
            math_data = {
                "text": math_data_parsed.get("text") or math_data_parsed.get("Text"),
                "goal": math_data_parsed.get("goal") or math_data_parsed.get("Goal") or f"Giải bài toán: {query}",
                "steps": math_data_parsed.get("steps") or math_data_parsed.get("Steps") or []
            }
            if not math_data["text"]:
                math_data["text"] = f"## 🎯 Mục tiêu: {query}\n\n" + "\n".join([f"### {s.get('title')}\n{s.get('content')}" for s in math_data["steps"]])
                
    except Exception as e:
        logger.error(f"Math Error: {e}")
        math_data = _fallback_math_data(query)

    response_data = {
        "text": math_data.get("text"),
        "video_url": [],
        "title": [],
        "filename": [],
        "start_timestamp": [],
        "end_timestamp": [],
        "confidence": [],
        "type": "math",
        "math_data": {
            "goal": math_data.get("goal"),
            "steps": math_data.get("steps"),
            "verification": {
                "status": "success" if is_success else "warning",
                "details": _clean_verification_text(math_result)
            }
        }
    }
    
    return {"response": response_data}

def build_math_subgraph():
    graph = StateGraph(MathState)
    graph.add_node("gen_sympy", generate_sympy_code)
    graph.add_node("verify", verify_sympy)
    graph.add_node("derive", generate_derivation)
    graph.add_edge(START, "gen_sympy")
    graph.add_edge("gen_sympy", "verify")
    graph.add_edge("verify", "derive")
    graph.add_edge("derive", END)
    return graph.compile()