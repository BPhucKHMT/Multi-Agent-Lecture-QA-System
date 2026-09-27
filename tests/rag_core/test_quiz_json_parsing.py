import asyncio
import json
import os
import sys
import pytest
from pathlib import Path

from langchain_core.messages import HumanMessage
from prometheus_client import REGISTRY

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.rag_core.agents import quiz


def test_extract_quiz_json_payload_parses_fenced_json():
    raw = """
```json
{
  "quizzes": [
    {
      "question": "CNN là gì?",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A",
      "explanation": "Giải thích",
      "video_url": "https://youtube.com/watch?v=abc",
      "timestamp": "00:10:00"
    }
  ]
}
```
"""
    parsed = quiz._extract_quiz_json_payload(raw)
    assert isinstance(parsed, dict)
    assert parsed["quizzes"][0]["question"] == "CNN là gì?"


def test_extract_quiz_json_payload_parses_prefixed_text():
    raw = (
        "Đây là kết quả tạo quiz của bạn:\n"
        '{"quizzes":[{"question":"Q","options":["A","B","C","D"],'
        '"correct_answer":"A","explanation":"E","video_url":"u","timestamp":"00:00:01"}]}'
    )
    parsed = quiz._extract_quiz_json_payload(raw)
    assert isinstance(parsed, dict)
    assert parsed["quizzes"][0]["correct_answer"] == "A"


class _FakeDoc:
    page_content = "CNN content"
    metadata = {"video_url": "https://youtube.com/watch?v=abc", "start_timestamp": "00:00:01"}


class _FakeRetriever:
    async def aget_relevant_documents(self, _query):
        return [_FakeDoc()]

class _FakeReranker:
    def rerank(self, docs, _query):
        return docs


class _FakeJsonOutputParser:
    def __init__(self, *_args, **_kwargs):
        pass

    def get_format_instructions(self):
        return "format"


class _FakeChain:
    def invoke(self, _input):
        raise ValueError("Invalid json output")


class _FakeLLMChain:
    def __or__(self, _parser):
        return _FakeChain()

    def invoke(self, _input):
        return type("RawResult", (), {"content": "not json"})()


class _FakePrompt:
    def __or__(self, _llm):
        return _FakeLLMChain()


class _FakeChatPromptTemplate:
    @staticmethod
    def from_template(_template):
        return _FakePrompt()


def _stub_quiz_output(monkeypatch, questions):
    class FixedChain:
        def __or__(self, _parser):
            return self

        async def ainvoke(self, _inputs, config=None):
            return {"quizzes": questions}

    class FixedPrompt:
        def __or__(self, _llm):
            return FixedChain()

    class FixedChatPromptTemplate:
        @staticmethod
        def from_template(_template):
            return FixedPrompt()

    monkeypatch.setattr(quiz.resource_manager, "get_vector_retriever", lambda: _FakeRetriever())
    monkeypatch.setattr(quiz.resource_manager, "get_quiz_reranker", lambda: _FakeReranker())
    monkeypatch.setattr(quiz, "get_llm", lambda: object())
    monkeypatch.setattr(quiz, "JsonOutputParser", _FakeJsonOutputParser)
    monkeypatch.setattr(quiz, "ChatPromptTemplate", FixedChatPromptTemplate)


def test_node_quiz_returns_structured_error_when_parser_and_fallback_fail(monkeypatch):
    monkeypatch.setattr(quiz.resource_manager, "get_vector_retriever", lambda: _FakeRetriever())
    monkeypatch.setattr(quiz.resource_manager, "get_quiz_reranker", lambda: _FakeReranker())
    monkeypatch.setattr(quiz, "get_llm", lambda: object())
    monkeypatch.setattr(quiz, "JsonOutputParser", _FakeJsonOutputParser)
    monkeypatch.setattr(quiz, "ChatPromptTemplate", _FakeChatPromptTemplate)

    result = asyncio.run(quiz.node_quiz({
        "messages": [HumanMessage(content="tạo quiz cnn")]
    }))

    assert result["response"]["type"] == "error"
    assert "Lỗi tạo quiz" in result["response"]["text"]


