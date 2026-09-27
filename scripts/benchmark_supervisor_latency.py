"""Đo thời gian phân loại Supervisor bằng Jev và GPT-6 Luna."""
import argparse
import asyncio
import os
import sys
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean, median
from time import perf_counter
from typing import Any, Optional


SAMPLE_QUESTIONS = [
    ("Toán học", "Tính đạo hàm của f(x)=x^3-3x tại x=2.", "MathSolver"),
    ("Toán học", "Giải phương trình 2x + 7 = 19.", "MathSolver"),
    ("Lý thuyết AI", "Giải thích Multi-Head Attention trong Transformer bằng ví dụ.", "AskTutor"),
    ("Lý thuyết AI", "CNN khác RNN thế nào khi xử lý dữ liệu tuần tự?", "AskTutor"),
    ("Lập trình", "Viết hàm Python tìm kiếm nhị phân trên danh sách tăng dần.", "CodeAssistant"),
    ("Lập trình", "Sửa lỗi chỉ số trong vòng lặp Python: for i in range(len(items)+1): print(items[i])", "CodeAssistant"),
    ("Tạo Quiz", "Tạo 3 câu trắc nghiệm về QuickSort, mỗi câu có 4 lựa chọn và đáp án.", "GenerateQuiz"),
    ("Tạo Quiz", "Tạo 2 câu hỏi đúng/sai về đệ quy, không cần giải thích.", "GenerateQuiz"),
    ("Chào hỏi", "Xin chào, hôm nay bạn thế nào?", "AskGeneral"),
    ("Xã giao", "Cảm ơn bạn đã giúp tôi. Chúc bạn buổi tối vui vẻ!", "AskGeneral"),
]

RouteDecision = dict[str, Any]
Classifier = Callable[[str], Awaitable[RouteDecision]]


@dataclass(frozen=True)
class Measurement:
    category: str
    query: str
    repetition: int
    model: str
    route: Optional[str]
    expected_route: Optional[str]
    elapsed_seconds: float
    error_type: Optional[str]

    @property
    def successful_latency(self) -> Optional[float]:
        return None if self.error_type else self.elapsed_seconds

def summarize_latencies(
    samples: Sequence[Optional[float]],
) -> Optional[dict[str, float]]:
    successful = [sample for sample in samples if sample is not None]
    if not successful:
        return None
    return {
        "min": min(successful),
        "median": median(successful),
        "mean": fmean(successful),
        "max": max(successful),
    }


def paired_mean_delta(
    jev_samples: Sequence[Optional[float]],
    luna_samples: Sequence[Optional[float]],
) -> Optional[float]:
    deltas = [
        luna - jev
        for jev, luna in zip(jev_samples, luna_samples)
        if jev is not None and luna is not None
    ]
    return fmean(deltas) if deltas else None


def route_match_counts(measurements: Sequence[Measurement]) -> tuple[int, int]:
    routed = [
        item
        for item in measurements
        if item.expected_route is not None and item.route is not None
    ]
    return (
        sum(item.route == item.expected_route for item in routed),
        len(routed),
    )


def error_label(error: Exception) -> str:
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code is None:
        return type(error).__name__
    try:
        body = response.json()
    except (AttributeError, ValueError):
        body = None
    details = body.get("error") if isinstance(body, dict) else None
    if isinstance(details, dict):
        safe_details = [
            value
            for value in (details.get("type"), details.get("code"))
            if isinstance(value, str) and value.isidentifier()
        ]
        if safe_details:
            return (
                f"{type(error).__name__} (HTTP {status_code}, "
                f"{'/'.join(safe_details)})"
            )
    return f"{type(error).__name__} (HTTP {status_code})"

async def classify_jev(
    query: str,
    route_with_jev: Callable[..., Awaitable[RouteDecision]],
    route_criteria: dict[str, str],
) -> RouteDecision:
    return await route_with_jev(query, [], route_criteria)


