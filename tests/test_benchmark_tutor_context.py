import asyncio
import json
from types import SimpleNamespace

from scripts.benchmark_tutor_context import (
    _citation_contract,
    benchmark_question,
    select_questions,
)


def test_citation_contract_requires_index_aligned_metadata_arrays():
    response = {
        "text": "Không có citation.",
        "video_url": [],
        "title": ["lệch"],
        "filename": [],
        "start_timestamp": [],
        "end_timestamp": [],
        "confidence": [],
    }

    indices_valid, arrays_aligned = _citation_contract(response, document_count=1)

    assert indices_valid is True
    assert arrays_aligned is False


def test_select_questions_applies_offset_and_limit():
    questions = [{"id": f"q{index}"} for index in range(5)]

    selected = select_questions(questions, offset=2, limit=2)

    assert [row["id"] for row in selected] == ["q2", "q3"]


def test_benchmark_question_marks_valid_tutor_payload_as_rag():
    response = {
        "text": "Decision tree chia dữ liệu theo thuộc tính [0].",
        "video_url": ["https://example.test/video"],
        "title": ["Decision tree"],
        "filename": ["lecture.json"],
        "start_timestamp": ["00:00:01"],
        "end_timestamp": ["00:00:05"],
        "confidence": ["high"],
    }

    class Chain:
        async def astream(self, _inputs):
            yield SimpleNamespace(
                content=json.dumps(response, ensure_ascii=False),
                usage_metadata={
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                },
            )

    class RagCore:
        async def get_context(self, _query, *, chat_history, expand_query):
            assert chat_history == ""
            assert expand_query is False
            return "[{}]"

        def get_answer_chain(self):
            return Chain()

    row = asyncio.run(
        benchmark_question(
            RagCore(),
            {
                "id": "q1",
                "question": "Decision tree là gì?",
                "answer": "Mô hình cây quyết định.",
                "evidence": [],
            },
            top_k=5,
        )
    )

    assert row["response_type"] == "rag"
    assert row["citation_indices_valid"] is True
    assert row["metadata_arrays_aligned"] is True
