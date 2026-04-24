from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables import RunnableLambda
from typing import List
import json as json_lib
import re
import asyncio

class VideoAnswer(BaseModel):
    text: str = Field(description="Câu trả lời đúng trọng tâm dựa trên transcript. SỬ DỤNG LaTeX ($...$ hoặc $$...$$) cho tất cả công thức/ký hiệu toán học và Markdown cho định dạng văn bản.")
    filename: List[str] = Field(description="Tên file transcript gốc")
    video_url: List[str] = Field(description="URL của video gốc, số video phải khớp với số timestamp")
    title: List[str] = Field(description="Tiêu đề của video gốc, số lượng phải khớp với số lượng timestamp")
    start_timestamp: List[str] = Field(description="Thời điểm bắt đầu (format: HH:MM:SS)")
    end_timestamp: List[str] = Field(description="Thời điểm kết thúc (format: HH:MM:SS)")
    confidence: List[str] = Field(description="Độ tin cậy: zero/low/medium/high")

class TutorOutput(BaseModel):
    text: str
    video_url: List[str]
    title: List[str]
    filename: List[str]
    start_timestamp: List[str]
    end_timestamp: List[str]
    confidence: List[str]

class Offline_RAG:
    def __init__(self, llm, retriever, reranker, llm_internal=None) -> None:
        self.llm = llm
        self.llm_internal = llm_internal or llm
        self.prompt = ChatPromptTemplate.from_template("""
Bạn là trợ lý RAG chuyên nghiệp. Hãy trả lời câu hỏi dựa trên transcript video và lịch sử hội thoại.

QUY TẮC ĐỊNH DẠNG TOÁN HỌC (CỰC KỲ QUAN TRỌNG):
1. TUYỆT ĐỐI KHÔNG copy nguyên văn các ký tự toán học từ transcript nếu chúng không ở dạng LaTeX (Vd: Không dùng x0, p_theta, Π, q(x1:T)).
2. TẤT CẢ công thức, biến số, ký hiệu kỹ thuật PHẢI được chuyển sang LaTeX bọc trong dấu `$` hoặc `$$`.
   - Ví dụ: `x0` -> `$x_0$`, `p_theta` -> `$p_{{\theta}}$`, `Π` -> `$\prod$`, `q(x1:T|x0)` -> `$q(x_{{1:T}} | x_0)$`.
3. Trình bày bài giải rõ ràng, đẹp mắt bằng Markdown.

YÊU CẦU NỘI DUNG:
1. Chỉ dùng thông tin có trong transcript. Nếu không đủ dữ liệu, trả lời: "Mình chưa thấy đủ dữ liệu trong transcript để trả lời chính xác."
2. `text` viết tiếng Việt, ngắn gọn, súc tích, có citation dạng [0], [1], ...
3. Citation trong text phải khớp với index trong danh sách `video_url`.
4. Danh sách `video_url` chỉ chứa các nguồn CÓ trích dẫn trong `text`.
5. Chỉ trả về MỘT JSON object hợp lệ, không thêm lời giải thích ngoài JSON.
6. TUYỆT ĐỐI KHÔNG lặp lại câu hỏi ban đầu hay các biến thể tìm kiếm (queries) trong câu trả lời.

Lịch sử hội thoại:
{chat_history}

Transcript JSON:
{context}

Câu hỏi hiện tại:
{question}

Format instructions:
{format_instructions}
""")
        self.retriever = retriever
        self.reranker = reranker

    def format_doc(self, docs):
        formatted = []
        for doc in docs:
            item = {
                "video_url": doc.metadata.get("video_url", ""),
                "filename": doc.metadata.get("filename", ""),
                "title": doc.metadata.get("title", ""),
                "start_timestamp": doc.metadata.get("start_timestamp", ""),
                "end_timestamp": doc.metadata.get("end_timestamp", ""),
                "content": doc.page_content if isinstance(doc.page_content, str) else str(doc.page_content)
            }
            formatted.append(json_lib.dumps(item, ensure_ascii=False))
        return "[" + ",".join(formatted) + "]"

    async def generate_queries(self, query: str, chat_history: str = "") -> List[str]:
        prompt = ChatPromptTemplate.from_template(
            "Bạn là một chuyên gia AI. Dựa trên lịch sử hội thoại và câu hỏi mới, "
            "hãy tạo ra 3 câu truy vấn tìm kiếm (search queries) tối ưu để tìm thông tin chính xác nhất. "
            "Nếu câu hỏi mới chứa các đại từ (nó, họ, đó, ...), hãy thay thế chúng bằng thực thể cụ thể từ lịch sử.\n\n"
            "Lịch sử:\n{chat_history}\n\n"
            "Câu hỏi mới: {query}\n\n"
            "Chỉ trả về danh sách JSON gồm 3 chuỗi."
        )
        llm_expanded = self.llm_internal.with_config(
            tags=["internal_query"],
            run_name="query_expansion",
            callbacks=[]
        )
        chain = prompt | llm_expanded
        try:
            res = await chain.ainvoke({"query": query, "chat_history": chat_history})
            content = res.content if hasattr(res, "content") else str(res)
            match = re.search(r"(\[.*\])", content, re.DOTALL)
            if match:
                queries = json_lib.loads(match.group(1))
                if isinstance(queries, list):
                    return [query] + queries[:3]
        except Exception:
            pass
        return [query]

    async def get_context(self, query: str, chat_history: str = ""):
        """Bước chuẩn bị context: Chạy song song, KHÔNG stream."""
        queries = await self.generate_queries(query, chat_history)
        
        search_tasks = []
        for q in queries:
            if hasattr(self.retriever, "ainvoke"):
                search_tasks.append(self.retriever.ainvoke(q))
            else:
                search_tasks.append(asyncio.to_thread(self.retriever.get_relevant_documents, q))
        
        results = await asyncio.gather(*search_tasks)
        
        all_docs = []
        for docs in results:
            all_docs.extend(docs[:15])
        
        unique_docs = []
        seen_content = set()
        for doc in all_docs:
            content_hash = hash(doc.page_content)
            if content_hash not in seen_content:
                unique_docs.append(doc)
                seen_content.add(content_hash)
        
        reranked = self.reranker.rerank(unique_docs, query)[:10]
        return self.format_doc(reranked)

    def get_answer_chain(self):
        """Chuỗi chỉ chứa bước sinh câu trả lời, dùng để stream sạch."""
        from langchain_core.output_parsers import JsonOutputParser
        parser = JsonOutputParser(pydantic_object=TutorOutput)
        
        return (
            self.prompt.partial(format_instructions=parser.get_format_instructions())
            | self.llm.with_config(tags=["final_answer"])
        )
