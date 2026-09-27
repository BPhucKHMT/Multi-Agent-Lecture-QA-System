import asyncio
import os
import sys
from pathlib import Path

import pytest
import httpx


from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.rag_core import lang_graph_rag
from src.rag_core.state import State

class FakeLLM:
    def __init__(self, tool_calls=None):
        self.tool_calls = tool_calls or []
        self.invoked_with = None

    async def ainvoke(self, messages, **kwargs):
        self.invoked_with = messages
        return AIMessage(content="", tool_calls=self.tool_calls)


class FailingLLM:
    async def ainvoke(self, messages, **kwargs):
        raise AssertionError("Luna fallback should not run when Jev succeeds")


@pytest.fixture(autouse=True)
def _isolate_jev_requests_in_unit_tests(monkeypatch):
    async def _jev_error(_input_text, _history, _route_criteria):
        raise RuntimeError("Experiential Jev disabled in unit tests")

    monkeypatch.setattr(lang_graph_rag, "route_with_jev", _jev_error)


class _MetricRecorder:
    def __init__(self):
        self.labels_calls = []
        self.inc_calls = 0
        self.observe_calls = []

    def labels(self, **labels):
        self.labels_calls.append(labels)
        return self

    def inc(self):
        self.inc_calls += 1

    def observe(self, value):
        self.observe_calls.append(value)


def _record_supervisor_fallbacks(monkeypatch):
    metric = _MetricRecorder()
    monkeypatch.setattr(lang_graph_rag, "SUPERVISOR_FALLBACKS", metric)
    return metric


def _record_node_duration(monkeypatch):
    metric = _MetricRecorder()
    monkeypatch.setattr(lang_graph_rag, "AGENT_NODE_DURATION", metric)
    return metric



def test_jev_supervisor_routes_to_agent_when_available(monkeypatch):
    async def _route(input_text, _history, _criteria):
        return {"name": "AskTutor", "args": {"query": input_text}}

    monkeypatch.setattr(lang_graph_rag, "route_with_jev", _route)
    monkeypatch.setattr(lang_graph_rag, "supervisor_llm", FailingLLM())

    result = asyncio.run(lang_graph_rag.node_supervisor({
        "messages": [
            HumanMessage(content="previous question"),
            AIMessage(content="previous response"),
            HumanMessage(content="giải thích self-attention"),
        ]
    }))

    assert result["tool_calls"] == [{
        "name": "AskTutor",
        "args": {"query": "giải thích self-attention"},
    }]


def test_jev_error_falls_back_to_luna_tool_call(monkeypatch):
    fake_luna = FakeLLM(tool_calls=[{
        "name": "MathSolver",
        "args": {"query": "solve this"},
        "id": "luna-call-1",
    }])
    monkeypatch.setattr(lang_graph_rag, "supervisor_llm", fake_luna)

    result = asyncio.run(lang_graph_rag.node_supervisor({
        "messages": [HumanMessage(content="solve this")]
    }))

    assert fake_luna.invoked_with is not None
    assert result["tool_calls"] == [{"name": "MathSolver", "args": {"query": "solve this"}}]


def test_jev_fallback_records_one_bounded_reason_even_when_luna_succeeds(monkeypatch):
    fallback_metric = _record_supervisor_fallbacks(monkeypatch)
    fake_luna = FakeLLM(tool_calls=[{
        "name": "MathSolver",
        "args": {"query": "solve this"},
        "id": "luna-call-1",
    }])

    async def _route(*_args):
        raise httpx.ReadTimeout("provider timeout")

    monkeypatch.setattr(lang_graph_rag, "route_with_jev", _route)
    monkeypatch.setattr(lang_graph_rag, "supervisor_llm", fake_luna)

    result = asyncio.run(lang_graph_rag.node_supervisor({
        "messages": [HumanMessage(content="solve this")]
    }))

    assert result["tool_calls"][0]["name"] == "MathSolver"
    assert fallback_metric.labels_calls == [{"reason": "jev_timeout"}]
    assert fallback_metric.inc_calls == 1



