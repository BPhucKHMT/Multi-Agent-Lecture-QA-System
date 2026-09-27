"""Client gửi typed evaluations của Jev qua Experiential Labs."""
import logging
from collections.abc import Mapping
from os import getenv
from time import perf_counter

import httpx

from src.shared.metrics import JEV_DURATION, JEV_REQUESTS

logger = logging.getLogger(__name__)

JEV_OUTCOMES = frozenset({
    "success",
    "http_429",
    "http_other",
    "timeout",
    "invalid",
    "other_error",
})

JEV_MODEL = "jev-latest"
EXPERIENTIAL_API_BASE_URL = "https://api.experientiallabs.ai/v1"
JEV_SYSTEMONE_PATH = "/systemone"
REQUEST_TIMEOUT_SECONDS = 15.0

_jev_http_client = None


def open_jev_http_client() -> httpx.AsyncClient:
    """Tạo hoặc trả về HTTP client dùng chung trong một vòng đời ứng dụng."""
    global _jev_http_client
    if _jev_http_client is None or _jev_http_client.is_closed:
        _jev_http_client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            limits=httpx.Limits(keepalive_expiry=90.0),
        )
    return _jev_http_client


async def close_jev_http_client() -> None:
    """Đóng HTTP client dùng chung khi backend dừng."""
    global _jev_http_client
    client = _jev_http_client
    _jev_http_client = None
    if client is not None and not client.is_closed:
        await client.aclose()
QUIZ_COUNT_CHOICES = {
    "unspecified": "Không nêu số lượng câu.",
    "other": "Có yêu cầu số câu ngoài 1–20; giữ nguyên số trong câu hỏi gốc.",
    **{
        str(count): f"Người dùng yêu cầu chính xác {count} câu hỏi."
        for count in range(1, 21)
    },
}
QUIZ_DIFFICULTY_CHOICES = {
    "unspecified": "Không nêu độ khó cụ thể.",
    "easy": "Dễ.",
    "medium": "Trung bình.",
    "hard": "Khó.",
}
QUIZ_LANGUAGE_CHOICES = {
    "unspecified": "Không nêu ngôn ngữ cụ thể.",
    "vi": "Tiếng Việt.",
    "en": "Tiếng Anh.",
    "other": "Người dùng yêu cầu ngôn ngữ khác; đọc tên ngôn ngữ trong câu hỏi gốc.",
}
QUIZ_TYPE_CHOICES = {
    "multiple_choice": "Trắc nghiệm nhiều lựa chọn; mặc định nếu không nêu loại.",
    "true_false": "Đúng/Sai.",
    "short_answer": "Trả lời ngắn, không có lựa chọn.",
}
QUIZ_OPTION_CHOICES = {
    "unspecified": "Không nêu số lựa chọn; mặc định 4 cho trắc nghiệm nhiều lựa chọn.",
    "other": "Có yêu cầu số lựa chọn ngoài 2–20; giữ nguyên số trong câu hỏi gốc.",
    **{
        str(count): f"Mỗi câu trắc nghiệm có chính xác {count} lựa chọn."
        for count in range(2, 21)
    },
}


def _choice(
    answers: Mapping[str, object],
    key: str,
    allowed: Mapping[str, str],
) -> str:
    answer = answers.get(key)
    choice = answer.get("choice") if isinstance(answer, dict) else None
    if not isinstance(choice, str) or choice not in allowed:
        raise ValueError(f"Experiential Jev returned an invalid {key} choice")
    return choice


def _probability(answers: Mapping[str, object], key: str) -> float:
    answer = answers.get(key)
    probability = answer.get("noul") if isinstance(answer, dict) else None
    if (
        not isinstance(probability, (int, float))
        or isinstance(probability, bool)
        or not 0 <= probability <= 1
    ):
        raise ValueError(f"Experiential Jev returned an invalid {key} noul")
    return float(probability)


def _quiz_tool_args(
    input_text: str,
    answers: Mapping[str, object],
) -> dict[str, object]:
    question_type = _choice(answers, "question_type", QUIZ_TYPE_CHOICES)
    question_count = _choice(answers, "num_questions", QUIZ_COUNT_CHOICES)
    difficulty = _choice(answers, "difficulty", QUIZ_DIFFICULTY_CHOICES)
    language = _choice(answers, "language", QUIZ_LANGUAGE_CHOICES)
    option_count = _choice(answers, "options_per_question", QUIZ_OPTION_CHOICES)
    args: dict[str, object] = {
        "query": input_text,
        "question_type": question_type,
        "include_answers": _probability(answers, "omit_answers") <= 0.5,
        "include_explanations": _probability(answers, "omit_explanations") <= 0.5,
    }
    if question_count == "other":
        args["num_questions"] = None
        args["num_questions_from_query"] = True
    elif question_count != "unspecified":
        args["num_questions"] = int(question_count)
    if difficulty != "unspecified":
        args["difficulty"] = difficulty
    if language in {"vi", "en", "other"}:
        args["language"] = language
    if question_type == "multiple_choice":
        if option_count == "other":
            args["options_per_question"] = None
            args["options_per_question_from_query"] = True
        elif option_count == "unspecified":
            args["options_per_question"] = 4
        else:
            args["options_per_question"] = int(option_count)
    elif question_type == "true_false":
        args["options_per_question"] = 2
    return args



