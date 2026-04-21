from pydantic import BaseModel, Field
from typing import List
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from src.generation.llm_model import get_llm
from src.rag_core.state import State
from src.rag_core import resource_manager
import json
import re

class QuizQuestion(BaseModel):
    question: str = Field(description="Nội dung câu hỏi trắc nghiệm")
    options: List[str] = Field(description="Mảng chứa đúng 4 lựa chọn (A, B, C, D) dưới dạng chuỗi")
    correct_answer: str = Field(description="Lựa chọn đúng (chỉ nội dung lựa chọn)")
    explanation: str = Field(description="Giải thích ngắn gọn bám sát nội dung trong video transcript")
    video_url: str = Field(description="URL video tương ứng với kiến thức trong câu hỏi")
    video_title: str = Field(description="Tiêu đề bài giảng chứa kiến thức này")
    timestamp: str = Field(description="Thời điểm (format HH:MM:SS) trong video nói về kiến thức này")

class QuizOutput(BaseModel):
    quizzes: List[QuizQuestion] = Field(description="Danh sách các câu trắc nghiệm")


def _extract_quiz_json_payload(raw: str):
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    fenced_match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if fenced_match:
        text = fenced_match.group(1).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    obj_match = re.search(r"(\{[\s\S]*\})", text)
    if not obj_match:
        return None

    try:
        return json.loads(obj_match.group(1))
    except Exception:
        return None

def node_quiz(state: State):
    """
    RAG-based Quiz Agent: Tìm kiếm nội dung bài giảng trước khi tạo câu hỏi.
    Đảm bảo câu hỏi bám sát kiến thức thực tế và có trích dẫn nguồn.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"response": {}}
        
    last_message = messages[-1]
    query = ""
    
    # Lấy query từ tool call hoặc message cuối
    tool_calls = state.get("tool_calls")
    if not tool_calls and hasattr(last_message, "tool_calls"):
        tool_calls = last_message.tool_calls

    if tool_calls:
        for tool_call in tool_calls:
            if tool_call.get("name") == "GenerateQuiz":
                args = tool_call.get("args", {})
                query = args.get("query", "")
                if not query:
                    topic = args.get("topic", "")
                    num_questions = args.get("num_questions")
                    difficulty = args.get("difficulty", "")
                    if topic:
                        query = f"Tạo quiz về {topic}"
                        if num_questions:
                            query += f", {num_questions} câu"
                        if difficulty:
                            query += f", độ khó {difficulty}"
                break
                
    if not query:
        for m in reversed(messages):
            if m.type == "human":
                query = m.content
                break
        if not query:
            query = last_message.content

    # BƯỚC 1: RETRIEVAL CONTEXT (dùng lazy singleton)
    retriever, reranker = resource_manager.get_quiz_resources()
    docs = retriever.get_relevant_documents(query)
    
    # Rerank để lấy 5 đoạn sát nhất
    reranked_docs = reranker.rerank(docs, query)[:5]
    
    context_list = []
    for doc in reranked_docs:
        context_list.append({
            "content": doc.page_content,
            "url": doc.metadata.get("video_url", ""),
            "title": doc.metadata.get("title", "Video bài giảng"),
            "timestamp": doc.metadata.get("start_timestamp", "")
        })
    
    context_str = json.dumps(context_list, ensure_ascii=False)

    # BƯỚC 2: GENERATION CÓ CONTEXT
    llm = get_llm()
    parser = JsonOutputParser(pydantic_object=QuizOutput)
    
    prompt = ChatPromptTemplate.from_template("""
Bạn là chuyên gia khảo thí bài giảng. Hãy dùng thông tin từ VIDEO TRANSCRIPT dưới đây để tạo một bộ câu hỏi trắc nghiệm. 

