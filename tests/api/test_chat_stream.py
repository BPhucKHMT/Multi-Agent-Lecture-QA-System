import asyncio
import builtins
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.api.services import chat_service
from src.rag_core import lang_graph_rag


async def _collect_stream(gen):
    chunks = []
    async for item in gen:
        chunks.append(item)
    return chunks


class _BrokenWorkflow:
    async def astream_events(self, *_args, **_kwargs):
        raise RuntimeError("stream exploded")
        yield  # pragma: no cover

    async def ainvoke(self, *_args, **_kwargs):
        return {"response": {"text": "fallback"}}


class _SingleRunWorkflow:
    def __init__(self):
        self.ainvoke_calls = 0

    async def astream_events(self, *_args, **_kwargs):
        class _Chunk:
            def __init__(self, content):
                self.content = content

        yield {"event": "on_chat_model_stream", "data": {"chunk": _Chunk("Xin")}}
        yield {
            "event": "on_chain_end",
            "data": {
                "output": {
                    "response": {
                        "text": "Xin chao",
                        "video_url": [],
                        "title": [],
                        "filename": [],
                        "start_timestamp": [],
                        "end_timestamp": [],
                        "confidence": [],
                        "type": "direct",
                    }
                }
            },
        }

    async def ainvoke(self, *_args, **_kwargs):
        self.ainvoke_calls += 1
        raise AssertionError("ainvoke should not be called in streaming path")


class _EmptyResponseWorkflow:
    async def astream_events(self, *_args, **_kwargs):
        yield {"event": "on_chain_end", "metadata": {"langgraph_node": "direct"}, "data": {"output": {"response": {}}}}

    async def ainvoke(self, *_args, **_kwargs):
        return {"response": {}}


class _EmptyDirectPayloadWorkflow:
    async def astream_events(self, *_args, **_kwargs):
        yield {
            "event": "on_chain_end",
            "metadata": {"langgraph_node": "direct"},
            "data": {
                "output": {
                    "response": {
                        "text": "   ",
                        "video_url": [],
                        "title": [],
                        "filename": [],
                        "start_timestamp": [],
                        "end_timestamp": [],
                        "confidence": [],
                        "type": "direct",
                    }
                }
            },
        }

    async def ainvoke(self, *_args, **_kwargs):
        return {"response": {"text": "unused"}}


class _CaptureHistoryWorkflow:
    def __init__(self):
        self.captured_message_count = None
        self.captured_messages = []

    @staticmethod
    def _extract_role(message):
        message_type = getattr(message, "type", "")
        if message_type == "human":
            return "user"
        if message_type == "ai":
            return "assistant"
        return message_type or message.__class__.__name__

    async def astream_events(self, initial_state, *_args, **_kwargs):
        messages = initial_state.get("messages", [])
        self.captured_message_count = len(messages)
        self.captured_messages = [
            {
                "role": self._extract_role(message),
                "content": getattr(message, "content", None),
            }
            for message in messages
        ]
        yield {
            "event": "on_chain_end",
            "data": {
                "output": {
                    "response": {
                        "text": "ok",
                        "video_url": [],
                        "title": [],
                        "filename": [],
                        "start_timestamp": [],
                        "end_timestamp": [],
                        "confidence": [],
                        "type": "direct",
                    }
                }
            },
        }

    async def ainvoke(self, *_args, **_kwargs):
        return {"response": {"text": "unused"}}


class _EmptySupervisorExecutor:
    def __init__(self):
        self.invoke_calls = 0

    def invoke(self, _payload):
        self.invoke_calls += 1
        return {"output": "", "intermediate_steps": []}


class _UsageOutput:
    def __init__(self, input_tokens: int, output_tokens: int):
        self.usage_metadata = {"input_tokens": input_tokens, "output_tokens": output_tokens}


class _SupervisorUsageWorkflow:
    async def astream_events(self, *_args, **_kwargs):
        yield {
            "event": "on_chat_model_end",
            "metadata": {"langgraph_node": "supervisor"},
            "data": {"output": _UsageOutput(11, 7)},
        }
        yield {
            "event": "on_chain_end",
            "data": {
                "output": {
                    "response": {
                        "text": "ok",
                        "video_url": [],
                        "title": [],
                        "filename": [],
                        "start_timestamp": [],
                        "end_timestamp": [],
                        "confidence": [],
                        "type": "direct",
                    }
                }
            },
        }

    async def ainvoke(self, *_args, **_kwargs):
        return {"response": {"text": "unused"}}


