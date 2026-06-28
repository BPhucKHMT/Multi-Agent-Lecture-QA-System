from experiments.src.evaluation.qa_metrics import (
    filter_answerable_records,
    compute_no_answer_metrics,
    is_refusal,
    normalize_answer,
)


def test_is_refusal_detects_template_and_variants():
    assert is_refusal("Không có thông tin trong dữ liệu bài giảng.")
    assert is_refusal("Mình không đủ thông tin để trả lời câu hỏi này.")
    assert is_refusal("Không tìm thấy nội dung liên quan trong transcript.")
    assert not is_refusal("Hàm main được thực thi khi chương trình bắt đầu chạy.")


def test_normalize_answer_collapses_whitespace_and_case():
    assert normalize_answer("  Xin   Chào\nBạn  ") == "xin chào bạn"


def test_compute_no_answer_metrics_counts_refusals_and_false_answers():
    records = [
        {"has_answer": False, "generated_answer": "Không có thông tin trong dữ liệu bài giảng.", "contexts": []},
        {"has_answer": False, "generated_answer": "Không đủ thông tin để trả lời.", "contexts": ["irrelevant"]},
        {"has_answer": False, "generated_answer": "Ngôn ngữ Go được phát triển bởi Google.", "contexts": ["irrelevant"]},
        {"has_answer": True, "generated_answer": "Answer", "contexts": []},
    ]

    metrics = compute_no_answer_metrics(records)

    assert metrics["no_answer_count"] == 3
    assert metrics["correct_refusal_count"] == 2
    assert metrics["false_answer_count"] == 1
    assert metrics["exact_template_count"] == 1
    assert metrics["refusal_accuracy"] == 2 / 3
    assert metrics["false_answer_rate"] == 1 / 3
    assert metrics["refusal_template_rate"] == 1 / 3
    assert metrics["non_empty_context_refusal_rate"] == 1 / 3


def test_filter_answerable_records_excludes_refusals_and_no_answer_items():
    records = [
        {"has_answer": True, "generated_answer": "Câu trả lời", "ground_truth": "Đáp án"},
        {"has_answer": True, "generated_answer": "Không có thông tin trong dữ liệu bài giảng.", "ground_truth": "Đáp án"},
        {"has_answer": False, "generated_answer": "Không có thông tin trong dữ liệu bài giảng.", "ground_truth": "Không có thông tin"},
    ]

    filtered = filter_answerable_records(records)

    assert filtered == [records[0]]
