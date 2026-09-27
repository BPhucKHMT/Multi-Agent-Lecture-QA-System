"""LangGraph Multi-Agent Supervisor workflow.

Module này là điểm điều phối chính của AI engine. Supervisor nhận lịch sử chat,
chuẩn hóa input người dùng, chọn đúng một tool/agent chuyên trách rồi chuyển
state sang node tương ứng.

Các nhánh xử lý chính:
- Tutor: truy hồi bài giảng bằng RAG và trả citation.
- Coding: sinh/chạy/sửa code Python trong sandbox khi phù hợp.
- Math: sinh SymPy, kiểm chứng và diễn giải lời giải bằng LaTeX.
- Quiz: tạo câu hỏi trắc nghiệm từ context bài giảng.
- Direct: trả lời chào hỏi/câu hỏi xã giao không cần retrieval.

Response cuối cùng được backend stream về frontend và lưu vào PostgreSQL.
"""


from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

import httpx

from src.shared.metrics import AGENT_NODE_DURATION, SUPERVISOR_FALLBACKS

from typing import List, Optional, Union
import logging
import json
import time
import asyncio
import inspect

from src.generation.llm_model import get_supervisor_llm, get_llm
from src.generation.jev_router import JEV_MODEL, route_with_jev
from src.rag_core.state import State
from src.rag_core.agents.tutor import node_tutor
from src.rag_core.agents.quiz import node_quiz
from src.rag_core.agents.coding import build_coding_subgraph
from src.rag_core.agents.math import build_math_subgraph

from src.rag_core.utils import _extract_tool_args_from_state
from src.rag_core.agents.direct import node_direct_answer

logger = logging.getLogger(__name__)

llm = get_supervisor_llm()


@tool("AskTutor")
def ask_tutor_tool(query: str) -> str:
    """Dùng khi người dùng hỏi lý thuyết môn học cần truy hồi tri thức."""
    return query


@tool("CodeAssistant")
def code_assistant_tool(query: str) -> str:
    """Dùng khi yêu cầu liên quan đến code hoặc sửa lỗi lập trình."""
    return query


@tool("MathSolver")
def math_solver_tool(query: str) -> str:
    """Dùng khi người dùng cần giải bài toán hoặc suy luận toán học."""
    return query


@tool("GenerateQuiz")
def generate_quiz_tool(
    query: str = "",
    topic: str = "",
    difficulty: str = "",
    num_questions: Optional[int] = None,
    number_of_questions: Optional[int] = None,
    language: str = "",
    question_type: str = "",
    options_per_question: Optional[int] = None,
    target_audience: str = "",
    include_answers: bool = True,
    include_explanations: bool = True,
    tags: Optional[list[str]] = None,
) -> str:
    """Dùng khi người dùng muốn tạo quiz/trắc nghiệm."""
    details = {
        "query": query,
        "topic": topic,
        "difficulty": difficulty,
        "num_questions": num_questions,
        "number_of_questions": number_of_questions,
        "language": language,
        "question_type": question_type,
        "options_per_question": options_per_question,
        "target_audience": target_audience,
        "include_answers": include_answers,
        "include_explanations": include_explanations,
        "tags": tags or [],
    }
    return json.dumps(details, ensure_ascii=False)


@tool("AskGeneral")
def ask_general_tool(query: str) -> str:
    """Dùng khi người dùng chào hỏi, tán gẫu, hoặc hỏi các câu hỏi chung ( ví dụ hôm nay ăn gì, chơi gì) không liên quan đến kiến thức ML, AI, toán hoặc lập trình."""
    return query


SUPERVISOR_TOOLS = [
    ask_tutor_tool,
    code_assistant_tool,
    math_solver_tool,
    generate_quiz_tool,
    ask_general_tool,
]

SUPERVISOR_ROUTE_CRITERIA: dict[str, str] = {
    "AskTutor": "Kiến thức học thuật hoặc lý thuyết cần truy hồi bài giảng; ưu tiên khi phân vân với AskGeneral.",
    "MathSolver": "Bài toán, phép tính, chứng minh, đạo hàm, tích phân hoặc suy luận toán học.",
    "CodeAssistant": "Viết, giải thích, sửa lỗi code hoặc câu hỏi về cú pháp lập trình.",
    "GenerateQuiz": "Yêu cầu tạo quiz hoặc câu hỏi trắc nghiệm.",
    "AskGeneral": "Chào hỏi, xã giao hoặc câu hỏi chung không cần truy hồi bài giảng.",
}