def _record_jev_metrics(outcome: str, elapsed: float) -> None:
    if outcome not in JEV_OUTCOMES:
        outcome = "other_error"
    try:
        JEV_REQUESTS.labels(outcome=outcome).inc()
    except Exception as error:
        logger.warning("Jev request metric failed (%s)", type(error).__name__)
    try:
        JEV_DURATION.labels(outcome=outcome).observe(elapsed)
    except Exception as error:
        logger.warning("Jev duration metric failed (%s)", type(error).__name__)


async def route_with_jev(
    input_text: str,
    history: list[dict[str, str]],
    route_criteria: Mapping[str, str],
) -> dict[str, object]:
    """Yêu cầu Experiential Jev chọn route và trích xuất quiz fields dạng typed."""
    api_key = getenv("EXPERIENTIAL_API_KEY", "").strip()
    if not api_key:
        raise ValueError("EXPERIENTIAL_API_KEY is required")
    if not route_criteria:
        raise ValueError("At least one supervisor route is required")

    questions = {
        "route": {
            "type": "choice",
            "instructions": (
                "Chọn đúng một agent. Câu hỏi giải thích khái niệm học thuật hoặc thuật ngữ "
                "kỹ thuật như diffusion, transformer, CNN, loss, model, training, AI, attention "
                "thì chọn AskTutor; yêu cầu tính toán, đạo hàm, tích phân hoặc chứng minh thì "
                "chọn MathSolver; viết/sửa code thì chọn CodeAssistant; yêu cầu tạo quiz thì "
                "chọn GenerateQuiz; chỉ chào hỏi hoặc xã giao không học thuật mới chọn AskGeneral. "
                "Khi phân vân giữa AskTutor và AskGeneral, ưu tiên AskTutor."
            ),
            "criteria": dict(route_criteria),
        },
        "num_questions": {
            "type": "choice",
            "instructions": (
                "Trích số câu quiz. Chọn unspecified nếu không nêu số; chọn other nếu số ngoài "
                "1–20 để hệ thống dùng đúng số có trong câu hỏi gốc."
            ),
            "criteria": QUIZ_COUNT_CHOICES,
        },
        "difficulty": {
            "type": "choice",
            "instructions": "Chọn độ khó chỉ khi người dùng nêu rõ; nếu không, chọn unspecified.",
            "criteria": QUIZ_DIFFICULTY_CHOICES,
        },
        "language": {
            "type": "choice",
            "instructions": (
                "Chọn ngôn ngữ nếu người dùng nêu rõ. Chọn other nếu yêu cầu ngôn ngữ không phải "
                "tiếng Việt hoặc tiếng Anh; không có yêu cầu thì chọn unspecified."
            ),
            "criteria": QUIZ_LANGUAGE_CHOICES,
        },
        "question_type": {
            "type": "choice",
            "instructions": (
                "Chọn dạng quiz được yêu cầu; nếu không nêu thì mặc định multiple_choice."
            ),
            "criteria": QUIZ_TYPE_CHOICES,
        },
        "options_per_question": {
            "type": "choice",
            "instructions": (
                "Với trắc nghiệm nhiều lựa chọn, trích đúng số lựa chọn 2–20. Chọn other nếu "
                "người dùng nêu số lớn hơn 20 để dùng số trong câu hỏi gốc; nếu không nêu số, "
                "chọn unspecified. Không dùng trường này cho đúng/sai hoặc trả lời ngắn."
            ),
            "criteria": QUIZ_OPTION_CHOICES,
        },
        "omit_answers": {
            "type": "noul",
            "instructions": "Người dùng có yêu cầu không hiển thị đáp án đúng không?",
            "criteria": {
                "true": "Người dùng yêu cầu ẩn hoặc không cung cấp đáp án.",
                "false": "Người dùng không yêu cầu ẩn đáp án; mặc định có đáp án.",
            },
        },
        "omit_explanations": {
            "type": "noul",
            "instructions": "Người dùng có yêu cầu không hiển thị phần giải thích không?",
            "criteria": {
                "true": "Người dùng yêu cầu bỏ phần giải thích.",
                "false": "Người dùng không yêu cầu bỏ giải thích.",
            },
        },
    }
    payload = {
        "model": JEV_MODEL,
        "state": {"current_request": input_text, "conversation_history": history},
        "questions": questions,
    }
    request_url = f"{EXPERIENTIAL_API_BASE_URL}{JEV_SYSTEMONE_PATH}"
    headers = {"Authorization": f"Bearer {api_key}"}
    started: float | None = None
    outcome = "other_error"
    try:
        client = _jev_http_client
        if client is not None and not client.is_closed:
            started = perf_counter()
            response = await client.post(request_url, headers=headers, json=payload)
        else:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                started = perf_counter()
                response = await client.post(request_url, headers=headers, json=payload)
        response.raise_for_status()

        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("Invalid Experiential Jev response")
        answers = body.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("Invalid Experiential Jev answers")
        route = _choice(answers, "route", route_criteria)
        args: dict[str, object] = {"query": input_text}
        if route == "GenerateQuiz":
            args = _quiz_tool_args(input_text, answers)
        outcome = "success"
    except httpx.HTTPStatusError as error:
        outcome = "http_429" if error.response.status_code == 429 else "http_other"
        raise
    except httpx.TimeoutException:
        outcome = "timeout"
        raise
    except ValueError:
        outcome = "invalid"
        raise
    except Exception:
        outcome = "other_error"
        raise
    finally:
        if started is not None:
            _record_jev_metrics(outcome, perf_counter() - started)
    return {"name": route, "args": args}
