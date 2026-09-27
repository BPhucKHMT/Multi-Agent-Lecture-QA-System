"""Quiz Agent tạo câu hỏi trắc nghiệm từ context bài giảng.

Agent này luôn retrieval trước khi sinh quiz để câu hỏi bám sát transcript/video
thay vì model tự bịa kiến thức. Output gồm Markdown để hiển thị trực tiếp và
metadata citation để frontend có thể render nguồn tham khảo.
"""

import json
import re
from typing import List, Literal, Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.generation.llm_model import get_llm
from src.rag_core import resource_manager
from src.shared.metrics import measure_rag_stage
from src.rag_core.state import State


class QuizQuestion(BaseModel):
    question_type: Literal["multiple_choice", "true_false", "short_answer"] = Field(
        default="multiple_choice",
        description="Dạng câu hỏi: trắc nghiệm, đúng/sai hoặc trả lời ngắn",
    )
    question: str = Field(description="Nội dung câu hỏi")
    options: List[str] = Field(
        default_factory=list,
        description="Các lựa chọn; rỗng với câu trả lời ngắn",
    )
    correct_answer: str = Field(description="Đáp án tham khảo nội bộ")
    explanation: str = Field(description="Giải thích ngắn gọn bám sát transcript")
    video_url: str = Field(description="URL video tương ứng")
    video_title: str = Field(description="Tiêu đề bài giảng chứa kiến thức")
    timestamp: str = Field(description="Thời điểm trong video (HH:MM:SS)")

class QuizOutput(BaseModel):
    quizzes: List[QuizQuestion] = Field(description="Danh sách các câu trắc nghiệm")


_QUESTION_COUNT_PATTERN = re.compile(
    r"\b([1-9]\d*)\s*(?:câu(?:\s+hỏi)?|questions?)\b", re.IGNORECASE
)
_REQUESTED_QUESTION_COUNT_PATTERN = re.compile(
    r"\b(?:tạo|soạn|viết|chọn|lấy|create|generate|select|choose|pick)"
    r"\s+(?:(?:ra|đúng|quiz|exactly)\s+)?([1-9]\d*)\s*"
    r"(?:câu(?:\s+hỏi)?|questions?)\b",
    re.IGNORECASE,
)
_SOURCE_QUESTION_PREFIX_PATTERN = re.compile(
    r"\b(?:từ|trong|bộ|danh\s+sách|ngân\s+hàng|from|among|bank\s+of)\s*$",
    re.IGNORECASE,
)
_OPTION_COUNT_PATTERN = re.compile(
    r"\b([1-9]\d*)\s*(?:lựa\s*chọn|phương\s*án|options?|choices?)\b",
    re.IGNORECASE,
)


def _quiz_error_response(reason: str) -> dict:
    return {
        "text": f"Lỗi tạo quiz: {reason}",
        "video_url": [],
        "title": [],
        "filename": [],
        "start_timestamp": [],
        "end_timestamp": [],
        "confidence": [],
        "type": "error",
    }



def _canonical_correct_answer(options: list[str], answer: object) -> Optional[str]:
    if not isinstance(answer, str):
        return None
    if answer in options:
        return answer

    normalized = answer.strip().casefold()
    matches = []
    for option in options:
        if not isinstance(option, str):
            continue
        if option.strip().casefold() == normalized:
            matches.append(option)
            continue
        labeled = re.match(r"^\s*([A-Za-z])[.)]\s*(.+?)\s*$", option)
        if labeled and normalized in {
            labeled.group(1).casefold(), labeled.group(2).strip().casefold()
        }:
            matches.append(option)
    return matches[0] if len(matches) == 1 else None


def _positive_int(value) -> Optional[int]:
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _text_setting(args: dict, name: str, default: str = "") -> str:
    value = args.get(name, default)
    return value if isinstance(value, str) else default