@pytest.mark.parametrize(
    ("include_answers", "include_explanations"),
    [(False, False), (False, True), (True, False), (True, True)],
)
def test_node_quiz_honors_structured_settings_and_hides_excluded_fields(
    monkeypatch, include_answers, include_explanations
):
    observed = {}
    generated_quiz = {
        "quizzes": [{
            "question_type": "short_answer",
            "question": "What is a convolution?",
            "options": [],
            "correct_answer": "A local feature operation.",
            "explanation": "It applies a kernel to nearby input values.",
            "video_url": "https://youtube.com/watch?v=abc",
            "video_title": "CNN",
            "timestamp": "00:00:01",
        }]
    }

    class CapturingRetriever:
        async def ainvoke(self, query):
            observed["retrieval_query"] = query
            return [_FakeDoc()]

    class CapturingReranker:
        def rerank(self, docs, query):
            return docs

    class CapturingChain:
        async def ainvoke(self, inputs, config=None):
            observed["generation_inputs"] = inputs
            return generated_quiz

    class FakeLlmChain:
        def __or__(self, _parser):
            return CapturingChain()

    class FakePrompt:
        def __or__(self, _llm):
            return FakeLlmChain()

    class FakePromptTemplate:
        @staticmethod
        def from_template(_template):
            return FakePrompt()

    monkeypatch.setattr(quiz.resource_manager, "get_vector_retriever", lambda: CapturingRetriever())
    monkeypatch.setattr(quiz.resource_manager, "get_quiz_reranker", lambda: CapturingReranker())
    monkeypatch.setattr(quiz, "get_llm", lambda: object())
    monkeypatch.setattr(quiz, "JsonOutputParser", _FakeJsonOutputParser)
    monkeypatch.setattr(quiz, "ChatPromptTemplate", FakePromptTemplate)
    query = "Tạo 1 câu trả lời ngắn bằng tiếng Anh về CNN cho người mới học."
    args = {
        "query": query,
        "topic": "CNN",
        "question_type": "short_answer",
        "num_questions": 1,
        "difficulty": "easy",
        "language": "en",
        "target_audience": "beginner",
        "include_answers": include_answers,
        "include_explanations": include_explanations,
        "tags": ["concepts"],
    }
    before_stages = {
        stage: REGISTRY.get_sample_value(
            "puq_rag_stage_duration_seconds_count",
            {"stage": stage, "outcome": "success"},
        ) or 0
        for stage in ("retrieval", "rerank", "answer")
    }

    response = asyncio.run(quiz.node_quiz({
        "messages": [HumanMessage(content=query)],
        "tool_calls": [{"name": "GenerateQuiz", "args": args}],
    }))["response"]

    assert observed["retrieval_query"] == query
    assert json.loads(observed["generation_inputs"]["quiz_settings"]) == {
        "topic": "CNN",
        "question_type": "short_answer",
        "num_questions": 1,
        "difficulty": "easy",
        "language": "en",
        "options_per_question": None,
        "target_audience": "beginner",
        "include_answers": include_answers,
        "include_explanations": include_explanations,
        "tags": ["concepts"],
    }
    assert response["type"] == "quiz"
    assert response["quizzes"][0]["question_type"] == "short_answer"
    assert response["quizzes"][0]["options"] == []
    assert ("correct_answer" in response["quizzes"][0]) is include_answers
    assert ("explanation" in response["quizzes"][0]) is include_explanations
    assert ("A local feature operation." in response["text"]) is include_answers
    assert ("It applies a kernel" in response["text"]) is include_explanations
    assert len(response["video_url"]) == len(response["title"]) == 1
    for stage, before in before_stages.items():
        after = REGISTRY.get_sample_value(
            "puq_rag_stage_duration_seconds_count",
            {"stage": stage, "outcome": "success"},
        ) or 0
        assert after == before + 1