@pytest.mark.parametrize(
    ("node_result", "raises", "expected_outcome"),
    [
        ({"response": {"type": "error"}}, False, "error"),
        (None, True, "error"),
    ],
)
def test_timed_node_records_error_for_response_or_exception(
    monkeypatch,
    node_result,
    raises,
    expected_outcome,
):
    duration_metric = _record_node_duration(monkeypatch)

    async def _node(_state):
        if raises:
            raise RuntimeError("node failed")
        return node_result

    wrapped = lang_graph_rag.timed_node("direct", _node)
    if raises:
        with pytest.raises(RuntimeError, match="node failed"):
            asyncio.run(wrapped({}))
    else:
        assert asyncio.run(wrapped({})) == node_result

    assert duration_metric.labels_calls == [{
        "node": "direct",
        "outcome": expected_outcome,
    }]
    assert len(duration_metric.observe_calls) == 1


def test_nested_coding_subgraph_receives_runnable_config(monkeypatch):
    class _NestedSubgraph:
        def __init__(self):
            self.calls = []

        async def ainvoke(self, payload, **kwargs):
            self.calls.append((payload, kwargs))
            return {"response": {"type": "coding"}}

    nested = _NestedSubgraph()
    monkeypatch.setattr(lang_graph_rag, "coding_subgraph", nested)
    config = {"callbacks": ["parent-callback"]}

    result = asyncio.run(lang_graph_rag.node_coding_wrapper(
        {
            "tool_calls": [{
                "name": "CodeAssistant",
                "args": {"query": "viết hàm sort"},
            }],
        },
        config=config,
    ))

    assert result["response"]["type"] == "coding"
    assert nested.calls == [
        ({"query": "viết hàm sort", "retry_count": 0}, {"config": config})
    ]

def test_node_supervisor_extracts_tool_call_from_agent_intermediate_steps(monkeypatch):
    fake_llm = FakeLLM(tool_calls=[{
        "name": "GenerateQuiz",
        "args": {"topic": "Diffusion", "number_of_questions": 10},
        "id": "call-1"
    }])
    monkeypatch.setattr(lang_graph_rag, "supervisor_llm", fake_llm)

    result = asyncio.run(lang_graph_rag.node_supervisor(
        {"messages": [HumanMessage(content="làm thế nào để học tốt")]}
    ))

    assert fake_llm.invoked_with is not None
    assert result["tool_calls"][0]["name"] == "GenerateQuiz"
    assert result["tool_calls"][0]["args"]["topic"] == "Diffusion"
    assert result["tool_calls"][0]["args"]["num_questions"] == 10


def test_workflow_routes_quiz_from_supervisor_agent_tool_step(monkeypatch):
    fake_llm = FakeLLM(tool_calls=[{
        "name": "GenerateQuiz",
        "args": {"topic": "CNN"},
        "id": "call-2"
    }])
    monkeypatch.setattr(lang_graph_rag, "supervisor_llm", fake_llm)

    async def _node_quiz(_state):
        return {"response": {"type": "quiz"}}

    async def _node_direct(_state):
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
    result = asyncio.run(workflow.ainvoke({"messages": [HumanMessage(content="tạo quiz cnn")]}))
    assert result["response"]["type"] == "quiz"




def test_workflow_routes_math_solver_tool_to_math_node(monkeypatch):
    fake_llm = FakeLLM(tool_calls=[{
        "name": "MathSolver",
        "args": {"query": "đạo hàm x^2"},
        "id": "call-5"
    }])
    monkeypatch.setattr(lang_graph_rag, "supervisor_llm", fake_llm)

    async def _node_math(_state):
        return {"response": {"type": "math"}}

    async def _node_direct(_state):
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
    result = asyncio.run(workflow.ainvoke({"messages": [HumanMessage(content="tính đạo hàm x^2")]}))
    assert result["response"]["type"] == "math"



