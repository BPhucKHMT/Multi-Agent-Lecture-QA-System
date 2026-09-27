import asyncio
import json

import httpx
import pytest

from src.generation import jev_router


def _choice(value):
    return {"type": "choice", "choice": value, "probabilities": {value: 1}}


def _noul(value):
    return {"type": "noul", "noul": value}


def _mock_experiential(monkeypatch, response_body):
    monkeypatch.setenv("EXPERIENTIAL_API_KEY", "xpl-unit-test")
    requests = []
    clients = []
    original_client = jev_router.httpx.AsyncClient

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=response_body)

    def build_client(**kwargs):
        client = original_client(
            transport=httpx.MockTransport(respond),
            **kwargs,
        )
        clients.append(client)
        return client

    monkeypatch.setattr(jev_router.httpx, "AsyncClient", build_client)
    return requests, clients

class _MetricRecorder:
    def __init__(self):
        self.labels_calls = []
        self.inc_calls = 0
        self.observe_calls = []

    def labels(self, **labels):
        self.labels_calls.append(labels)
        return self

    def inc(self):
        self.inc_calls += 1

    def observe(self, value):
        self.observe_calls.append(value)


def _record_jev_metrics(monkeypatch):
    requests_metric = _MetricRecorder()
    duration_metric = _MetricRecorder()
    monkeypatch.setattr(jev_router, "JEV_REQUESTS", requests_metric)
    monkeypatch.setattr(jev_router, "JEV_DURATION", duration_metric)
    return requests_metric, duration_metric


def _mock_jev_response(monkeypatch, response):
    monkeypatch.setenv("EXPERIENTIAL_API_KEY", "xpl-unit-test")
    original_client = jev_router.httpx.AsyncClient

    def respond(request):
        if isinstance(response, BaseException):
            raise response
        return response

    def build_client(**kwargs):
        return original_client(
            transport=httpx.MockTransport(respond),
            **kwargs,
        )

    monkeypatch.setattr(jev_router.httpx, "AsyncClient", build_client)


@pytest.mark.parametrize(
    ("response", "expected_outcome", "expected_error"),
    [
        (httpx.Response(429, json={"error": "rate limited"}), "http_429", httpx.HTTPStatusError),
        (httpx.Response(200, json={"answers": {"route": _choice("UnknownAgent")}}), "invalid", ValueError),
    ],
)
def test_jev_request_metrics_classify_http_and_invalid_outcomes(
    monkeypatch,
    response,
    expected_outcome,
    expected_error,
):
    requests_metric, duration_metric = _record_jev_metrics(monkeypatch)
    _mock_jev_response(monkeypatch, response)

    with pytest.raises(expected_error):
        asyncio.run(jev_router.route_with_jev(
            "nội dung riêng tư",
            [{"role": "user", "content": "lịch sử riêng tư"}],
            {"AskGeneral": "Greetings"},
        ))

    assert requests_metric.labels_calls == [{"outcome": expected_outcome}]
    assert requests_metric.inc_calls == 1
    assert duration_metric.labels_calls == [{"outcome": expected_outcome}]
    assert len(duration_metric.observe_calls) == 1


def test_jev_request_metrics_classify_timeout_without_counting_missing_key(monkeypatch):
    requests_metric, duration_metric = _record_jev_metrics(monkeypatch)
    _mock_jev_response(monkeypatch, httpx.ReadTimeout("provider timeout"))

    with pytest.raises(httpx.ReadTimeout):
        asyncio.run(jev_router.route_with_jev(
            "câu hỏi",
            [],
            {"AskGeneral": "Greetings"},
        ))

    assert requests_metric.labels_calls == [{"outcome": "timeout"}]
    assert requests_metric.inc_calls == 1
    assert len(duration_metric.observe_calls) == 1

    monkeypatch.delenv("EXPERIENTIAL_API_KEY", raising=False)
    with pytest.raises(ValueError, match="EXPERIENTIAL_API_KEY is required"):
        asyncio.run(jev_router.route_with_jev("câu hỏi", [], {"AskGeneral": "Greetings"}))
    assert requests_metric.inc_calls == 1