class _MultiNodeUsageWorkflow:
    async def astream_events(self, *_args, **_kwargs):
        yield {
            "event": "on_chat_model_end",
            "metadata": {"langgraph_node": "supervisor"},
            "data": {"output": _UsageOutput(120, 24)},
        }
        yield {
            "event": "on_chat_model_end",
            "metadata": {"langgraph_node": "tutor"},
            "data": {"output": _UsageOutput(240, 96)},
        }
        yield {
            "event": "on_chain_end",
            "metadata": {"langgraph_node": "tutor"},
            "data": {
                "output": {
                    "response": {
                        "text": "Linear regression là mô hình tuyến tính cơ bản để dự đoán biến liên tục.",
                        "video_url": [],
                        "title": [],
                        "filename": [],
                        "start_timestamp": [],
                        "end_timestamp": [],
                        "confidence": [],
                        "type": "rag",
                    }
                }
            },
        }

    async def ainvoke(self, *_args, **_kwargs):
        return {"response": {"text": "unused"}}


def test_generate_stream_returns_error_metadata_when_streaming_fails(monkeypatch):
    monkeypatch.setattr(lang_graph_rag, "workflow", _BrokenWorkflow(), raising=False)

    chunks = asyncio.run(_collect_stream(chat_service.generate_stream("conv-1", [], "tạo quiz cnn")))
    payloads = [c for c in chunks if c.startswith("data: ") and c != "data: [DONE]\n\n"]

    assert payloads, "Expected at least one SSE payload"
    body = json.loads(payloads[-1][6:])
    assert body["type"] == "metadata"
    assert body["response"]["type"] == "error"
    assert "stream exploded" in body["response"]["text"]
    assert chunks[-1] == "data: [DONE]\n\n"


def test_generate_stream_uses_single_workflow_execution(monkeypatch):
    workflow = _SingleRunWorkflow()
    monkeypatch.setattr(lang_graph_rag, "workflow", workflow, raising=False)

    chunks = asyncio.run(_collect_stream(chat_service.generate_stream("conv-1", [], "tạo quiz cnn")))
    payloads = [c for c in chunks if c.startswith("data: ") and c != "data: [DONE]\n\n"]

    assert payloads, "Expected at least one SSE payload"
    body = json.loads(payloads[-1][6:])
    assert body["type"] == "metadata"
    assert body["response"]["type"] == "direct"
    assert body["response"]["text"] == "Xin chao"
    assert workflow.ainvoke_calls == 0
    assert chunks[-1] == "data: [DONE]\n\n"


def test_generate_stream_emits_token_before_metadata(monkeypatch):
    workflow = _SingleRunWorkflow()
    monkeypatch.setattr(lang_graph_rag, "workflow", workflow, raising=False)

    chunks = asyncio.run(_collect_stream(chat_service.generate_stream("conv-1", [], "tạo quiz cnn")))
    payloads = [
        json.loads(c[6:])
        for c in chunks
        if c.startswith("data: ") and c != "data: [DONE]\n\n"
    ]

    assert payloads, "Expected SSE payloads"
    assert payloads[0]["type"] == "token"
    assert payloads[0]["content"] == "Xin"
    assert payloads[-1]["type"] == "metadata"
    assert payloads[-1]["response"]["type"] == "direct"


def test_generate_stream_falls_back_to_default_direct_answer_when_supervisor_content_empty(
    monkeypatch,
):
    fallback_text = "Mình chưa nhận được nội dung rõ ràng, bạn thử diễn đạt lại giúp mình nhé."
    fake_executor = _EmptySupervisorExecutor()
    monkeypatch.setattr(lang_graph_rag, "supervisor_executor", fake_executor, raising=False)

    chunks = asyncio.run(_collect_stream(chat_service.generate_stream("conv-1", [], "xin chào")))
    payloads = [
        json.loads(c[6:])
        for c in chunks
        if c.startswith("data: ") and c != "data: [DONE]\n\n"
    ]

    assert fake_executor.invoke_calls == 1
    assert payloads, "Expected at least one SSE payload"
    assert payloads[-1]["type"] == "metadata"
    assert payloads[-1]["response"]["type"] == "direct"
    assert payloads[-1]["response"]["text"] == fallback_text
    assert payloads[-1]["response"]["text"].strip()
    assert chunks[-1] == "data: [DONE]\n\n"


