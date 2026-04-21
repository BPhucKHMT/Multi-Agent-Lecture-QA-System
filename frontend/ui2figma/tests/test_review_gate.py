import pytest

from frontend.ui2figma.review_gate import evaluate_review_decision


def test_evaluate_review_decision_accepts_ok():
    result = evaluate_review_decision("OK")
    assert result["ready_for_codegen"] is True


def test_evaluate_review_decision_rejects_unknown():
    with pytest.raises(ValueError):
        evaluate_review_decision("approve")
