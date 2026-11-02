from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_questions(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 20 or len({row.get("id") for row in rows}) != 20:
        raise ValueError("questions file must contain exactly 20 unique records")
    required = {"id", "question", "answer", "evidence"}
    if any(set(row) != required for row in rows):
        raise ValueError("each question must contain exactly id, question, answer, evidence")
    return rows


def select_questions(
    questions: list[dict[str, Any]],
    *,
    offset: int = 0,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if offset < 0:
        raise ValueError("offset phải lớn hơn hoặc bằng 0")
    if limit is not None and limit < 1:
        raise ValueError("limit phải lớn hơn 0")
    end = offset + limit if limit is not None else None
    selected = questions[offset:end]
    if not selected:
        raise ValueError("Không có câu hỏi nào trong khoảng đã chọn")
    return selected


def _usage_from_chunk(chunk: Any) -> dict[str, int]:
    usage = getattr(chunk, "usage_metadata", None) or {}
    return {
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
    }


def _citation_contract(
    response: dict[str, Any],
    document_count: int,
) -> tuple[bool, bool]:
    text = str(response.get("text", ""))
    indices = [int(value) for value in re.findall(r"\[(\d+)\]", text)]
    indices_valid = all(index < document_count for index in indices)
    highest = max(indices, default=-1)
    array_names = (
        "video_url",
        "title",
        "filename",
        "start_timestamp",
        "end_timestamp",
        "confidence",
    )
    arrays = [response.get(key) for key in array_names]
    lengths = [len(value) for value in arrays if isinstance(value, list)]
    aligned = (
        len(lengths) == len(array_names)
        and len(set(lengths)) == 1
        and (highest < 0 or lengths[0] > highest)
    )
    return indices_valid, aligned


async def benchmark_question(rag_core: Any, question: dict[str, Any], top_k: int) -> dict[str, Any]:
    os.environ["RAG_CONTEXT_TOP_K"] = str(top_k)
    context_started = time.perf_counter()
    context = await rag_core.get_context(question["question"], chat_history="", expand_query=False)
    context_seconds = time.perf_counter() - context_started
    documents = json.loads(context)

    chain = rag_core.get_answer_chain()
    generation_started = time.perf_counter()
    first_token = None
    chunks = []
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    async for chunk in chain.astream(
        {
            "context": context,
            "question": question["question"],
            "chat_history": "",
        }
    ):
        content = getattr(chunk, "content", "") or ""
        if content and first_token is None:
            first_token = time.perf_counter() - generation_started
        chunks.append(content)
        current_usage = _usage_from_chunk(chunk)
        for key in usage:
            usage[key] = max(usage[key], current_usage[key])

    from src.rag_core.agents.tutor import _extract_tutor_json_payload

    raw_answer = "".join(chunks)
    response = _extract_tutor_json_payload(raw_answer) or {}
    indices_valid, arrays_aligned = _citation_contract(response, len(documents))
    generation_seconds = time.perf_counter() - generation_started
    return {
        "id": question["id"],
        "context_top_k": top_k,
        "context_document_count": len(documents),
        "context_chars": len(context),
        "context_seconds": context_seconds,
        "generation_ttft_seconds": first_token,
        "generation_seconds": generation_seconds,
        "total_seconds": context_seconds + generation_seconds,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "total_tokens": usage["total_tokens"],
        "citation_indices_valid": indices_valid,
        "metadata_arrays_aligned": arrays_aligned,
        "response_type": "rag" if response else "error",
        "expected_answer": question["answer"],
        "generated_answer": response.get("text", ""),
    }


async def run(args: argparse.Namespace) -> None:
    all_questions = load_questions(args.questions)
    questions = select_questions(
        all_questions,
        offset=args.offset,
        limit=args.limit,
    )
    if args.repeats < 1:
        raise ValueError("repeats phải lớn hơn 0")
    os.environ["RAG_CONTEXT_TOP_K"] = str(args.context_top_k)
    from src.rag_core import resource_manager

    args.output_dir.mkdir(parents=True, exist_ok=True)
    is_full_run = args.offset == 0 and args.limit is None
    suffix = (
        ""
        if is_full_run
        else f"_offset_{args.offset}_count_{len(questions)}"
    )
    output = (
        args.output_dir
        / f"context_top_{args.context_top_k}{suffix}.jsonl"
    )
    rag_core = resource_manager.get_rag_core()
    total = args.repeats * len(questions)
    completed = 0
    with output.open("w", encoding="utf-8") as file:
        for _repeat in range(args.repeats):
            for question in questions:
                row = await benchmark_question(
                    rag_core,
                    question,
                    args.context_top_k,
                )
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
                file.flush()
                completed += 1
                print(
                    f"[context_top_k={args.context_top_k}] "
                    f"{completed}/{total}",
                    flush=True,
                )
    print(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark direct Tutor context and generation latency.")
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--context-top-k", type=int, choices=(10, 7, 5), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