def _quiz_settings(args: dict, query: str) -> dict:
    question_type = _text_setting(args, "question_type", "multiple_choice").strip().lower()
    question_type = {
        "multiple": "multiple_choice",
        "mcq": "multiple_choice",
        "multiple-choice": "multiple_choice",
        "true/false": "true_false",
        "đúng/sai": "true_false",
        "short answer": "short_answer",
        "trả lời ngắn": "short_answer",
    }.get(question_type, question_type)
    if question_type not in {"multiple_choice", "true_false", "short_answer"}:
        question_type = "multiple_choice"

    question_count = args.get("num_questions")
    if question_count is None:
        question_count = args.get("number_of_questions")
    question_count = _positive_int(question_count)
    query_text = query if isinstance(query, str) else ""
    if question_count is None:
        matches = list(_QUESTION_COUNT_PATTERN.finditer(query_text))
        if len(matches) == 1:
            match = matches[0]
            prefix = query_text[max(0, match.start() - 24):match.start()]
            if not _SOURCE_QUESTION_PREFIX_PATTERN.search(prefix):
                question_count = int(match.group(1))
        elif len(matches) > 1:
            requested = list(_REQUESTED_QUESTION_COUNT_PATTERN.finditer(query_text))
            if len(requested) == 1:
                question_count = int(requested[0].group(1))

    option_count = _positive_int(args.get("options_per_question"))
    if question_type == "multiple_choice":
        if args.get("options_per_question_from_query") is True or option_count is None:
            match = _OPTION_COUNT_PATTERN.search(query_text)
            if match:
                option_count = int(match.group(1))
        if option_count is not None and option_count < 2:
            option_count = None
        if option_count is None and args.get("options_per_question_from_query") is not True:
            option_count = 4
    elif question_type == "true_false":
        option_count = 2
    else:
        option_count = None

    tags = args.get("tags")
    include_answers = args.get("include_answers", True)
    include_explanations = args.get("include_explanations", True)
    return {
        "topic": _text_setting(args, "topic"),
        "question_type": question_type,
        "num_questions": question_count,
        "difficulty": _text_setting(args, "difficulty"),
        "language": _text_setting(args, "language", "vi"),
        "options_per_question": option_count,
        "target_audience": _text_setting(args, "target_audience"),
        "include_answers": include_answers if isinstance(include_answers, bool) else True,
        "include_explanations": (
            include_explanations if isinstance(include_explanations, bool) else True
        ),
        "tags": [tag for tag in tags if isinstance(tag, str)] if isinstance(tags, list) else [],
    }

def _extract_quiz_json_payload(raw: str):
    """Parse JSON quiz khi LLM trả raw JSON hoặc markdown fenced JSON."""
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    fenced_match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if fenced_match:
        text = fenced_match.group(1).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    obj_match = re.search(r"(\{[\s\S]*\})", text)
    if not obj_match:
        return None

    try:
        return json.loads(obj_match.group(1))
    except Exception:
        return None


