from types import SimpleNamespace
from collections import Counter

from scripts.benchmark_supervisor_latency import (
    Measurement,
    SAMPLE_QUESTIONS,
    error_label,
    paired_mean_delta,
    route_match_counts,
    summarize_latencies,
)


def test_summary_excludes_failed_observations():
    assert summarize_latencies([0.2, None, 0.6]) == {
        "min": 0.2,
        "median": 0.4,
        "mean": 0.4,
        "max": 0.6,
    }


def test_paired_mean_delta_is_positive_when_luna_is_slower():
    assert paired_mean_delta([1.0, 2.0, None], [1.5, 2.5, 9.0]) == 0.5


def test_paired_mean_delta_is_none_without_successful_pairs():
    assert paired_mean_delta([None], [0.4]) is None


def test_default_suite_has_two_questions_per_agent_route():
    counts = Counter(expected_route for _, _, expected_route in SAMPLE_QUESTIONS)

    assert counts == {
        "MathSolver": 2,
        "AskTutor": 2,
        "CodeAssistant": 2,
        "GenerateQuiz": 2,
        "AskGeneral": 2,
    }


def test_route_match_counts_excludes_failed_calls():
    results = [
        Measurement("Math", "query", 1, "Jev", "MathSolver", "MathSolver", 0.2, None),
        Measurement("Tutor", "query", 1, "Jev", "AskTutor", "MathSolver", 0.3, None),
        Measurement("Code", "query", 1, "Jev", None, "CodeAssistant", 0.4, "HTTPStatusError"),
    ]

    assert route_match_counts(results) == (1, 2)


def test_error_label_shows_http_status_without_response_body():
    error = RuntimeError()
    error.response = SimpleNamespace(status_code=429)

    assert error_label(error) == "RuntimeError (HTTP 429)"


def test_error_label_includes_provider_code_but_not_message():
    error = RuntimeError()
    error.response = SimpleNamespace(
        status_code=403,
        json=lambda: {
            "error": {
                "type": "permission_error",
                "code": "model_not_granted",
                "message": "Do not expose this text.",
            }
        },
    )

    label = error_label(error)
    assert label == "RuntimeError (HTTP 403, permission_error/model_not_granted)"
    assert "Do not expose" not in label