@pytest.mark.parametrize(
    ("args", "expected_options", "expected_questions"),
    [
        ({}, 4, None),
        ({"question_type": "multiple_choice", "options_per_question": 7}, 7, None),
        ({"question_type": "multiple_choice", "options_per_question": 1}, 4, None),
        (
            {
                "question_type": "multiple_choice",
                "options_per_question": None,
                "options_per_question_from_query": True,
                "number_of_questions": 8,
            },
            None,
            8,
        ),
        ({"question_type": "true_false"}, 2, None),
        ({"question_type": "short_answer"}, None, None),
    ],
)
def test_quiz_settings_keep_mcq_default_and_legacy_count_variants(
    args, expected_options, expected_questions
):
    settings = quiz._quiz_settings(args, "")

    assert settings["options_per_question"] == expected_options
    assert settings["num_questions"] == expected_questions


@pytest.mark.parametrize(
    ("query", "expected_count"),
    [
        ("Từ 25 câu hỏi ôn tập CNN, chọn 3 câu làm quiz.", 3),
        ("Chọn 3 câu làm quiz từ bộ 25 câu hỏi ôn tập CNN.", 3),
        ("Tạo quiz từ bộ 25 câu hỏi ôn tập CNN.", None),
    ],
)
def test_quiz_uses_requested_size_not_source_bank_size(query, expected_count):
    assert quiz._quiz_settings({}, query)["num_questions"] == expected_count

@pytest.mark.parametrize(
    ("query", "generated_count", "generated_options", "expected_error"),
    [
        ("Tạo 21 câu trắc nghiệm về CNN, mỗi câu có 22 lựa chọn.", 3, 22, "21 câu"),
        ("Tạo 21 câu trắc nghiệm về CNN, mỗi câu có 22 lựa chọn.", 21, 4, "22 lựa chọn"),
        ("Tạo 21 câu trắc nghiệm về CNN, mỗi câu có 22 lựa chọn.", 21, 22, None),
        ("Tạo hai mươi mốt câu trắc nghiệm về CNN, mỗi câu có 22 lựa chọn.", 3, 22, "số câu"),
    ],
)
def test_node_quiz_rejects_wrong_counts_outside_jev_choices(
    monkeypatch, query, generated_count, generated_options, expected_error
):
    quizzes = [
        {
            "question_type": "multiple_choice",
            "question": f"Câu {index}?",
            "options": ["A"] + [f"B{option}" for option in range(generated_options - 1)],
            "correct_answer": "A",
            "explanation": "Giải thích",
            "video_url": "https://youtube.com/watch?v=abc",
            "video_title": "CNN",
            "timestamp": "00:00:01",
        }
        for index in range(generated_count)
    ]

    _stub_quiz_output(monkeypatch, quizzes)

    response = asyncio.run(quiz.node_quiz({
        "messages": [HumanMessage(content=query)],
        "tool_calls": [{
            "name": "GenerateQuiz",
            "args": {
                "query": query,
                "question_type": "multiple_choice",
                "num_questions": None,
                "num_questions_from_query": True,
                "options_per_question": None,
                "options_per_question_from_query": True,
            },
        }],
    }))["response"]

    if expected_error is None:
        assert response["type"] == "quiz"
        assert len(response["quizzes"]) == generated_count
    else:
        assert response["type"] == "error"
        assert expected_error in response["text"]


@pytest.mark.parametrize("answer", ["Convolution", "A"])
def test_quiz_normalizes_labeled_correct_answer_for_interactive_grading(monkeypatch, answer):
    _stub_quiz_output(monkeypatch, [{
        "question_type": "multiple_choice",
        "question": "CNN dùng phép gì?",
        "options": ["A. Convolution", "B. Pooling"],
        "correct_answer": answer,
        "explanation": "Tích chập áp dụng kernel.",
        "video_url": "https://youtube.com/watch?v=abc",
        "video_title": "CNN",
        "timestamp": "00:00:01",
    }])
    query = "Tạo 1 câu trắc nghiệm về CNN, mỗi câu có 2 lựa chọn."
    response = asyncio.run(quiz.node_quiz({
        "messages": [HumanMessage(content=query)],
        "tool_calls": [{"name": "GenerateQuiz", "args": {
            "query": query, "question_type": "multiple_choice",
            "num_questions": 1, "options_per_question": 2,
        }}],
    }))["response"]

    assert response["type"] == "quiz"
    assert response["quizzes"][0]["correct_answer"] == "A. Convolution"
    assert "**Đáp án tham khảo:** A. Convolution" in response["text"]