SUPERVISOR_SYSTEM_PROMPT = (
    "Bạn là một Supervisor (Bộ điều phối) thông minh. Nhiệm vụ của bạn là phân loại yêu cầu của người dùng.\n\n"

    "CÁC CÔNG CỤ CÓ SẴN:\n"
    "1. AskTutor: Dùng khi hỏi về nội dung học thuật, lý thuyết liên quan đến AI, Machine Learning, Deep Learning "
    "(ví dụ: diffusion model, loss function, transformers, CNN, LLM, attention, gradient descent, etc.) "
    "hoặc bất kỳ kiến thức chuyên môn nào.\n"
    "2. MathSolver: Dùng khi giải toán, tính toán công thức, đạo hàm, tích phân, chứng minh toán học.\n"
    "3. CodeAssistant: Dùng khi viết code, sửa lỗi lập trình hoặc hỏi về cú pháp.\n"
    "4. GenerateQuiz: Dùng khi người dùng muốn làm trắc nghiệm.\n"
    "5. AskGeneral: CHỈ dùng cho chào hỏi, xã giao, hoặc hỏi về chatbot.\n\n"

    "QUY TẮC CỰC KỲ QUAN TRỌNG:\n"
    "- Bạn là một bộ điều phối thuần túy. BẮT BUỘC phải gọi đúng 1 công cụ.\n"
    "- KHÔNG được trả lời nội dung.\n"
    "- Khi đã quyết định gọi công cụ, chỉ trả về tool call. Không viết câu trả lời giải thích thêm.\n\n"

    "QUY TẮC PHÂN LOẠI (ƯU TIÊN CAO):\n"
    "- Nếu câu hỏi chứa thuật ngữ kỹ thuật (ví dụ: diffusion, transformer, CNN, loss, model, training, AI) "
    "→ LUÔN chọn AskTutor.\n"
    "- Nếu có bất kỳ nghi ngờ nào giữa AskTutor và AskGeneral → CHỌN AskTutor.\n"
    "- AskGeneral CHỈ dùng khi KHÔNG có nội dung học thuật.\n"
)

supervisor_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SUPERVISOR_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

supervisor_llm = llm.bind_tools(SUPERVISOR_TOOLS)




def _extract_text_from_ai_content(content) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
            continue
        if not isinstance(block, dict):
            continue
        text = block.get("text")
        if isinstance(text, str):
            parts.append(text)
        elif isinstance(text, dict):
            value = text.get("value")
            if isinstance(value, str):
                parts.append(value)
    return "".join(parts)


def _coerce_tool_args(raw_args) -> dict:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, str):
                return {"query": parsed}
        except Exception:
            pass
        return {"query": raw_args}
    return {}


def _extract_tool_calls_from_intermediate_steps(intermediate_steps) -> Optional[List[dict]]:
    if not isinstance(intermediate_steps, list):
        return None

    normalized = []
    for step in intermediate_steps:
        if not isinstance(step, tuple) or not step:
            continue
        action = step[0]
        tool_name = getattr(action, "tool", None)
        tool_input = _coerce_tool_args(getattr(action, "tool_input", {}))
        if not tool_name:
            continue
        if tool_name == "GenerateQuiz":
            if "num_questions" not in tool_input and "number_of_questions" in tool_input:
                tool_input["num_questions"] = tool_input.get("number_of_questions")
        normalized.append({"name": tool_name, "args": tool_input})
    if not normalized:
        return None
    return list(reversed(normalized))


