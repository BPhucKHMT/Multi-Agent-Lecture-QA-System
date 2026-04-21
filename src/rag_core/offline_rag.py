from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables import RunnableLambda
from typing import List
import json


class VideoAnswer(BaseModel):
    text: str = Field(description="Câu trả lời đúng trọng tâm dựa trên transcript. SỬ DỤNG LaTeX ($...$ hoặc $$...$$) cho tất cả công thức/ký hiệu toán học và Markdown cho định dạng văn bản.")
    filename: List[str] = Field(description="Tên file transcript gốc")
    video_url: List[str] = Field(description="URL của video gốc, số video phải khớp với số timestamp")
    title: List[str] = Field(description="Tiêu đề của video gốc, số lượng phải khớp với số lượng timestamp")
    start_timestamp: List[str] = Field(description="Thời điểm bắt đầu (format: HH:MM:SS)")
    end_timestamp: List[str] = Field(description="Thời điểm kết thúc (format: HH:MM:SS)")
    confidence: List[str] = Field(description="Độ tin cậy: zero/low/medium/high")


parser = JsonOutputParser(pydantic_object=VideoAnswer)


class Offline_RAG:
    def __init__(self, llm, retriever, reranker) -> None:
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_template("""
Bạn là trợ lý RAG chuyên nghiệp. Hãy trả lời câu hỏi dựa trên transcript video được cung cấp.

QUY TẮC ĐỊNH DẠNG TOÁN HỌC (CỰC KỲ QUAN TRỌNG):
1. TUYỆT ĐỐI KHÔNG copy nguyên văn các ký tự toán học từ transcript nếu chúng không ở dạng LaTeX (Vd: Không dùng x0, p_theta, Π, q(x1:T)).
2. TẤT CẢ công thức, biến số, ký hiệu kỹ thuật PHẢI được chuyển sang LaTeX bọc trong dấu `$` hoặc `$$`.
   - Ví dụ: `x0` -> `$x_0$`, `p_theta` -> `$p_{\theta}$`, `Π` -> `$\prod$`, `q(x1:T|x0)` -> `$q(x_{1:T} | x_0)$`.
3. Trình bày bài giải rõ ràng, đẹp mắt bằng Markdown.

YÊU CẦU NỘI DUNG:
1. Chỉ dùng thông tin có trong transcript. Nếu không đủ dữ liệu, trả lời: "Mình chưa thấy đủ dữ liệu trong transcript để trả lời chính xác."
2. `text` viết tiếng Việt, ngắn gọn, súc tích, có citation dạng [0], [1], ...
3. Citation trong text phải khớp với index trong danh sách `video_url`.
4. Danh sách `video_url` chỉ chứa các nguồn CÓ trích dẫn trong `text`.
5. Chỉ trả về MỘT JSON object hợp lệ, không thêm lời giải thích ngoài JSON.

Transcript JSON:
{context}

Câu hỏi:
{question}

Format instructions:
{format_instructions}
""")
        self.retriever = retriever
        self.reranker = reranker

    def format_doc(self, docs, *args, **kwargs):
        formatted = []
        max_chars_per_doc = 1000
        for doc in docs:
            url = doc.metadata.get("video_url", "")
            filename = doc.metadata.get("filename", "")
            title = doc.metadata.get("title", "")
            start = doc.metadata.get("start_timestamp", "")
            end = doc.metadata.get("end_timestamp", "")
            content_text = doc.page_content if isinstance(doc.page_content, str) else str(doc.page_content)
            content = json.dumps(content_text[:max_chars_per_doc])  # escape quotes, newlines
            formatted.append(f'{{"video_url": "{url}", "filename": "{filename}", "title": "{title}","start": "{start}", "end": "{end}",  "content": {content}}}')
        return "[" + ",".join(formatted) + "]"

    # Hàm lấy context để đưa vào prompt
    def get_context(self, query: str):
        import time
        start_time = time.time()
        if hasattr(self.retriever, "invoke"):
            docs = self.retriever.invoke(query)
        else:
            docs = self.retriever.get_relevant_documents(query)
        reranked = self.reranker.rerank(docs, query, top_k=10)
        end_time = time.time()
        print(f"Time taken to get context: {end_time - start_time} seconds")
        return self.format_doc(reranked)

    def get_chain(self):
        return (
            {
                "question": RunnablePassthrough(),
                "context": RunnableLambda(self.get_context),
            }
            | self.prompt.partial(format_instructions=parser.get_format_instructions())
            | self.llm
        )