def _quiz_answers(
    question_type="multiple_choice",
    num_questions="unspecified",
    difficulty="unspecified",
    language="unspecified",
    options_per_question="unspecified",
    omit_answers=0.0,
    omit_explanations=0.0,
):
    return {
        "route": _choice("GenerateQuiz"),
        "num_questions": _choice(num_questions),
        "difficulty": _choice(difficulty),
        "language": _choice(language),
        "question_type": _choice(question_type),
        "options_per_question": _choice(options_per_question),
        "omit_answers": _noul(omit_answers),
        "omit_explanations": _noul(omit_explanations),
    }


def test_experiential_systemone_maps_quiz_answers_and_noul_flags(monkeypatch):
    query = "Tạo 5 câu trả lời ngắn khó về CNN, bằng tiếng Anh; ẩn đáp án."
    requests, _ = _mock_experiential(monkeypatch, {
        "answers": _quiz_answers(
            question_type="short_answer",
            num_questions="5",
            difficulty="hard",
            language="en",
            omit_answers=0.9,
            omit_explanations=0.1,
        )
    })

    decision = asyncio.run(jev_router.route_with_jev(
        query,
        [{"role": "user", "content": "Câu hỏi trước"}],
        {"AskTutor": "Nội dung học thuật", "GenerateQuiz": "Tạo quiz"},
    ))

    assert decision == {
        "name": "GenerateQuiz",
        "args": {
            "query": query,
            "question_type": "short_answer",
            "include_answers": False,
            "include_explanations": True,
            "num_questions": 5,
            "difficulty": "hard",
            "language": "en",
        },
    }
    request = requests[0]
    assert str(request.url) == "https://api.experientiallabs.ai/v1/systemone"
    assert request.headers["Authorization"] == "Bearer xpl-unit-test"
    payload = json.loads(request.content)
    assert payload["model"] == "jev-latest"
    assert payload["state"] == {
        "current_request": query,
        "conversation_history": [{"role": "user", "content": "Câu hỏi trước"}],
    }
    assert set(payload["questions"]) == {
        "route",
        "num_questions",
        "difficulty",
        "language",
        "question_type",
        "options_per_question",
        "omit_answers",
        "omit_explanations",
    }
    assert set(payload["questions"]["num_questions"]["criteria"]) == {
        "unspecified",
        "other",
        *(str(count) for count in range(1, 21)),
    }
    assert set(payload["questions"]["options_per_question"]["criteria"]) == {
        "unspecified",
        "other",
        *(str(count) for count in range(2, 21)),
    }
    assert payload["questions"]["route"]["criteria"] == {
        "AskTutor": "Nội dung học thuật",
        "GenerateQuiz": "Tạo quiz",
    }
    assert payload["questions"]["omit_answers"]["type"] == "noul"
    assert payload["questions"]["omit_answers"]["criteria"] == {
        "true": "Người dùng yêu cầu ẩn hoặc không cung cấp đáp án.",
        "false": "Người dùng không yêu cầu ẩn đáp án; mặc định có đáp án.",
    }


def test_unspecified_multiple_choice_defaults_to_four_options(monkeypatch):
    _mock_experiential(monkeypatch, {"answers": _quiz_answers()})

    decision = asyncio.run(jev_router.route_with_jev(
        "Tạo quiz về CNN", [], {"GenerateQuiz": "Tạo quiz"}
    ))

    assert decision["args"]["question_type"] == "multiple_choice"
    assert decision["args"]["options_per_question"] == 4
    assert decision["args"]["include_answers"] is True
    assert decision["args"]["include_explanations"] is True