def jev_fallback_reason(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
        return "jev_429" if status_code == 429 else "jev_other"
    if isinstance(error, httpx.TimeoutException):
        return "jev_timeout"
    if isinstance(error, ValueError):
        return "jev_invalid"
    return "jev_other"


def _record_supervisor_fallback(error: Exception) -> str:
    reason = jev_fallback_reason(error)
    try:
        SUPERVISOR_FALLBACKS.labels(reason=reason).inc()
    except Exception as metric_error:
        logger.warning(
            "Supervisor fallback metric failed (%s)",
            type(metric_error).__name__,
        )
    return reason

async def node_supervisor(
    state: State,
    config: RunnableConfig | None = None,
):
    """Điều phối bằng Jev qua Experiential Labs, fallback sang GPT-6 Luna nếu lỗi."""
    messages = state.get("messages", [])

    try:
        chat_history = messages[:-1] if messages and isinstance(messages[-1], HumanMessage) else messages
        input_text = ""
        if messages:
            last_message = messages[-1]
            if isinstance(last_message, HumanMessage):
                input_text = str(getattr(last_message, "content", "") or "")
            elif isinstance(last_message, AIMessage):
                input_text = _extract_text_from_ai_content(getattr(last_message, "content", ""))

        if not input_text:
            for message in reversed(messages):
                if isinstance(message, HumanMessage):
                    input_text = str(getattr(message, "content", "") or "")
                    break

        jev_history = []
        for message in chat_history:
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                continue
            content = _extract_text_from_ai_content(getattr(message, "content", ""))
            if content:
                jev_history.append({"role": role, "content": content})

        try:
            from langchain_core.runnables import RunnableLambda

            async def _call_jev(_):
                return await route_with_jev(
                    input_text,
                    jev_history,
                    SUPERVISOR_ROUTE_CRITERIA,
                )

            jev_chain = RunnableLambda(_call_jev).with_config(
                run_name="jev_supervisor", metadata={"model": JEV_MODEL}
            )
            invoke_cfg = {"config": config} if config is not None else {}
            decision = await jev_chain.ainvoke(None, **invoke_cfg)
            if (
                not isinstance(decision, dict)
                or decision.get("name") not in SUPERVISOR_ROUTE_CRITERIA
                or not isinstance(decision.get("args"), dict)
            ):
                raise ValueError("Experiential Jev returned an invalid supervisor tool call")
        except Exception as error:
            reason = _record_supervisor_fallback(error)
            logger.warning(
                "Experiential Jev supervisor failed; falling back to GPT-6 Luna "
                "(reason=%s error=%s fallback_error=true)",
                reason,
                type(error).__name__,
            )
        else:
            return {"tool_calls": [decision]}

        formatted_prompt = supervisor_prompt.format_messages(
            input=input_text,
            chat_history=chat_history,
            agent_scratchpad=[],
        )
        invoke_kwargs = {"config": config} if config is not None else {}
        response = await supervisor_llm.ainvoke(formatted_prompt, **invoke_kwargs)
        tool_calls = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                args = tool_call["args"] or {}
                if tool_call["name"] == "GenerateQuiz":
                    if "num_questions" not in args and "number_of_questions" in args:
                        args["num_questions"] = args.get("number_of_questions")
                tool_calls.append({"name": tool_call["name"], "args": args})

        if not tool_calls:
            if len(input_text.split()) > 4:
                logger.info("Luna supervisor fallback: route to AskTutor for a long query.")
                tool_calls = [{"name": "AskTutor", "args": {"query": input_text}}]
            else:
                logger.info("Luna supervisor fallback: route to AskGeneral for a short query.")
                tool_calls = [{"name": "AskGeneral", "args": {"query": input_text}}]

        return {"messages": [response], "tool_calls": tool_calls}
    except Exception as error:
        logger.error("Supervisor error: %s", type(error).__name__)
        return {
            "tool_calls": [
                {"name": "AskGeneral", "args": {"query": "Lỗi hệ thống điều phối."}}
            ]
        }



def router(state: State) -> str:
    """Chuyển tool call của Supervisor thành tên node LangGraph kế tiếp."""
    messages = state.get("messages", [])
    last_message = messages[-1]

    # Kiểm tra tool_calls
    tool_calls = state.get("tool_calls")
    if not tool_calls and hasattr(last_message, "tool_calls"):
        tool_calls = getattr(last_message, "tool_calls", None)

    decision = "direct" # Mặc định là General Talk

    if tool_calls:
        tool_call = tool_calls[0]
        name = tool_call.get("name")
        if name == "AskTutor":
            decision = "tutor"
        elif name == "CodeAssistant":
            decision = "coding"
        elif name == "MathSolver":
            decision = "math"
        elif name == "GenerateQuiz":
            decision = "quiz"
        elif name == "AskGeneral":
            decision = "direct"

    logger.info(
        "supervisor_router decision=%s tool_call_count=%d",
        decision,
        len(tool_calls or []),
    )
    return decision

# Prepare subgraphs
coding_subgraph = build_coding_subgraph()
math_subgraph = build_math_subgraph()

async def node_coding_wrapper(
    state: State,
    config: RunnableConfig | None = None,
):
    """Adapter giữa State chung của graph và Coding subgraph riêng."""
    args = _extract_tool_args_from_state(state, "CodeAssistant")
    query = args.get("query", "")
    invoke_kwargs = {"config": config} if config is not None else {}
    res = await coding_subgraph.ainvoke(
        {"query": query, "retry_count": 0},
        **invoke_kwargs,
    )
    return {"response": res.get("response", {})}

async def node_math_wrapper(
    state: State,
    config: RunnableConfig | None = None,
):
    """Adapter giữa State chung của graph và Math subgraph riêng."""
    args = _extract_tool_args_from_state(state, "MathSolver")
    query = args.get("query", "")
    invoke_kwargs = {"config": config} if config is not None else {}
    try:
        res = await math_subgraph.ainvoke({"query": query}, **invoke_kwargs)
        response = res.get("response", {})
        
        # Đảm bảo type luôn là math cho agent này
        if isinstance(response, dict):
            response["type"] = "math"
    except Exception as e:
        logger.error(f"Error in node_math_wrapper: {e}")
        response = {
            "text": f"Gặp lỗi khi giải toán: {str(e)}",
            "type": "math",
            "video_url": [], "title": [], "filename": [],
            "start_timestamp": [], "end_timestamp": [], "confidence": [],
        }
        
    return {"response": response}


graph = StateGraph(State)

def timed_node(name: str, node_func):
    """Bọc node để log thời gian chạy mà không đổi signature LangGraph."""
    try:
        parameters = inspect.signature(node_func).parameters.values()
        accepts_config = any(
            parameter.name == "config"
            or parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in parameters
        )
    except (TypeError, ValueError):
        accepts_config = False

    async def wrapper(
        state: State,
        config: RunnableConfig | None = None,
    ):
        start_time = time.perf_counter()
        outcome = "success"
        try:
            if accepts_config:
                result = node_func(state, config=config)
            else:
                result = node_func(state)
            if inspect.isawaitable(result):
                result = await result
            if (
                isinstance(result, dict)
                and isinstance(result.get("response"), dict)
                and result["response"].get("type") == "error"
            ):
                outcome = "error"
            return result
        except BaseException:
            outcome = "error"
            raise
        finally:
            elapsed = time.perf_counter() - start_time
            try:
                AGENT_NODE_DURATION.labels(node=name, outcome=outcome).observe(elapsed)
            except Exception as metric_error:
                logger.warning(
                    "Agent node duration metric failed (%s)",
                    type(metric_error).__name__,
                )
            logger.info(f"[PERFORMANCE LOG] Node '{name}' thực thi mất {elapsed:.2f}s")
    return wrapper

graph.add_node("supervisor", timed_node("supervisor", node_supervisor))
graph.add_node("tutor", timed_node("tutor", node_tutor))
graph.add_node("quiz", timed_node("quiz", node_quiz))
graph.add_node("coding", timed_node("coding", node_coding_wrapper))
graph.add_node("math", timed_node("math", node_math_wrapper))
graph.add_node("direct", timed_node("direct", node_direct_answer))

graph.add_edge(START, "supervisor")
graph.add_conditional_edges("supervisor", router, {
    "tutor": "tutor",
    "coding": "coding",
    "math": "math",
    "quiz": "quiz",
    "direct": "direct"
})
graph.add_edge("tutor", END)
graph.add_edge("coding", END)
graph.add_edge("math", END)
graph.add_edge("quiz", END)
graph.add_edge("direct", END)

workflow = graph.compile()

