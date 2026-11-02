"""
JSON trả ra có dạng:
{{
    "text": str,
    "video_url": List[str],
    "title": List[str],
    "filename": List[str],
    "start_timestamp": List[str],
    "end_timestamp": List[str],
    "confidence": List[str]
}}
Vì vậy khi thực hiện streaming, output đầu tiên luôn là "{{\n", output cuối cùng luôn là "}}\n".
Trong quá trình thực hiện, ta chỉ cần trích xuất phần value của key 'text' và ghép lại với nhau.
Bên cạnh đó prompt để trả về trường "text" ở đầu tiên giúp cho JsonStreamCleaner sẽ ngay lập tức "bắt" được tín hiệu và streaming trực tiếp từng 
chữ ra frontend mà không có độ trễ nào nữa. 
"""


from contextlib import nullcontext
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from typing import List
import json as json_lib
import re
import asyncio
import logging
import os
import time


from src.shared.metrics import (
    RAG_QUERY_EXPANSION_DECISIONS,
    RAG_RERANK_INPUT_DOCUMENTS,
    measure_rag_stage,
)
from src.shared.observability import get_langfuse_client

logger = logging.getLogger(__name__)

DEFAULT_RERANK_CANDIDATE_LIMIT = 24


def _rag_observation(name: str):
    client = get_langfuse_client()
    return (
        client.start_as_current_observation(as_type="span", name=name)
        if client is not None
        else nullcontext()
    )

def _context_top_k() -> int:
    try:
        value = int(os.getenv("RAG_CONTEXT_TOP_K", "5"))
    except ValueError:
        return 5
    return value if 1 <= value <= 20 else 5


def _rerank_candidate_limit() -> int:
    try:
        value = int(
            os.getenv(
                "RAG_RERANK_CANDIDATE_LIMIT",
                str(DEFAULT_RERANK_CANDIDATE_LIMIT),
            )
        )
    except ValueError:
        return DEFAULT_RERANK_CANDIDATE_LIMIT
    return value if value >= 10 else DEFAULT_RERANK_CANDIDATE_LIMIT


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
        self.prompt = ChatPromptTemplate.from_template(r"""
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
LUÔN LUÔN đặt key "text" ở vị trí ĐẦU TIÊN trong JSON object để hỗ trợ streaming nhanh nhất.
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
                "content": doc.page_content
                if isinstance(doc.page_content, str)
                else str(doc.page_content),
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
            tags=["internal_query"], run_name="query_expansion"
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

    async def get_context(
        self,
        query: str,
        chat_history: str = "",
        expand_query: bool = True,
    ):
        """Bước chuẩn bị context: Chạy song song, KHÔNG stream."""
        total_start = time.perf_counter()

        expand_start = time.perf_counter()
        should_expand = expand_query is not False
        decision = "expand" if should_expand else "skip"
        RAG_QUERY_EXPANSION_DECISIONS.labels(decision=decision).inc()
        if should_expand:
            with measure_rag_stage("query_expansion"):
                queries = await self.generate_queries(query, chat_history)
        else:
            queries = [query]
        expand_elapsed = time.perf_counter() - expand_start
        logger.info(
            "[TUTOR_TIMING] query_expansion=%.2fs query_count=%d",
            expand_elapsed,
            len(queries),
        )

        search_start = time.perf_counter()
        with _rag_observation("hybrid_retrieval") as observation:
            with measure_rag_stage("retrieval"):
                search_tasks = []
                for q in queries:
                    if hasattr(self.retriever, "ainvoke"):
                        search_tasks.append(self.retriever.ainvoke(q))
                    else:
                        search_tasks.append(
                            asyncio.to_thread(
                                self.retriever.get_relevant_documents, q
                            )
                        )

                results = await asyncio.gather(*search_tasks)
                result_counts = [len(docs) for docs in results]
            if observation is not None:
                observation.update(
                    metadata={
                        "query_count": len(queries),
                        "raw_docs": sum(result_counts),
                    }
                )
        search_elapsed = time.perf_counter() - search_start
        logger.info(
            "[TUTOR_TIMING] retrieve=%.2fs query_count=%d docs_per_query=%s total_raw_docs=%d",
            search_elapsed,
            len(queries),
            result_counts,
            sum(result_counts),
        )

        dedupe_start = time.perf_counter()
        with _rag_observation("dedupe") as observation:
            with measure_rag_stage("dedupe"):
                all_docs = []
                for docs in results:
                    all_docs.extend(docs[:15])

                unique_docs = []
                seen_content = set()
                for doc in all_docs:
                    if doc.page_content not in seen_content:
                        unique_docs.append(doc)
                        seen_content.add(doc.page_content)
            if observation is not None:
                observation.update(
                    metadata={
                        "capped_docs": len(all_docs),
                        "unique_docs": len(unique_docs),
                    }
                )
        dedupe_elapsed = time.perf_counter() - dedupe_start
        logger.info(
            "[TUTOR_TIMING] dedupe=%.2fs capped_docs=%d unique_docs=%d",
            dedupe_elapsed,
            len(all_docs),
            len(unique_docs),
        )

        rerank_start = time.perf_counter()
        rerank_candidates = unique_docs[:_rerank_candidate_limit()]
        rerank_backend = str(getattr(self.reranker, "backend", "none"))
        if rerank_backend not in {
            "openvino",
            "onnx",
            "onnx_cuda",
            "tensorrt",
            "torch_fp16",
            "torch_bf16",
            "torch_cpu",
            "none",
        }:
            rerank_backend = "none"
        RAG_RERANK_INPUT_DOCUMENTS.labels(backend=rerank_backend).observe(
            len(rerank_candidates)
        )

        with _rag_observation("rag_rerank") as observation:
            with measure_rag_stage("rerank"):
                reranked = await asyncio.to_thread(
                    self.reranker.rerank,
                    rerank_candidates,
                    query,
                )
                reranked = reranked[:_context_top_k()]
            if observation is not None:
                observation.update(
                    metadata={
                        "rerank_input_docs": len(rerank_candidates),
                        "rerank_output_docs": len(reranked),
                        "rerank_backend": rerank_backend,
                    }
                )
        rerank_elapsed = time.perf_counter() - rerank_start
        logger.info(
            "[TUTOR_TIMING] rerank=%.2fs input_docs=%d output_docs=%d",
            rerank_elapsed,
            len(rerank_candidates),
            len(reranked),
        )

        format_start = time.perf_counter()
        with _rag_observation("format_context") as observation:
            with measure_rag_stage("format"):
                context = self.format_doc(reranked)
            if observation is not None:
                observation.update(metadata={"context_chars": len(context)})
        format_elapsed = time.perf_counter() - format_start
        total_elapsed = time.perf_counter() - total_start
        logger.info(
            "[TUTOR_TIMING] format_context=%.2fs context_chars=%d total_context=%.2fs",
            format_elapsed,
            len(context),
            total_elapsed,
        )
        return context

    def get_answer_chain(self):
        """Chuỗi chỉ chứa bước sinh câu trả lời, dùng để stream sạch."""
        from langchain_core.output_parsers import JsonOutputParser

        parser = JsonOutputParser(pydantic_object=TutorOutput)

        return self.prompt.partial(
            format_instructions=parser.get_format_instructions()
        ) | self.llm.with_config(tags=["final_answer_json"])
