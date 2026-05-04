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

async def node_direct_answer(state: State):
    """Sinh response trực tiếp và chuẩn hóa schema không citation."""
    messages = state.get("messages", [])
    args = _extract_tool_args_from_state(state, "AskGeneral")
    query = args.get("query", "")
    
    if not query and messages:
        last_message = messages[-1]
        if isinstance(last_message, HumanMessage):
            query = last_message.content

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