def test_workflow_routes_jev_math_choice_to_math_node(monkeypatch):
    async def _route(input_text, _history, _criteria):
        return {"name": "MathSolver", "args": {"query": input_text}}

    monkeypatch.setattr(lang_graph_rag, "route_with_jev", _route)
    monkeypatch.setattr(lang_graph_rag, "supervisor_llm", FailingLLM())

    async def _node_math(_state):
        return {"response": {"type": "math"}}

    async def _node_tutor(_state):
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
    result = asyncio.run(workflow.ainvoke({"messages": [HumanMessage(content="chứng minh bất đẳng thức")]}))
    assert result["response"]["type"] == "math"

@pytest.mark.parametrize(
    ("tool_name", "expected_node"),
    [
        ("AskTutor", "tutor"),
        ("CodeAssistant", "coding"),
        ("MathSolver", "math"),
        ("GenerateQuiz", "quiz"),
        ("AskGeneral", "direct"),
    ],
)
def test_supervisor_routes_every_legacy_tool(tool_name, expected_node):
    result = lang_graph_rag.router({
        "messages": [HumanMessage(content="test")],
        "tool_calls": [{"name": tool_name, "args": {"query": "test"}}],
    })

    assert result == expected_node

def test_node_supervisor_maps_string_tool_input_to_query_arg(monkeypatch):
    fake_llm = FakeLLM(tool_calls=[{
        "name": "CodeAssistant",
        "args": {"query": "viết hàm sort"},
        "id": "call-6"
    }])
    monkeypatch.setattr(lang_graph_rag, "supervisor_llm", fake_llm)

    result = asyncio.run(lang_graph_rag.node_supervisor(
        {"messages": [HumanMessage(content="giúp mình viết hàm sort")]}
    ))

    assert result["tool_calls"][0]["name"] == "CodeAssistant"
    assert result["tool_calls"][0]["args"]["query"] == "viết hàm sort"


def test_node_direct_answer_fallback_to_default_when_last_ai_content_empty():
    result = asyncio.run(lang_graph_rag.node_direct_answer(
        {
            "messages": [
                HumanMessage(content="Giải thích giúp mình về CNN"),
                AIMessage(content=""),
            ]
        }
    ))

    assert (
        result["response"]["text"]
        == "Mình chưa nhận được nội dung rõ ràng, bạn thử diễn đạt lại giúp mình nhé."
    )
    assert result["response"]["type"] == "direct"


def test_node_direct_answer_fallback_to_default_when_no_message_content():
    result = asyncio.run(lang_graph_rag.node_direct_answer(
        {"messages": [HumanMessage(content=""), AIMessage(content="")]}
    ))

    assert (
        result["response"]["text"]
        == "Mình chưa nhận được nội dung rõ ràng, bạn thử diễn đạt lại giúp mình nhé."
    )
    assert result["response"]["type"] == "direct"


def test_node_direct_answer_does_not_echo_when_last_message_is_human():
    user_text = "Đây là nội dung người dùng, không được echo."
    result = asyncio.run(lang_graph_rag.node_direct_answer(
        {"messages": [AIMessage(content="Mình có thể hỗ trợ bạn."), HumanMessage(content=user_text)]}
    ))

    assert (
        result["response"]["text"]
        == "Mình chưa nhận được nội dung rõ ràng, bạn thử diễn đạt lại giúp mình nhé."
    )
    assert result["response"]["type"] == "direct"



def test_node_supervisor_falls_back_to_tutor_when_output_empty_and_no_tool_calls(monkeypatch):
    fake_llm = FakeLLM(tool_calls=[])
    monkeypatch.setattr(lang_graph_rag, "supervisor_llm", fake_llm)

    result = asyncio.run(lang_graph_rag.node_supervisor(
        {"messages": [HumanMessage(content="linear regression là cái gì")]}
    ))

    assert result["tool_calls"][0]["name"] == "AskTutor"
    assert result["tool_calls"][0]["args"]["query"] == "linear regression là cái gì"