async def node_quiz(state: State):
    """Chạy Quiz node: truy hồi, sinh và chuẩn hóa quiz theo tool arguments."""
    messages = state.get("messages", [])
    if not messages:
        return {"response": {}}

    last_message = messages[-1]
    query = ""
    quiz_args = {}
    tool_calls = state.get("tool_calls")
    if not tool_calls and hasattr(last_message, "tool_calls"):
        tool_calls = last_message.tool_calls

    for tool_call in tool_calls or []:
        if tool_call.get("name") != "GenerateQuiz":
            continue
        args = tool_call.get("args") or {}
        quiz_args = args if isinstance(args, dict) else {}
        query = quiz_args.get("query", "")
        if not query:
            topic = quiz_args.get("topic", "")
            question_count = quiz_args.get("num_questions") or quiz_args.get("number_of_questions")
            difficulty = quiz_args.get("difficulty", "")
            if topic:
                query = f"Tạo quiz về {topic}"
                if question_count:
                    query += f", {question_count} câu"
                if difficulty:
                    query += f", độ khó {difficulty}"
        break

    if not query:
        query = next(
            (message.content for message in reversed(messages) if message.type == "human"),
            last_message.content,
        )
    settings = _quiz_settings(quiz_args, query)
    if quiz_args.get("num_questions_from_query") is True and settings["num_questions"] is None:
        return {"response": _quiz_error_response("Không xác định được số câu yêu cầu.")}
    if quiz_args.get("options_per_question_from_query") is True and settings["options_per_question"] is None:
        return {"response": _quiz_error_response("Không xác định được số lựa chọn yêu cầu.")}

    retriever = resource_manager.get_vector_retriever()
    reranker = resource_manager.get_quiz_reranker()
    from langchain_core.runnables import RunnableLambda

    with measure_rag_stage("retrieval"):
        docs = (
            await retriever.ainvoke(query)
            if hasattr(retriever, "ainvoke")
            else await retriever.aget_relevant_documents(query)
        )
    rerank_chain = RunnableLambda(
        lambda d: reranker.rerank(d, query)[:5]
    ).with_config(run_name="rag_rerank")
    with measure_rag_stage("rerank"):
        reranked_docs = await rerank_chain.ainvoke(docs)
    with measure_rag_stage("format"):
        context_str = json.dumps(
            [
                {
                    "content": doc.page_content,
                    "url": doc.metadata.get("video_url", ""),
                    "title": doc.metadata.get("title", "Video bài giảng"),
                    "timestamp": doc.metadata.get("start_timestamp", ""),
                }
                for doc in reranked_docs
            ],
            ensure_ascii=False,
        )

    llm = get_llm()
    parser = JsonOutputParser(pydantic_object=QuizOutput)
    prompt = ChatPromptTemplate.from_template("""
Bạn là chuyên gia khảo thí bài giảng. Dùng VIDEO TRANSCRIPT để tạo quiz kiểm tra hiểu biết và tư duy, không hỏi máy móc.

YÊU CẦU:
- Tạo đúng số câu trong cài đặt; nếu num_questions là null, theo số nêu trong yêu cầu gốc; nếu người dùng không nêu số thì tạo 3 câu.
- Dạng multiple_choice: tạo đúng options_per_question lựa chọn; nếu trường này là null, theo số trong yêu cầu gốc; nếu không yêu cầu số lựa chọn thì tạo 4 (A, B, C, D).
- Dạng true_false: tạo đúng hai lựa chọn Đúng/Sai theo ngôn ngữ yêu cầu.
- Dạng short_answer: options phải là mảng rỗng; không biến câu trả lời ngắn thành câu trắc nghiệm.
- Dùng đúng difficulty, language, topic, target_audience và tags khi được cung cấp; nếu language là other, theo ngôn ngữ được nêu trong yêu cầu gốc.
- Câu hỏi kiểm tra khái niệm, nguyên lý hoặc tư duy; tránh hỏi số liệu ghi nhớ máy móc.
- Mỗi câu phải có video_url, video_title và timestamp chính xác từ transcript.
- Luôn tạo correct_answer và explanation trong JSON nội bộ; hệ thống sẽ bỏ trường nào người dùng yêu cầu ẩn.
- Giải thích ngắn gọn, tự nhiên; viết nội dung theo ngôn ngữ yêu cầu.

DỮ LIỆU TRANSCRIPT:
{context}

Yêu cầu gốc của người dùng:
{query}

Cài đặt quiz:
{quiz_settings}

{format_instructions}
Trả về JSON nguyên thủy theo format, không dùng markdown fence.
""")

    llm_chain = prompt | llm
    chain = llm_chain | parser
    invoke_input = {
        "context": context_str,
        "query": query,
        "quiz_settings": json.dumps(settings, ensure_ascii=False),
        "format_instructions": parser.get_format_instructions(),
    }

    try:
        with measure_rag_stage("answer"):
            result = await chain.ainvoke(
                invoke_input, config={"tags": ["final_answer_json"]}
            )
    except Exception as parse_error:
        try:
            with measure_rag_stage("answer"):
                raw_result = await llm_chain.ainvoke(
                    invoke_input, config={"tags": ["final_answer_json"]}
                )
            raw_content = (
                raw_result.content
                if hasattr(raw_result, "content")
                else str(raw_result)
            )
            repaired = _extract_quiz_json_payload(raw_content)
            if not repaired:
                raise ValueError("Invalid json output")
            result = QuizOutput.model_validate(repaired).model_dump()
        except Exception as fallback_error:
            return {"response": _quiz_error_response(str(fallback_error or parse_error))}

    try:
        questions = result["quizzes"]
        expected_count = settings["num_questions"]
        if expected_count is not None and len(questions) != expected_count:
            raise ValueError(f"Quiz phải có đúng {expected_count} câu hỏi")

        text_parts = ["### 📝 Bộ câu hỏi dựa trên bài giảng:\n"]
        urls = []
        titles = []
        timestamps = []
        public_questions = []
        expected_type = settings["question_type"]
        expected_options = settings["options_per_question"]

        for index, question in enumerate(questions, 1):
            question_type = question.get("question_type", expected_type)
            if question_type != expected_type:
                raise ValueError("Dạng câu hỏi được sinh không khớp yêu cầu")
            options = question.get("options")
            if question_type == "short_answer":
                options = []
            elif (
                not isinstance(options, list)
                or (expected_options is not None and len(options) != expected_options)
            ):
                raise ValueError(
                    f"Mỗi câu phải có đúng {expected_options} lựa chọn"
                    if expected_options is not None
                    else "Câu hỏi nhiều lựa chọn phải có options dạng danh sách"
                )
            if question_type != "short_answer":
                correct_answer = _canonical_correct_answer(
                    options, question.get("correct_answer")
                )
                if correct_answer is None:
                    raise ValueError("Đáp án đúng phải trùng một trong các lựa chọn")
                question["correct_answer"] = correct_answer

            question["question_type"] = question_type
            question["options"] = options
            text_parts.append(f"**Câu {index}:** {question['question']}\n")
            text_parts.extend(f"- {option}\n" for option in options)

            display_title = question.get("video_title") or "bài giảng"
            timestamp = question["timestamp"]
            video_url = question["video_url"]
            video_timestamp = timestamp.replace(":", "m", 1).replace(":", "s") if ":" in timestamp else timestamp
            text_parts.append(
                f"\n> 📖 *Gợi ý: Xem lại [{display_title} tại {timestamp}]"
                f"({video_url}&t={video_timestamp})*\n"
            )
            if settings["include_answers"]:
                text_parts.append(f"\n**Đáp án tham khảo:** {question['correct_answer']}\n")
            if settings["include_explanations"]:
                text_parts.append(f"\n**Giải thích:** {question['explanation']}\n")
            text_parts.append("\n---\n")

            public_question = dict(question)
            if not settings["include_answers"]:
                public_question.pop("correct_answer", None)
            if not settings["include_explanations"]:
                public_question.pop("explanation", None)
            public_questions.append(public_question)

            if video_url not in urls:
                urls.append(video_url)
                titles.append(question.get("video_title", f"Video bài giảng cho câu {index}"))
                timestamps.append(timestamp)

        data = {
            "text": "".join(text_parts),
            "video_url": urls,
            "title": titles,
            "filename": ["quiz_source"] * len(urls),
            "start_timestamp": timestamps,
            "end_timestamp": timestamps,
            "confidence": ["high"] * len(urls),
            "type": "quiz",
            "quizzes": public_questions,
        }
    except Exception as error:
        data = _quiz_error_response(str(error))

    return {"response": data}