async def classify_luna(
    query: str,
    supervisor_prompt: Any,
    supervisor_llm: Any,
) -> RouteDecision:
    formatted_prompt = supervisor_prompt.format_messages(
        input=query,
        chat_history=[],
        agent_scratchpad=[],
    )
    response = await supervisor_llm.ainvoke(formatted_prompt)
    tool_calls = getattr(response, "tool_calls", None) or []
    if tool_calls:
        call = tool_calls[0]
        return {"name": call["name"], "args": call.get("args") or {}}

    route = "AskTutor" if len(query.split()) > 4 else "AskGeneral"
    return {"name": route, "args": {"query": query}}


async def _measure(
    category: str,
    query: str,
    expected_route: Optional[str],
    repetition: int,
    model: str,
    classifier: Classifier,
) -> Measurement:
    started = perf_counter()
    try:
        decision = await classifier(query)
    except Exception as error:
        return Measurement(
            category=category,
            query=query,
            repetition=repetition,
            model=model,
            route=None,
            expected_route=expected_route,
            elapsed_seconds=perf_counter() - started,
            error_type=error_label(error),
        )

    return Measurement(
        category=category,
        query=query,
        repetition=repetition,
        model=model,
        route=str(decision["name"]),
        expected_route=expected_route,
        elapsed_seconds=perf_counter() - started,
        error_type=None,
    )


async def run_benchmark(
    questions: Sequence[tuple[str, str, Optional[str]]],
    runs: int,
    classifiers: dict[str, Classifier],
    jev_interval_seconds: float = 0.0,
) -> list[Measurement]:
    measurements = []
    model_order = list(classifiers)
    last_jev_started = None
    for repetition in range(runs):
        for question_index, (category, query, expected_route) in enumerate(questions):
            order = model_order if (repetition + question_index) % 2 == 0 else model_order[::-1]
            for model in order:
                if model == "Jev" and last_jev_started is not None:
                    delay = jev_interval_seconds - (perf_counter() - last_jev_started)
                    if delay > 0:
                        print(f"Chờ {delay:.1f}s để giãn cách request Jev.")
                        await asyncio.sleep(delay)
                if model == "Jev":
                    last_jev_started = perf_counter()
                measurement = await _measure(
                    category,
                    query,
                    expected_route,
                    repetition + 1,
                    model,
                    classifiers[model],
                )
                measurements.append(measurement)
                expected = f", mong đợi {expected_route}" if expected_route else ""
                if measurement.error_type:
                    print(
                        f"[{category}, lượt {repetition + 1}] {model}: "
                        f"LỖI {measurement.error_type} "
                        f"({measurement.elapsed_seconds:.3f} giây){expected}"
                    )
                else:
                    match = (
                        "khớp"
                        if expected_route is None or measurement.route == expected_route
                        else "không khớp"
                    )
                    print(
                        f"[{category}, lượt {repetition + 1}] {model}: "
                        f"{measurement.route} ({measurement.elapsed_seconds:.3f} giây)"
                        f"{expected}; {match}"
                    )
    return measurements


