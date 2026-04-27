import os
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage

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
    def get_relevant_documents(self, _query):
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


def test_node_quiz_returns_structured_error_when_parser_and_fallback_fail(monkeypatch):
    monkeypatch.setattr(
        quiz.resource_manager,
        "get_quiz_resources",
        lambda: (_FakeRetriever(), _FakeReranker()),
    )
    monkeypatch.setattr(quiz, "get_llm", lambda: object())
    monkeypatch.setattr(quiz, "JsonOutputParser", _FakeJsonOutputParser)
    monkeypatch.setattr(quiz, "ChatPromptTemplate", _FakeChatPromptTemplate)

    result = quiz.node_quiz({"messages": [HumanMessage(content="tạo quiz cnn")]})

    assert result["response"]["type"] == "error"
    assert "Lỗi tạo quiz" in result["response"]["text"]