def test_counts_outside_typed_ranges_remain_in_original_query(monkeypatch):
    query = "Tạo 25 câu hỏi, mỗi câu có 24 lựa chọn, về mạng máy tính."
    _mock_experiential(monkeypatch, {
        "answers": _quiz_answers(
            num_questions="other",
            options_per_question="other",
        )
    })

    decision = asyncio.run(jev_router.route_with_jev(
        query, [], {"GenerateQuiz": "Tạo quiz"}
    ))

    assert decision["args"]["num_questions"] is None
    assert decision["args"]["num_questions_from_query"] is True
    assert decision["args"]["options_per_question"] is None
    assert decision["args"]["options_per_question_from_query"] is True
    assert decision["args"]["query"] == query


@pytest.mark.parametrize(
    ("question_type", "option_count", "expected_options"),
    [
        ("multiple_choice", "5", 5),
        ("true_false", "unspecified", 2),
        ("short_answer", "unspecified", None),
    ],
)
def test_supported_quiz_formats_keep_option_rules(
    question_type,
    option_count,
    expected_options,
    monkeypatch,
):
    _mock_experiential(monkeypatch, {
        "answers": _quiz_answers(
            question_type=question_type,
            options_per_question=option_count,
        )
    })

    decision = asyncio.run(jev_router.route_with_jev(
        "Tạo quiz về CNN", [], {"GenerateQuiz": "Tạo quiz"}
    ))

    assert decision["args"]["question_type"] == question_type
    if expected_options is None:
        assert "options_per_question" not in decision["args"]
    else:
        assert decision["args"]["options_per_question"] == expected_options


def test_non_quiz_route_keeps_only_original_query(monkeypatch):
    _mock_experiential(monkeypatch, {
        "answers": {"route": _choice("MathSolver")}
    })

    decision = asyncio.run(jev_router.route_with_jev(
        "Tính đạo hàm x^2",
        [],
        {"MathSolver": "Toán học", "AskTutor": "Bài giảng"},
    ))

    assert decision == {
        "name": "MathSolver",
        "args": {"query": "Tính đạo hàm x^2"},
    }


def test_rejects_route_outside_allowlist(monkeypatch):
    _mock_experiential(monkeypatch, {
        "answers": {"route": _choice("UnknownAgent")}
    })

    with pytest.raises(ValueError):
        asyncio.run(jev_router.route_with_jev(
            "hello", [], {"AskGeneral": "Greetings"}
        ))


def test_requires_experiential_api_key(monkeypatch):
    monkeypatch.delenv("EXPERIENTIAL_API_KEY", raising=False)

    with pytest.raises(ValueError, match="EXPERIENTIAL_API_KEY is required"):
        asyncio.run(jev_router.route_with_jev(
            "hello", [], {"AskGeneral": "Greetings"}
        ))


def test_managed_jev_client_is_reused_across_calls(monkeypatch):
    monkeypatch.setenv("EXPERIENTIAL_API_KEY", "xpl-unit-test")
    requests = []
    clients = []
    response_body = {"answers": {"route": _choice("MathSolver")}}
    original_client = httpx.AsyncClient

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=response_body)

    def build_client(**kwargs):
        client = original_client(
            transport=httpx.MockTransport(respond),
            **kwargs,
        )
        clients.append(client)
        return client

    monkeypatch.setattr(jev_router.httpx, "AsyncClient", build_client)

    async def make_two_calls():
        client = jev_router.open_jev_http_client()
        try:
            first = await jev_router.route_with_jev(
                "Tính đạo hàm x^2", [], {"MathSolver": "Toán học"}
            )
            second = await jev_router.route_with_jev(
                "Giải phương trình x + 2 = 5", [], {"MathSolver": "Toán học"}
            )
            assert first["name"] == second["name"] == "MathSolver"
            assert len(requests) == 2
            assert clients == [client]
            assert not client.is_closed
        finally:
            await jev_router.close_jev_http_client()
        assert client.is_closed

    asyncio.run(make_two_calls())


