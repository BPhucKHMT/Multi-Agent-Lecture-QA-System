import os
import sys
import builtins
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.rag_core import lang_graph_rag
from src.rag_core.state import State


class _FakeLLM:
    def invoke(self, _messages):
        return AIMessage(content="fallback")


class _FakeAction:
    def __init__(self, tool: str, tool_input):
        self.tool = tool
        self.tool_input = tool_input


class _FakeSupervisorExecutor:
    def __init__(self, output: str, intermediate_steps):
        self.output = output
        self.intermediate_steps = intermediate_steps
        self.invoked_with = None

    def invoke(self, payload):
        self.invoked_with = payload
        return {
            "output": self.output,
            "intermediate_steps": self.intermediate_steps,
        }


class _TrackableSupervisorExecutor(_FakeSupervisorExecutor):
    def __init__(self, output: str, intermediate_steps):
        super().__init__(output=output, intermediate_steps=intermediate_steps)
        self.invoke_calls = 0

    def invoke(self, payload):
        self.invoke_calls += 1
        return super().invoke(payload)


def test_node_supervisor_extracts_tool_call_from_agent_intermediate_steps(monkeypatch):
    monkeypatch.setattr(lang_graph_rag, "llm", _FakeLLM())
    fake_executor = _FakeSupervisorExecutor(
        output="Đang tạo quiz...",
        intermediate_steps=[
            (
                _FakeAction(
                    tool="GenerateQuiz",
                    tool_input={"topic": "Diffusion", "number_of_questions": 10},
                ),
                "ok",
            )
        ],
    )
    monkeypatch.setattr(lang_graph_rag, "supervisor_executor", fake_executor, raising=False)

    result = lang_graph_rag.node_supervisor(
        {"messages": [HumanMessage(content="tạo quiz diffusion")]}
    )

    assert fake_executor.invoked_with is not None
    assert fake_executor.invoked_with["input"] == "tạo quiz diffusion"
    assert result["tool_calls"][0]["name"] == "GenerateQuiz"
    assert result["tool_calls"][0]["args"]["topic"] == "Diffusion"
    assert result["tool_calls"][0]["args"]["num_questions"] == 10


def test_workflow_routes_quiz_from_supervisor_agent_tool_step(monkeypatch):
    monkeypatch.setattr(lang_graph_rag, "llm", _FakeLLM())
    fake_executor = _FakeSupervisorExecutor(
        output="Đang tạo quiz...",
        intermediate_steps=[(_FakeAction(tool="GenerateQuiz", tool_input={"topic": "CNN"}), "ok")],
    )
    monkeypatch.setattr(lang_graph_rag, "supervisor_executor", fake_executor, raising=False)

    def _node_quiz(_state):
        return {"response": {"type": "quiz"}}

    def _node_direct(_state):
        return {"response": {"type": "direct"}}

    graph = StateGraph(State)
    graph.add_node("supervisor", lang_graph_rag.node_supervisor)
    graph.add_node("quiz", _node_quiz)
    graph.add_node("direct", _node_direct)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lang_graph_rag.router,
        {"quiz": "quiz", "direct": "direct"},
    )
    graph.add_edge("quiz", END)
    graph.add_edge("direct", END)

    workflow = graph.compile()
    result = workflow.invoke({"messages": [HumanMessage(content="tạo quiz cnn")]})
    assert result["response"]["type"] == "quiz"


def test_workflow_routes_using_latest_tool_call_from_intermediate_steps(monkeypatch):
    monkeypatch.setattr(lang_graph_rag, "llm", _FakeLLM())
    fake_executor = _FakeSupervisorExecutor(
        output="Đã xác định tạo quiz.",
        intermediate_steps=[
            (_FakeAction(tool="AskTutor", tool_input={"query": "diffusion là gì"}), "ok"),
            (_FakeAction(tool="GenerateQuiz", tool_input={"topic": "Diffusion"}), "ok"),
        ],
    )
    monkeypatch.setattr(lang_graph_rag, "supervisor_executor", fake_executor, raising=False)

    def _node_quiz(_state):
        return {"response": {"type": "quiz"}}

    def _node_tutor(_state):
        return {"response": {"type": "rag"}}

    graph = StateGraph(State)
    graph.add_node("supervisor", lang_graph_rag.node_supervisor)
    graph.add_node("quiz", _node_quiz)
    graph.add_node("tutor", _node_tutor)
    graph.add_node("direct", lambda _state: {"response": {"type": "direct"}})
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lang_graph_rag.router,
        {"quiz": "quiz", "tutor": "tutor", "direct": "direct"},
    )
    graph.add_edge("quiz", END)
    graph.add_edge("tutor", END)
    graph.add_edge("direct", END)

    workflow = graph.compile()
    result = workflow.invoke({"messages": [HumanMessage(content="tạo quiz diffusion")]})
    assert result["response"]["type"] == "quiz"