def test_generate_stream_returns_error_when_response_payload_is_empty(monkeypatch):
    monkeypatch.setattr(lang_graph_rag, "workflow", _EmptyResponseWorkflow(), raising=False)

    chunks = asyncio.run(_collect_stream(chat_service.generate_stream("conv-1", [], "tạo quiz cnn")))
    payloads = [c for c in chunks if c.startswith("data: ") and c != "data: [DONE]\n\n"]

    assert payloads, "Expected at least one SSE payload"
    body = json.loads(payloads[-1][6:])
    assert body["type"] == "metadata"
    assert body["response"]["type"] == "error"
    assert "Không nhận được phản hồi từ AI" in body["response"]["text"]


def test_generate_stream_returns_error_when_direct_payload_text_is_empty(monkeypatch):
    monkeypatch.setattr(
        lang_graph_rag,
        "workflow",
        _EmptyDirectPayloadWorkflow(),
        raising=False,
    )

    chunks = asyncio.run(_collect_stream(chat_service.generate_stream("conv-1", [], "tạo quiz cnn")))
    payloads = [c for c in chunks if c.startswith("data: ") and c != "data: [DONE]\n\n"]

    assert payloads, "Expected at least one SSE payload"
    body = json.loads(payloads[-1][6:])
    assert body["type"] == "metadata"
    assert body["response"]["type"] == "error"
    assert "Không nhận được phản hồi từ AI" in body["response"]["text"]


def test_generate_stream_caps_history_before_invoking_workflow(monkeypatch):
    workflow = _CaptureHistoryWorkflow()
    monkeypatch.setattr(lang_graph_rag, "workflow", workflow, raising=False)
    monkeypatch.setattr(chat_service, "MAX_STREAM_HISTORY_MESSAGES", 4, raising=False)

    request_messages = []
    for i in range(12):
        role = "user" if i % 2 == 0 else "assistant"
        request_messages.append({"role": role, "content": f"msg-{i}"})

    chunks = asyncio.run(_collect_stream(chat_service.generate_stream("conv-1", request_messages, "new-msg")))
    assert chunks[-1] == "data: [DONE]\n\n"
    expected_messages = [
        {"role": "user", "content": "msg-8"},
        {"role": "assistant", "content": "msg-9"},
        {"role": "user", "content": "msg-10"},
        {"role": "assistant", "content": "msg-11"},
        {"role": "user", "content": "new-msg"},
    ]
    assert workflow.captured_message_count == len(expected_messages)
    assert workflow.captured_messages == expected_messages


def test_safe_stream_log_falls_back_when_console_cannot_encode(monkeypatch):
    outputs = []

    class _FailOncePrinter:
        def __init__(self):
            self.failed = False

        def __call__(self, message):
            if not self.failed:
                self.failed = True
                raise UnicodeEncodeError("cp1252", "ỗ", 0, 1, "cannot encode")
            outputs.append(message)

    printer = _FailOncePrinter()
    monkeypatch.setattr(builtins, "print", printer)

    chat_service._safe_stream_log("[stream] ERROR lỗi unicode")

    assert outputs
    assert "\\u" in outputs[0]


def test_generate_stream_counts_supervisor_usage_in_token_metrics(monkeypatch):
    logs = []
    monkeypatch.setattr(lang_graph_rag, "workflow", _SupervisorUsageWorkflow(), raising=False)
    monkeypatch.setattr(chat_service, "_safe_stream_log", lambda message: logs.append(message))

    chunks = asyncio.run(_collect_stream(chat_service.generate_stream("conv-1", [], "xin chào")))

    assert chunks[-1] == "data: [DONE]\n\n"
    token_metric_lines = [line for line in logs if "[TOKEN METRICS]" in line]
    assert token_metric_lines
    assert "mode=stream input=11 output=7 total=18" in token_metric_lines[-1]


def test_generate_stream_logs_token_breakdown_and_visible_estimate(monkeypatch):
    logs = []
    monkeypatch.setattr(lang_graph_rag, "workflow", _MultiNodeUsageWorkflow(), raising=False)
    monkeypatch.setattr(chat_service, "_safe_stream_log", lambda message: logs.append(message))

    chunks = asyncio.run(_collect_stream(chat_service.generate_stream("conv-1", [], "linear regression là gì")))

    assert chunks[-1] == "data: [DONE]\n\n"
    breakdown_lines = [line for line in logs if "[TOKEN BREAKDOWN]" in line]
    assert breakdown_lines
    assert "supervisor:in=120,out=24" in breakdown_lines[-1]
    assert "tutor:in=240,out=96" in breakdown_lines[-1]
    assert "visible_chars=" in breakdown_lines[-1]
    assert "visible_tokens_estimate=" in breakdown_lines[-1]