def print_summary(
    measurements: Sequence[Measurement],
    jev_model: str,
    luna_model: str,
) -> None:
    print("\n=== Thống kê latency phía client (API + mạng + parse route) ===")
    for label in ("Jev", "GPT-6 Luna"):
        model_measurements = [
            item for item in measurements if item.model == label
        ]
        samples = [item.successful_latency for item in model_measurements]
        summary = summarize_latencies(samples)
        model_name = jev_model if label == "Jev" else luna_model
        if summary is None:
            print(f"{label} ({model_name}): không có lần gọi thành công")
        else:
            print(
                f"{label} ({model_name}): "
                f"min={summary['min']:.3f}s, median={summary['median']:.3f}s, "
                f"mean={summary['mean']:.3f}s, max={summary['max']:.3f}s"
            )

        expected_count = sum(
            item.expected_route is not None for item in model_measurements
        )
        if expected_count:
            correct, evaluated = route_match_counts(model_measurements)
            print(
                f"  Route đúng: {correct}/{evaluated} kết quả; "
                f"gọi thành công {evaluated}/{expected_count}"
            )

    jev_samples = [
        item.successful_latency for item in measurements if item.model == "Jev"
    ]
    luna_samples = [
        item.successful_latency for item in measurements if item.model == "GPT-6 Luna"
    ]
    paired_count = sum(
        jev is not None and luna is not None
        for jev, luna in zip(jev_samples, luna_samples)
    )
    total_pairs = min(len(jev_samples), len(luna_samples))
    delta = paired_mean_delta(jev_samples, luna_samples)
    if delta is None:
        print(
            "Chênh lệch ghép cặp (GPT-6 Luna − Jev): "
            f"không có cặp thành công (n=0/{total_pairs})."
        )
        return

    rounded_delta = round(delta, 3)
    if rounded_delta > 0:
        comparison = "GPT-6 Luna chậm hơn"
    elif rounded_delta < 0:
        comparison = "GPT-6 Luna nhanh hơn"
    else:
        comparison = "thời gian trung bình gần bằng nhau"
    print(
        f"Chênh lệch ghép cặp (GPT-6 Luna − Jev): "
        f"{delta:+.3f} giây ({comparison}; n={paired_count}/{total_pairs} cặp)."
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="So sánh thời gian classify của Supervisor dùng Jev và GPT-6 Luna."
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Số lượt chạy mỗi câu hỏi (mặc định: 1).",
    )
    parser.add_argument(
        "--jev-interval-seconds",
        type=float,
        default=15.0,
        help="Khoảng tối thiểu giữa các request Jev; thời gian chờ không tính vào latency.",
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Câu hỏi tùy chọn; bỏ trống để chạy mười câu mẫu.",
    )
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error("--runs phải lớn hơn hoặc bằng 1")
    if args.jev_interval_seconds < 0:
        parser.error("--jev-interval-seconds không được âm")
    return args


async def main(args: argparse.Namespace) -> int:
    root_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root_dir))

    from dotenv import load_dotenv

    load_dotenv(dotenv_path=root_dir / ".env", override=True)
    missing_keys = [
        name
        for name in ("EXPERIENTIAL_API_KEY", "myAPIKey")
        if not os.getenv(name, "").strip()
    ]
    if missing_keys:
        print("Thiếu cấu hình API key: " + ", ".join(missing_keys))
        return 2

    from src.generation.jev_router import (
        JEV_MODEL,
        close_jev_http_client,
        open_jev_http_client,
        route_with_jev,
    )
    from src.rag_core.lang_graph_rag import (
        SUPERVISOR_ROUTE_CRITERIA,
        supervisor_llm,
        supervisor_prompt,
    )

    async def jev_classifier(query: str) -> RouteDecision:
        return await classify_jev(query, route_with_jev, SUPERVISOR_ROUTE_CRITERIA)

    async def luna_classifier(query: str) -> RouteDecision:
        return await classify_luna(query, supervisor_prompt, supervisor_llm)

    query_text = " ".join(args.query).strip()
    questions = [("Tùy chọn", query_text, None)] if query_text else SAMPLE_QUESTIONS
    if not query_text and args.query:
        print("Câu hỏi truyền vào đang trống; dùng mười câu mẫu.")

    jev_model = JEV_MODEL
    luna_model = os.getenv(
        "OPENAI_SUPERVISOR_MODEL",
        os.getenv("OPENAI_MODEL", "gpt-6-luna"),
    ).strip()
    print(f"Mô hình Jev: {jev_model}")
    print(f"Mô hình Luna: {luna_model or 'gpt-6-luna'}")
    print(f"Số câu: {len(questions)}; số lượt/câu: {args.runs}\n")
    print(f"Khoảng giữa các request Jev: {args.jev_interval_seconds:.1f}s (ngoài thời gian đo)\n")

    open_jev_http_client()
    try:
        measurements = await run_benchmark(
            questions,
            args.runs,
            {"Jev": jev_classifier, "GPT-6 Luna": luna_classifier},
            args.jev_interval_seconds,
        )
    finally:
        await close_jev_http_client()
    print_summary(measurements, jev_model, luna_model)
    return 0


def cli(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(main(args))


if __name__ == "__main__":
    raise SystemExit(cli())
