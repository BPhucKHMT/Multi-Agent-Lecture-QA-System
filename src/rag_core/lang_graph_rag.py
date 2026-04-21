"""
Module này định nghĩa một hệ thống Multi-Agent Supervisor
sử dụng StateGraph để điều phối giữa các agent con như Tutor, Coding, Math, và Quiz 
 dựa trên truy vấn của người dùng. Supervisor sẽ phân tích yêu cầu và quyết định agent nào phù hợp nhất để xử lý, 
sau đó gọi agent đó với các tham số cần thiết. Kết quả cuối cùng sẽ được trả về cho người dùng dưới dạng một phản hồi tổng hợp.

Output của mỗi agent con sẽ có định dạng chuẩn để dễ dàng tổng hợp và trả về cho người dùng.
Supervisor sẽ sử dụng một LLM để phân tích truy vấn và quyết định agent nào nên được gọi, dựa trên nội dung của truy vấn và lịch sử chat.

"""


from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.callbacks import BaseCallbackHandler

from typing import List
import logging
import json
import time
import asyncio
import inspect

from src.generation.llm_model import get_supervisor_llm, get_llm
from src.rag_core.state import State
from src.rag_core.agents.tutor import node_tutor
from src.rag_core.agents.quiz import node_quiz
from src.rag_core.agents.coding import build_coding_subgraph
from src.rag_core.agents.math import build_math_subgraph
from src.rag_core.router_patterns import (
    FORCE_MATH_PATTERNS,
    GREETING_PATTERNS,
    QUIZ_PATTERNS,
    CODING_PATTERNS
)
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
    num_questions: int | None = None,
    number_of_questions: int | None = None,
    language: str = "",
    question_type: str = "",
    options_per_question: int | None = None,
    target_audience: str = "",
    include_answers: bool = True,
    include_explanations: bool = True,
    tags: list[str] | None = None,
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
    """Dùng khi người dùng chào hỏi, tán gẫu, hoặc hỏi các câu hỏi chung không liên quan đến bài học."""
    return query


SUPERVISOR_TOOLS = [
    ask_tutor_tool,
    code_assistant_tool,
    math_solver_tool,
    generate_quiz_tool,
    ask_general_tool,
]