Yêu cầu:
1. SỐ LƯỢNG: Trả về ĐÚNG số câu hỏi mà người dùng yêu cầu (ví dụ: yêu cầu 1 câu thì chỉ ra 1 câu). Nếu không yêu cầu số lượng, mặc định tạo 3 câu.
2. CÂU HỎI TỰ NHIÊN: Đặt câu hỏi trực tiếp vào kiến thức. KHÔNG bắt đầu bằng các cụm từ thừa thãi như "Theo transcript", "Theo bài giảng", "Dựa vào nội dung...".
3. TRÍCH DẪN: Với mỗi câu hỏi, phải đính kèm ĐÚNG 'video_url', 'video_title' và 'timestamp' từ đoạn transcript tương ứng đã dùng làm căn cứ.
4. GIẢI THÍCH: Ngắn gọn, bám sát nội dung lời giảng nhưng vẫn đảm bảo tính sư phạm.
5. Ngôn ngữ: Tiếng Việt.

DỮ LIỆU TRANSCRIPT:
{context}

Yêu cầu cụ thể của người dùng: {query}

{format_instructions}
TRẢ VỀ JSON NGUYÊN THỦY PHẢI CHỨA OBJECT THEO FORMAT, KHÔNG DÙNG ```json.
""")

    llm_chain = prompt | llm
    chain = llm_chain | parser
    invoke_input = {
        "context": context_str,
        "query": query,
        "format_instructions": parser.get_format_instructions()
    }
    
    try:
        result = chain.invoke(invoke_input)
    except Exception as parse_error:
        try:
            raw_result = llm_chain.invoke(invoke_input)
            raw_content = raw_result.content if hasattr(raw_result, "content") else str(raw_result)
            repaired = _extract_quiz_json_payload(raw_content)
            if not repaired:
                raise ValueError("Invalid json output")
            result = QuizOutput.model_validate(repaired).model_dump()
        except Exception as fallback_error:
            data = {
                "text": f"Lỗi tạo quiz: {str(fallback_error or parse_error)}",
                "video_url": [],
                "title": [],
                "filename": [],
                "start_timestamp": [],
                "end_timestamp": [],
                "confidence": [],
                "type": "error",
            }
            return {"response": data}
    
    try:
        
        md_text = f"### 📝 Bộ câu hỏi Trắc Nghiệm dựa trên Bài Giảng:\n\n"
        urls = []
        titles = []
        timestamps = []
        
        for i, q in enumerate(result['quizzes']):
            md_text += f"**Câu {i+1}:** {q['question']}\n\n"
            for z, opt in enumerate(q['options']):
                md_text += f"- {opt}\n"
            
            # Citation cho mỗi câu hỏi
            display_title = q.get('video_title') or "bài giảng"
            md_text += f"\n> 📖 *Gợi ý: Xem lại [{display_title} tại {q['timestamp']}]({q['video_url']}&t={q['timestamp'].replace(':', 'm', 1).replace(':', 's') if ':' in q['timestamp'] else q['timestamp']})*\n"
            
            md_text += f"\n**Đáp án đúng:** {q['correct_answer']}\n\n"
            md_text += f"**Giải thích:** {q['explanation']}\n\n---\n"
            
            # Thu thập metadata để Frontend render danh sách nguồn bên dưới (nếu cần)
            if q['video_url'] not in urls:
                urls.append(q['video_url'])
                titles.append(q.get('video_title', f"Video bài giảng cho câu {i+1}"))
                timestamps.append(q['timestamp'])
            
        data = {
            "text": md_text,
            "video_url": urls,
            "title": titles,
            "filename": ["quiz_source"] * len(urls),
            "start_timestamp": timestamps,
            "end_timestamp": timestamps,
            "confidence": ["high"] * len(urls),
            "type": "quiz",
            "quizzes": result['quizzes']
        }
    except Exception as e:
        data = {
             "text": f"Lỗi tạo quiz: {str(e)}",
             "video_url": [], "title": [], "filename": [],
             "start_timestamp": [], "end_timestamp": [], "confidence": [],
             "type": "error"
        }
    
    return {"response": data}
