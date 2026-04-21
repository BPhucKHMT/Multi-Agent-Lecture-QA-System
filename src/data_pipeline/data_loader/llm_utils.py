import os
from typing import Optional, List, Dict
from dotenv import load_dotenv

# Load env variables
load_dotenv()

def call_llm_api(text: str, system_prompt: str, history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
    """
    Hàm core gọi LLM qua LangChain để xử lý văn bản.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return text

    auth_token = os.getenv("myAPIKey", "")
    if not auth_token:
        raise ValueError("Thiếu myAPIKey trong môi trường để gọi LLM API.")

    from langchain_openai import ChatOpenAI

    model_name = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    llm = ChatOpenAI(
        api_key=auth_token,
        model=model_name,
        temperature=0.1,
    )

    messages = [{"role": "system", "content": system_prompt}]
    for item in history or []:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant", "system"} and isinstance(content, str):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": text})

    try:
        response = llm.invoke(messages)
        content = getattr(response, "content", None)
        if isinstance(content, str):
            return content.strip()
        return None

    except Exception as e:
        print(f"⚠️ Lỗi thực thi LLM API: {e}")
        return None

def correct_transcript_spelling(text: str) -> Optional[str]:
    """Chuyên dụng cho sửa lỗi chính tả Transcript (giữ timestamp)."""
    system_prompt = (
        "Bạn là AI chuyên sửa chính tả tiếng Việt và tiếng Anh cho bài giảng Machine Learning. "
        "Hãy sửa lỗi chính tả và thuật ngữ kĩ thuật cho đoạn transcript sau. "
        "YÊU CẦU: Giữ nguyên TUYỆT ĐỐI các mốc thời gian (timestamp) dạng H:MM:SS - H:MM:SS. "
        "Không thêm bớt nội dung, không giải thích. Chỉ trả về văn bản đã sửa."
    )
    return call_llm_api(text, system_prompt)

def correct_ocr_text(text: str) -> Optional[str]:
    """Chuyên dụng cho sửa lỗi nhận dạng OCR từ Slide bài giảng."""
    if not text or len(text.strip()) < 5:
        return text
        
    system_prompt = (
        "Bạn là AI chuyên sửa chính tả tiếng Việt và tiếng Anh cho nội dung Slide bài giảng (OCR). "
        "Hãy sửa lỗi nhận dạng sai, khôi phục các từ bị dính hoặc thiếu dấu do OCR. "
        "Đặc biệt chú trọng các thuật ngữ Machine Learning, Deep Learning và code. "
        "Chỉ trả về đoạn văn bản đã sửa, không thêm giải thích."
    )
    history = [
        { "role": "user", "content": "Vietnam Nauonal University HCMC" },
        { "role": "assistant", "content": "Vietnam National University HCMC" }
    ]
    return call_llm_api(text, system_prompt, history=history)