def test_workflow_routes_math_solver_tool_to_math_node(monkeypatch):
    monkeypatch.setattr(lang_graph_rag, "llm", _FakeLLM())
    fake_executor = _FakeSupervisorExecutor(
        output="Đang xử lý bài toán...",
        intermediate_steps=[(_FakeAction(tool="MathSolver", tool_input={"query": "đạo hàm x^2"}), "ok")],
    )
    monkeypatch.setattr(lang_graph_rag, "supervisor_executor", fake_executor, raising=False)

    def _node_math(_state):
        return {"response": {"type": "math"}}

    def _node_direct(_state):
        return {"response": {"type": "direct"}}

    graph = StateGraph(State)
    graph.add_node("supervisor", lang_graph_rag.node_supervisor)
    graph.add_node("math", _node_math)
    graph.add_node("direct", _node_direct)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lang_graph_rag.router,
        {"math": "math", "direct": "direct"},
    )
    graph.add_edge("math", END)
    graph.add_edge("direct", END)

    workflow = graph.compile()
    result = workflow.invoke({"messages": [HumanMessage(content="tính đạo hàm x^2")]})
    assert result["response"]["type"] == "math"


def test_node_supervisor_forces_math_route_for_proof_pattern(monkeypatch):
    monkeypatch.setattr(lang_graph_rag, "llm", _FakeLLM())
    fake_executor = _TrackableSupervisorExecutor(
        output="Mình sẽ dùng tutor.",
        intermediate_steps=[(_FakeAction(tool="AskTutor", tool_input={"query": "chứng minh sigmoid là hàm lồi"}), "ok")],
    )
    monkeypatch.setattr(lang_graph_rag, "supervisor_executor", fake_executor, raising=False)

    result = lang_graph_rag.node_supervisor(
        {"messages": [HumanMessage(content="chứng minh sigmoid là hàm lồi")]}
    )

    assert fake_executor.invoke_calls == 0
    assert result["tool_calls"][0]["name"] == "MathSolver"
    assert result["tool_calls"][0]["args"]["query"] == "chứng minh sigmoid là hàm lồi"


def test_workflow_routes_proof_pattern_to_math_node(monkeypatch):
    monkeypatch.setattr(lang_graph_rag, "llm", _FakeLLM())
    fake_executor = _TrackableSupervisorExecutor(
        output="Mình sẽ dùng tutor.",
        intermediate_steps=[(_FakeAction(tool="AskTutor", tool_input={"query": "chứng minh bất đẳng thức"}), "ok")],
    )
    monkeypatch.setattr(lang_graph_rag, "supervisor_executor", fake_executor, raising=False)

    def _node_math(_state):
        return {"response": {"type": "math"}}

    def _node_tutor(_state):
        return {"response": {"type": "rag"}}

    graph = StateGraph(State)
    graph.add_node("supervisor", lang_graph_rag.node_supervisor)
    graph.add_node("math", _node_math)
    graph.add_node("tutor", _node_tutor)
    graph.add_node("direct", lambda _state: {"response": {"type": "direct"}})
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lang_graph_rag.router,
        {"math": "math", "tutor": "tutor", "direct": "direct"},
    )
    graph.add_edge("math", END)
    graph.add_edge("tutor", END)
    graph.add_edge("direct", END)

    workflow = graph.compile()
    result = workflow.invoke({"messages": [HumanMessage(content="chứng minh bất đẳng thức")]} )
    assert fake_executor.invoke_calls == 0
    assert result["response"]["type"] == "math"


