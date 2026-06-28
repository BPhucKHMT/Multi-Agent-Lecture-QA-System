from __future__ import annotations

import os
import re
from collections.abc import Iterable, Sequence
from typing import Any

NO_ANSWER_TEMPLATE = "Không có thông tin trong dữ liệu bài giảng."
NO_ANSWER_PATTERNS = (
    "không có thông tin",
    "không đủ thông tin",
    "không tìm thấy",
    "không thể trả lời",
    "dữ liệu bài giảng không",
)


def normalize_answer(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def is_refusal(text: str) -> bool:
    normalized = normalize_answer(text)
    return any(pattern in normalized for pattern in NO_ANSWER_PATTERNS)


def filter_answerable_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if record.get("has_answer") is True and not is_refusal(str(record.get("generated_answer", "")))
    ]


def compute_no_answer_metrics(records: Iterable[dict[str, Any]]) -> dict[str, float | int]:
    no_answer_records = [record for record in records if record.get("has_answer") is False]
    total = len(no_answer_records)
    if total == 0:
        return _empty_no_answer_metrics()

    refusal_records = [
        record
        for record in no_answer_records
        if is_refusal(str(record.get("generated_answer", "")))
    ]
    exact_template_count = sum(
        1
        for record in refusal_records
        if normalize_answer(str(record.get("generated_answer", ""))) == normalize_answer(NO_ANSWER_TEMPLATE)
    )
    non_empty_context_refusals = sum(
        1 for record in refusal_records if _has_context(record.get("contexts", []))
    )
    correct_refusal_count = len(refusal_records)
    false_answer_count = total - correct_refusal_count

    return {
        "no_answer_count": total,
        "correct_refusal_count": correct_refusal_count,
        "false_answer_count": false_answer_count,
        "exact_template_count": exact_template_count,
        "refusal_accuracy": correct_refusal_count / total,
        "false_answer_rate": false_answer_count / total,
        "refusal_template_rate": exact_template_count / total,
        "non_empty_context_refusal_rate": non_empty_context_refusals / total,
    }


def compute_bertscore_metrics(records: Sequence[dict[str, Any]]) -> dict[str, float | int]:
    answerable_records = filter_answerable_records(records)
    if not answerable_records:
        return {"answerable_count": 0, "bertscore_precision": 0.0, "bertscore_recall": 0.0, "bertscore_f1": 0.0}

    from bert_score import score as bert_score

    predictions = [str(record["generated_answer"]) for record in answerable_records]
    references = [str(record["ground_truth"]) for record in answerable_records]
    precision, recall, f1 = bert_score(predictions, references, lang="vi", verbose=True)
    return {
        "answerable_count": len(answerable_records),
        "bertscore_precision": float(precision.mean().item()),
        "bertscore_recall": float(recall.mean().item()),
        "bertscore_f1": float(f1.mean().item()),
    }


def compute_ragas_metrics(records: Sequence[dict[str, Any]]) -> dict[str, float | int]:
    answerable_records = filter_answerable_records(records)
    if not answerable_records:
        return _empty_ragas_metrics(0)

    _ensure_openai_api_key()

    from datasets import Dataset
    from langchain_openai import OpenAIEmbeddings
    from ragas import evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

    dataset = Dataset.from_list([
        {
            "question": str(record["question"]),
            "answer": str(record["generated_answer"]),
            "contexts": [str(context) for context in record.get("contexts", [])],
            "ground_truth": str(record["ground_truth"]),
        }
        for record in answerable_records
    ])
    embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        embeddings=embeddings,
    )
    return {
        "ragas_count": len(answerable_records),
        "ragas_faithfulness": _metric_value(result, "faithfulness"),
        "ragas_answer_relevancy": _metric_value(result, "answer_relevancy"),
        "ragas_context_precision": _metric_value(result, "context_precision"),
        "ragas_context_recall": _metric_value(result, "context_recall"),
    }


def _ensure_openai_api_key() -> None:
    if os.getenv("OPENAI_API_KEY"):
        return
    api_key = os.getenv("myAPIKey")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY or myAPIKey for RAGAS evaluation.")
    os.environ["OPENAI_API_KEY"] = api_key


def _has_context(contexts: Any) -> bool:
    return isinstance(contexts, list) and any(str(context).strip() for context in contexts)


def _empty_no_answer_metrics() -> dict[str, float | int]:
    return {
        "no_answer_count": 0,
        "correct_refusal_count": 0,
        "false_answer_count": 0,
        "exact_template_count": 0,
        "refusal_accuracy": 0.0,
        "false_answer_rate": 0.0,
        "refusal_template_rate": 0.0,
        "non_empty_context_refusal_rate": 0.0,
    }


def _empty_ragas_metrics(count: int) -> dict[str, float | int]:
    return {
        "ragas_count": count,
        "ragas_faithfulness": 0.0,
        "ragas_answer_relevancy": 0.0,
        "ragas_context_precision": 0.0,
        "ragas_context_recall": 0.0,
    }


def _metric_value(result: Any, key: str) -> float:
    if hasattr(result, "to_pandas"):
        frame = result.to_pandas()
        if key in frame:
            return float(frame[key].mean())
    if isinstance(result, dict):
        return float(result.get(key, 0.0))
    return float(getattr(result, key, 0.0) or 0.0)
