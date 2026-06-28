from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.scripts.benchmark_embeddings import load_config, resolve_paths as resolve_dense_paths
from experiments.scripts.benchmark_hybrid_retrieval import resolve_paths as resolve_hybrid_paths
from experiments.src.data.chunk_loader import load_chunks, load_parent_chunks
from experiments.src.evaluation.qa_metrics import (
    NO_ANSWER_TEMPLATE,
    compute_bertscore_metrics,
    compute_no_answer_metrics,
    compute_ragas_metrics,
    is_refusal,
)

CONFIGS: dict[str, dict[str, str]] = {
    "C21": {
        "family": "timestamp150",
        "retrieval": "hybrid",
        "config_path": "experiments/configs/embedding/timestamp_150_50_bge_m3_finetuned_v3_hybrid.yaml",
    },
    "C22": {
        "family": "parent-child",
        "retrieval": "hybrid",
        "config_path": "experiments/configs/embedding/parent_child_180s_45s_bge_m3_finetuned_v3_child_hybrid.yaml",
    },
    "C19": {
        "family": "semantic",
        "retrieval": "hybrid",
        "config_path": "experiments/configs/embedding/semantic_bge_m3_finetuned_v3_hybrid.yaml",
    },
    "C02": {
        "family": "recursive",
        "retrieval": "hybrid",
        "config_path": "experiments/configs/embedding/recursive_bge_m3_hybrid.yaml",
    },
}