SUPERVISOR_SYSTEM_PROMPT = (
    "Bạn là một Supervisor (Bộ điều phối) thông minh. Nhiệm vụ của bạn là phân loại yêu cầu của người dùng.\n\n"
    "CÁC CÔNG CỤ CÓ SẴN:\n"
    "1. AskTutor: Dùng khi hỏi về nội dung học thuật, lý thuyết cần tra cứu video.\n"
    "2. MathSolver: Dùng khi giải toán, tính toán, đạo hàm, tích phân, chứng minh.\n"
    "3. CodeAssistant: Dùng khi viết code, sửa lỗi lập trình hoặc hỏi về công nghệ.\n"
    "4. GenerateQuiz: Dùng khi người dùng muốn làm trắc nghiệm.\n"
    "5. AskGeneral: Dùng cho mọi trường hợp khác: chào hỏi, tán gẫu, giới thiệu bản thân, hỏi xem bạn làm được gì.\n\n"
    "QUY TẮC CỰC KỲ QUAN TRỌNG:\n"
    "- Bạn là một bộ điều phối thuần túy (Pure Dispatcher). BẠN BẮT BUỘC PHẢI GỌI 1 CÔNG CỤ.\n"
    "- KHÔNG được tự ý trả lời nội dung hay giải thích gì thêm trong nội dung phản hồi.\n"
    "- Hãy phân tích kỹ để chọn đúng chuyên gia phù hợp nhất.\n"
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


def _extract_tool_calls_from_intermediate_steps(intermediate_steps) -> list[dict] | None:
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


def _should_force_math_route(input_text: str) -> bool:
    normalized = str(input_text or "").lower()
    if not normalized.strip():
        return False
    return any(pattern in normalized for pattern in FORCE_MATH_PATTERNS)


def _should_force_quiz_route(input_text: str) -> bool:
    normalized = str(input_text or "").lower()
    return any(pattern in normalized for pattern in QUIZ_PATTERNS)


def _should_force_coding_route(input_text: str) -> bool:
    normalized = str(input_text or "").lower()
    return any(pattern in normalized for pattern in CODING_PATTERNS)


def _is_greeting_input(input_text: str) -> bool:
    normalized = str(input_text or "").strip().lower()
    if not normalized:
        return False
    return any(normalized == pattern or normalized.startswith(f"{pattern} ") for pattern in GREETING_PATTERNS)

async def node_supervisor(state: State):
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

        # 1. Hệ thống điều hướng cứng (Deterministic Steering)
        if _should_force_math_route(input_text):
            return {
                "tool_calls": [{"name": "MathSolver", "args": {"query": input_text}}],
            }
        
        if _should_force_quiz_route(input_text):
            return {
                "tool_calls": [{"name": "GenerateQuiz", "args": {"query": input_text}}],
            }

        if _should_force_coding_route(input_text):
            return {
                "tool_calls": [{"name": "CodeAssistant", "args": {"query": input_text}}],
            }

        # 2. Sử dụng LLM với bind_tools để phân phối (Pure Supervisor)
        formatted_prompt = supervisor_prompt.format_messages(
            input=input_text,
            chat_history=chat_history,
            agent_scratchpad=[]
        )
        
        response = await supervisor_llm.ainvoke(formatted_prompt)
        
        tool_calls = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls.append({
                    "name": tc["name"],
                    "args": tc["args"]
                })

        # Logic Fallback nếu LLM không gọi tool (Pure Supervisor fallback)
        if not tool_calls:
            # Nếu input có vẻ là câu hỏi kiến thức dài -> AskTutor
            if len(input_text.split()) > 4:
                logger.info("Supervisor fallback: Forced AskTutor due to long query without tool call.")
                tool_calls = [{"name": "AskTutor", "args": {"query": input_text}}]
            else:
                # Ngược lại mặc định là AskGeneral (Chào hỏi/Xã giao)
                logger.info("Supervisor fallback: Forced AskGeneral for short query without tool call.")
                tool_calls = [{"name": "AskGeneral", "args": {"query": input_text}}]
        
        # Luôn trả về tool_calls, không trả về AIMessage text ở node này để đảm bảo Pure Routing
        return {"messages": [response], "tool_calls": tool_calls}

    except Exception as e:
        logger.error(f"Supervisor error: {e}")
        return {"tool_calls": [{"name": "AskGeneral", "args": {"query": f"Lỗi hệ thống điều phối: {str(e)}"}}]}



def router(state: State) -> str:
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

async def node_coding_wrapper(state: State):
    args = _extract_tool_args_from_state(state, "CodeAssistant")
    query = args.get("query", "")
    res = await coding_subgraph.ainvoke({"query": query, "retry_count": 0})
    return {"response": res.get("response", {})}

async def node_math_wrapper(state: State):
    args = _extract_tool_args_from_state(state, "MathSolver")
    query = args.get("query", "")
    try:
        res = await math_subgraph.ainvoke({"query": query})
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
    async def wrapper(state: State):
        start_time = time.time()
        
        # Gọi node function
        result = node_func(state)
        
        # Nếu kết quả trả về là một awaitable (coroutine), ta phải await nó.
        # Điều này giúp xử lý an toàn cả các node định nghĩa bằng 'def' và 'async def'.
        if inspect.isawaitable(result):
            result = await result
            
        elapsed = time.time() - start_time
        logger.info(f"[PERFORMANCE LOG] Node '{name}' thực thi mất {elapsed:.2f}s")
        return result
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

# Hàm dùng để đo hiệu năng của từng node và tổng thể workflow, cũng như đếm token sử dụng trong LLM calls ( sẽ xóa sau khi hoàn thiện )
class PerformanceCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        super().__init__()
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def on_llm_end(self, response, **kwargs):
        try:
            if hasattr(response, "llm_output") and response.llm_output and "token_usage" in response.llm_output:
                usage = response.llm_output["token_usage"]
                self.total_input_tokens += usage.get("prompt_tokens", usage.get("input_tokens", 0))
                self.total_output_tokens += usage.get("completion_tokens", usage.get("output_tokens", 0))
            elif hasattr(response, "generations") and response.generations:
                for gen_list in response.generations:
                    for gen in gen_list:
                        msg = getattr(gen, "message", None)
                        if msg and hasattr(msg, "usage_metadata") and msg.usage_metadata:
                            self.total_input_tokens += msg.usage_metadata.get("input_tokens", 0)
                            self.total_output_tokens += msg.usage_metadata.get("output_tokens", 0)
        except Exception:
            pass


def call_agent(chat_history: List[dict]) -> dict:
    """
    Chạy hệ thống Multi-Agent Supervisor với lịch sử chat.
    """
    langchain_messages = []
    for msg in chat_history:
        if msg["role"] == "user":
            langchain_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            langchain_messages.append(AIMessage(content=msg["content"]))
            
    initial_state = {"messages": langchain_messages}
    
    cb = PerformanceCallbackHandler()
    start_time = time.time()
    
    final_state = workflow.invoke(initial_state, config={"callbacks": [cb]})
    
    elapsed = time.time() - start_time
    # Log tổng thời gian và token usage của toàn bộ workflow
    logger.info(
        f"[PERFORMANCE LOG] Tổng thời gian AI Workflow (call_agent): {elapsed:.2f}s | "
        f"Tổng Token Input: {cb.total_input_tokens} | "
        f"Tổng Token Output: {cb.total_output_tokens}"
    )
    print(
        f"[TOKEN METRICS] mode=chat input={cb.total_input_tokens} "
        f"output={cb.total_output_tokens} total={cb.total_input_tokens + cb.total_output_tokens}"
    )
    
    return final_state.get("response", {})
