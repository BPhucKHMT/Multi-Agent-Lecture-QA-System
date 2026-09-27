"""Direct Agent cho câu hỏi xã giao hoặc câu hỏi không cần truy hồi.

Agent này là nhánh nhẹ nhất của LangGraph workflow. Nó không gọi retrieval,
không tạo citation và chỉ dùng LLM để trả lời tự nhiên bằng tiếng Việt cho các
trường hợp chào hỏi, hỏi khả năng chatbot hoặc tương tác chung.
"""

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from src.generation.llm_model import get_llm
from src.rag_core.state import State
from src.rag_core.utils import _extract_tool_args_from_state

# Từ khóa liên quan đến Giao tiếp (Greeting)
CHITCHAT_PATTERNS = (
    # ===== GREETING =====
    "xin chào", "chào", "hello", "hi", "hey", "alo", "ê",
    "chào bạn", "chào bot", "hey bot", "hi bot",
    "good morning", "good afternoon", "good evening",
    "morning", "yo", "sup", "what's up", "wassup",
    "chào buổi sáng", "chào buổi chiều", "chào buổi tối",

    # ===== FAREWELL =====
    "tạm biệt", "bye", "goodbye", "see you", "see ya",
    "hẹn gặp lại", "bai", "bb", "good night",
    "tôi đi đây", "mình đi nhé", "out đây",

    # ===== THANKS =====
    "cảm ơn", "thanks", "thank you", "thank u",
    "tks", "ty", "thx",
    "cảm ơn bạn", "cảm ơn nhiều", "thank you so much",
    "ok cảm ơn", "thanks bro", "thank you bot",

    # ===== IDENTITY =====
    "bạn là ai", "mày là ai", "who are you",
    "giới thiệu bản thân", "bạn tên gì",
    "what are you", "are you human",
    "bạn là bot à", "ai tạo ra bạn",

    # ===== CAPABILITY =====
    "bạn làm được gì", "you can do what",
    "help", "giúp tôi", "có thể làm gì",
    "how can you help", "hướng dẫn",
    "tôi có thể hỏi gì", "use bạn sao",

    # ===== STATUS =====
    "bạn khỏe không", "how are you", "how are you doing",
    "ổn không", "today thế nào",
    "bạn đang làm gì", "what are you doing",
    "có rảnh không",

    # ===== FUN / JOKE =====
    "kể chuyện cười", "tell me a joke",
    "joke", "funny", "make me laugh",
    "giải trí", "chán quá", "bored",
    "có gì vui không",

    # ===== CASUAL / FILLER =====
    "ừ", "ok", "ừm", "hmm", "huh",
    "à", "ờ", "uh", "um",
    "được", "ok luôn", "fine",
    "k", "ko", "không", "no",
    "yes", "yeah", "yep",

    # ===== COMPLIMENT =====
    "bạn giỏi", "you are smart",
    "hay quá", "good answer",
    "nice one", "đỉnh", "xịn",
    "ok đấy", "tốt", "well done",

    # ===== TOXIC / NEGATIVE =====
    "ngu", "dốt", "stupid", "idiot",
    "bot ngu", "mày ngu",
    "vô dụng", "useless",
    "trash", "rác",

    # ===== META =====
    "bạn dùng model gì",
    "are you gpt",
    "bạn có dùng openai không",
    "backend là gì",
    "how you work",
    "cách bạn hoạt động",
)


async def node_direct_answer(state: State):
    """Sinh response trực tiếp và chuẩn hóa schema không citation."""
    messages = state.get("messages", [])
    args = _extract_tool_args_from_state(state, "AskGeneral")
    query = args.get("query", "")
    
    if not query and messages:
        last_message = messages[-1]
        if isinstance(last_message, HumanMessage):
            val = str(last_message.content or "").strip().lower()
            is_greeting = False
            if any(val == p for p in CHITCHAT_PATTERNS):
                is_greeting = True
            else:
                words = val.split()
                if len(words) <= 3:
                    if any(val.startswith(f"{p} ") or val.endswith(f" {p}") for p in CHITCHAT_PATTERNS):
                        is_greeting = True
            if is_greeting:
                query = last_message.content

    if not str(query or "").strip():
        return {
            "response": {
                "text": "Mình chưa nhận được nội dung rõ ràng, bạn thử diễn đạt lại giúp mình nhé.",
                "video_url": [],
                "title": [],
                "filename": [],
                "start_timestamp": [],
                "end_timestamp": [],
                "confidence": [],
                "type": "direct"
            }
        }

    # Sử dụng LLM để trả lời một cách tự nhiên
    llm_for_chat = get_llm()
    chat_prompt = ChatPromptTemplate.from_template("""
Bạn là trợ lý học tập UIT thân thiện và nhiệt tình.
Hãy trả lời câu hỏi tán gẫu hoặc chào hỏi của sinh viên một cách tự nhiên bằng tiếng Việt.
Học sinh: {query}

Lưu ý:
- Giọng văn: Gần gũi, chuyên nghiệp, súc tích.
- Nếu được hỏi bạn có thể làm gì, hãy liệt kê ngắn gọn các khả năng: Giải Toán, Hướng dẫn học qua video, Sửa lỗi lập trình và làm Trắc nghiệm.
""")
    # Sử dụng ainvoke để hỗ trợ streaming tokens thông qua astream_events
    response = await llm_for_chat.ainvoke(
        chat_prompt.format(query=query),
        config={"tags": ["final_answer"]}
    )

    text = response.content

    data = {
        "text": text,
        "video_url": [],
        "title": [],
        "filename": [],
        "start_timestamp": [],
        "end_timestamp": [],
        "confidence": [],
        "type": "direct"
    }
    return {"response": data}
