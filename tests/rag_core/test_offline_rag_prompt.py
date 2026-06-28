import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.rag_core.offline_rag import Offline_RAG


def test_offline_rag_prompt_prioritizes_quality_without_hard_caps():
    rag = Offline_RAG(llm=None, retriever=None, reranker=None)
    prompt_text = rag.prompt.messages[0].prompt.template

    assert "Mình chưa thấy đủ dữ liệu trong transcript để trả lời chính xác." in prompt_text
    assert "Mình chỉ hỗ trợ các câu hỏi liên quan nội dung video." in prompt_text
    assert "Trả lời đủ ý theo mức độ phức tạp câu hỏi" in prompt_text
    assert "Chỉ trích dẫn những nguồn cần thiết" in prompt_text
    assert "Giới hạn `text` tối đa 120 từ" not in prompt_text