def test_node_supervisor_maps_string_tool_input_to_query_arg(monkeypatch):
    monkeypatch.setattr(lang_graph_rag, "llm", _FakeLLM())
    fake_executor = _FakeSupervisorExecutor(
        output="Đã chọn trợ lý code.",
        intermediate_steps=[(_FakeAction(tool="CodeAssistant", tool_input="viết hàm sort"), "ok")],
    )
    monkeypatch.setattr(lang_graph_rag, "supervisor_executor", fake_executor, raising=False)

    result = lang_graph_rag.node_supervisor(
        {"messages": [HumanMessage(content="giúp mình viết hàm sort")]}
    )

    assert result["tool_calls"][0]["name"] == "CodeAssistant"
    assert result["tool_calls"][0]["args"]["query"] == "viết hàm sort"


def test_node_direct_answer_fallback_to_default_when_last_ai_content_empty():
    result = lang_graph_rag.node_direct_answer(
        {
            "messages": [
                HumanMessage(content="Giải thích giúp mình về CNN"),
                AIMessage(content=""),
            ]
        }
    )

    assert (
        result["response"]["text"]
        == "Mình chưa nhận được nội dung rõ ràng, bạn thử diễn đạt lại giúp mình nhé."
    )
    assert result["response"]["text"] != "Giải thích giúp mình về CNN"
    assert result["response"]["type"] == "direct"


def test_node_direct_answer_fallback_to_default_when_no_message_content():
    result = lang_graph_rag.node_direct_answer(
        {"messages": [HumanMessage(content=""), AIMessage(content="")]}
    )

    assert (
        result["response"]["text"]
        == "Mình chưa nhận được nội dung rõ ràng, bạn thử diễn đạt lại giúp mình nhé."
    )
    assert result["response"]["type"] == "direct"


def test_node_direct_answer_does_not_echo_when_last_message_is_human():
    user_text = "Đây là nội dung người dùng, không được echo."
    result = lang_graph_rag.node_direct_answer(
        {"messages": [AIMessage(content="Mình có thể hỗ trợ bạn."), HumanMessage(content=user_text)]}
    )

    assert (
        result["response"]["text"]
        == "Mình chưa nhận được nội dung rõ ràng, bạn thử diễn đạt lại giúp mình nhé."
    )
    assert result["response"]["text"] != user_text
    assert result["response"]["type"] == "direct"


def test_supervisor_prompt_requires_no_extra_text_when_calling_tool():
    assert "Khi đã quyết định gọi công cụ, chỉ trả về tool call." in lang_graph_rag.SUPERVISOR_SYSTEM_PROMPT
    assert "Không viết câu trả lời giải thích thêm" in lang_graph_rag.SUPERVISOR_SYSTEM_PROMPT


class _WorkflowWithoutLlmEvents:
    def invoke(self, *_args, **_kwargs):
        return {"response": {"text": "ok", "type": "direct"}}


def test_call_agent_prints_token_metrics(monkeypatch):
    outputs = []
    monkeypatch.setattr(lang_graph_rag, "workflow", _WorkflowWithoutLlmEvents(), raising=False)
    monkeypatch.setattr(builtins, "print", lambda message: outputs.append(message))

    response = lang_graph_rag.call_agent([{"role": "user", "content": "xin chao"}])

    assert response["text"] == "ok"
    assert any("[TOKEN METRICS]" in line for line in outputs)


def test_node_supervisor_falls_back_to_tutor_when_output_empty_and_no_tool_calls(monkeypatch):
    monkeypatch.setattr(lang_graph_rag, "llm", _FakeLLM())
    fake_executor = _FakeSupervisorExecutor(
        output="",
        intermediate_steps=[],
    )
    monkeypatch.setattr(lang_graph_rag, "supervisor_executor", fake_executor, raising=False)

    result = lang_graph_rag.node_supervisor(
        {"messages": [HumanMessage(content="linear regression là gì")]}
    )

    assert result["tool_calls"][0]["name"] == "AskTutor"
    assert result["tool_calls"][0]["args"]["query"] == "linear regression là gì"