PROMPT_TEMPLATE = """Bạn là trợ lý học tập. Trả lời câu hỏi chỉ dựa trên ngữ cảnh được cung cấp.

Ngữ cảnh:
{context}

Câu hỏi:
{question}

Quy tắc:
1. Nếu ngữ cảnh có đủ thông tin, trả lời ngắn gọn, đúng trọng tâm bằng tiếng Việt.
2. Nếu ngữ cảnh không có đủ thông tin, trả lời đúng câu sau:
   \"Không có thông tin trong dữ liệu bài giảng.\"
3. Không dùng kiến thức ngoài ngữ cảnh.
4. Không cần tạo citation.

Câu trả lời:"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark QA generation metrics for selected retrieval configs.")
    parser.add_argument("--configs", default="C21,C22,C19,C02", help="Comma-separated config IDs.")
    parser.add_argument("--query-path", default="experiments/data/ground_truth/ground_truth_pilot.jsonl")
    parser.add_argument("--reranked-root", default="experiments/runs/e2e_reranked")
    parser.add_argument("--out-dir", default="experiments/runs/qa_metrics")
    parser.add_argument("--limit", type=int, help="Limit queries per config for smoke tests.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of reranked contexts used for generation.")
    parser.add_argument("--generate", action="store_true", help="Call OpenAI to generate predictions. Costs money.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing prediction files.")
    parser.add_argument("--run-bertscore", action="store_true", help="Compute BERTScore. May download/load models.")
    parser.add_argument("--run-ragas", action="store_true", help="Compute RAGAS. Costs money.")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    ground_truth = load_ground_truth(ROOT / args.query_path, args.limit)
    selected_configs = [config_id.strip() for config_id in args.configs.split(",") if config_id.strip()]
    validate_optional_dependencies(args.run_bertscore, args.run_ragas)
    summary = {}

    llm = create_llm() if args.generate else None
    for config_id in selected_configs:
        if config_id not in CONFIGS:
            raise ValueError(f"Unknown config_id: {config_id}")

        prediction_path = out_dir / f"{config_id}_predictions.jsonl"
        if args.generate and (args.overwrite or not prediction_path.exists()):
            records = generate_predictions(config_id, ground_truth, ROOT / args.reranked_root, args.top_k, llm)
            write_jsonl(prediction_path, records)
        elif prediction_path.exists():
            records = load_jsonl(prediction_path)
        else:
            raise FileNotFoundError(
                f"Missing {prediction_path}. Run with --generate to create predictions."
            )

        summary[config_id] = compute_summary(config_id, records, args.run_bertscore, args.run_ragas)
        print(format_summary(config_id, summary[config_id]))

    write_json(out_dir / "qa_metrics_summary.json", summary)
    write_report(out_dir / "qa_metrics_report.md", summary)


def load_ground_truth(path: Path, limit: int | None) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                row = json.loads(line)
                records.append(row)
            if limit and len(records) >= limit:
                break
    return records


def validate_optional_dependencies(run_bertscore: bool, run_ragas: bool) -> None:
    missing = []
    if run_bertscore:
        missing.extend(missing_modules(["bert_score"]))
    if run_ragas:
        missing.extend(missing_modules(["datasets", "ragas"]))
    if missing:
        modules = ", ".join(sorted(set(missing)))
        raise RuntimeError(f"Missing optional QA metric dependencies: {modules}")


def missing_modules(module_names: list[str]) -> list[str]:
    import importlib.util

    return [name for name in module_names if importlib.util.find_spec(name) is None]


def create_llm() -> Any:
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("myAPIKey") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing myAPIKey or OPENAI_API_KEY in environment.")

    return ChatOpenAI(
        api_key=api_key,
        model=os.getenv("QA_BENCHMARK_OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        temperature=float(os.getenv("QA_BENCHMARK_TEMPERATURE", "0.0")),
        streaming=False,
        max_tokens=int(os.getenv("QA_BENCHMARK_MAX_TOKENS", "512")),
    )


def generate_predictions(
    config_id: str,
    ground_truth: list[dict[str, Any]],
    reranked_root: Path,
    top_k: int,
    llm: Any,
) -> list[dict[str, Any]]:
    config_meta = CONFIGS[config_id]
    config = resolve_config(config_meta)
    chunk_by_id = load_chunk_map(config)
    reranked_by_query = load_reranked_by_query(reranked_root / config_id / "reranked_results.json")

    records = []
    for row in ground_truth:
        query_id = row["id"]
        reranked = reranked_by_query.get(query_id, {"results": []})
        contexts, metadata = build_contexts(reranked.get("results", []), chunk_by_id, top_k)
        start = time.perf_counter()
        answer = invoke_llm(llm, row["question"], contexts)
        latency = time.perf_counter() - start
        records.append(to_prediction_record(config_id, config_meta, row, answer, contexts, metadata, latency))
        print(f"{config_id} {query_id} latency={latency:.2f}s refusal={is_refusal(answer)}")
    return records


def resolve_config(config_meta: dict[str, str]) -> dict[str, Any]:
    config = load_config(ROOT / config_meta["config_path"])
    if config_meta["retrieval"] == "hybrid":
        return resolve_hybrid_paths(config)
    return resolve_dense_paths(config)


def load_chunk_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if config["strategy_id"] == "parent_child_180s_45s":
        chunks = load_parent_chunks(config["chunks_dir"])
    else:
        chunks = load_chunks(config["chunks_dir"], strategy_id=config["strategy_id"])
    return {chunk["doc_id"]: chunk for chunk in chunks}


def load_reranked_by_query(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing reranked results: {path}")
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {row["query_id"]: row for row in rows}


def build_contexts(
    ranked_results: list[dict[str, Any]],
    chunk_by_id: dict[str, dict[str, Any]],
    top_k: int,
) -> tuple[list[str], list[dict[str, Any]]]:
    contexts = []
    metadata = []
    for result in ranked_results[:top_k]:
        chunk = chunk_by_id.get(result["doc_id"])
        if not chunk:
            continue
        contexts.append(str(chunk.get("text", "")))
        metadata.append({"doc_id": result["doc_id"], **dict(chunk.get("metadata", {}))})
    return contexts, metadata


def invoke_llm(llm: Any, question: str, contexts: list[str]) -> str:
    context = format_context(contexts)
    response = llm.invoke(PROMPT_TEMPLATE.format(context=context, question=question))
    return str(getattr(response, "content", response)).strip()


def format_context(contexts: list[str]) -> str:
    if not contexts:
        return "(Không có ngữ cảnh được truy xuất.)"
    return "\n\n".join(f"[Đoạn {idx}]\n{context}" for idx, context in enumerate(contexts, start=1))


def to_prediction_record(
    config_id: str,
    config_meta: dict[str, str],
    row: dict[str, Any],
    answer: str,
    contexts: list[str],
    metadata: list[dict[str, Any]],
    latency: float,
) -> dict[str, Any]:
    has_answer = row.get("category") != "no_answer" and bool(row.get("evidence"))
    return {
        "query_id": row["id"],
        "config_id": config_id,
        "chunk_family": config_meta["family"],
        "category": row.get("category", ""),
        "question": row["question"],
        "ground_truth": row.get("answer", NO_ANSWER_TEMPLATE),
        "generated_answer": answer,
        "contexts": contexts,
        "context_metadata": metadata,
        "has_answer": has_answer,
        "is_refusal": is_refusal(answer),
        "latency_seconds": latency,
    }


def compute_summary(
    config_id: str,
    records: list[dict[str, Any]],
    run_bertscore: bool,
    run_ragas: bool,
) -> dict[str, Any]:
    answerable = [record for record in records if record.get("has_answer") is True]
    summary = {
        "config_id": config_id,
        "chunk_family": CONFIGS[config_id]["family"],
        "total_count": len(records),
        "answerable_count": len(answerable),
        "mean_latency_seconds": mean(record.get("latency_seconds", 0.0) for record in records),
        **compute_no_answer_metrics(records),
    }
    if run_bertscore:
        summary.update(compute_bertscore_metrics(records))
    if run_ragas:
        summary.update(compute_ragas_metrics(records))
    return summary


def mean(values: Any) -> float:
    items = [float(value) for value in values]
    return sum(items) / len(items) if items else 0.0


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(path: Path, summary: dict[str, dict[str, Any]]) -> None:
    lines = ["# QA Metrics Benchmark Report", "", "## Answerable QA quality", ""]
    lines.append("| Config | Chunk family | BERTScore F1 | Faithfulness | Answer relevancy | Context precision | Context recall | Mean latency |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for row in summary.values():
        lines.append(
            f"| {row['config_id']} | {row['chunk_family']} | {fmt(row.get('bertscore_f1'))} | "
            f"{fmt(row.get('ragas_faithfulness'))} | {fmt(row.get('ragas_answer_relevancy'))} | "
            f"{fmt(row.get('ragas_context_precision'))} | {fmt(row.get('ragas_context_recall'))} | "
            f"{fmt(row.get('mean_latency_seconds'))} |"
        )
    lines.extend(["", "## No-answer robustness", ""])
    lines.append("| Config | Chunk family | Refusal accuracy | False answer rate | Exact template rate | Mean latency |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for row in summary.values():
        lines.append(
            f"| {row['config_id']} | {row['chunk_family']} | {fmt(row.get('refusal_accuracy'))} | "
            f"{fmt(row.get('false_answer_rate'))} | {fmt(row.get('refusal_template_rate'))} | "
            f"{fmt(row.get('mean_latency_seconds'))} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.4f}"


def format_summary(config_id: str, row: dict[str, Any]) -> str:
    return (
        f"{config_id} answerable={row['answerable_count']} no_answer={row['no_answer_count']} "
        f"refusal={row['refusal_accuracy']:.4f} false_answer={row['false_answer_rate']:.4f}"
    )


if __name__ == "__main__":
    main()
