import json
from src.rag_core.state import State

def _extract_tool_args_from_state(state: State, tool_name: str) -> dict:
    """Trích xuất tham số của tool từ state hoặc messages."""
    tool_calls = state.get("tool_calls") or []
    for tool_call in tool_calls:
        if tool_call.get("name") == tool_name:
            args = tool_call.get("args", {})
            if isinstance(args, dict):
                return args

    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                if tool_call.get("name") == tool_name:
                    args = tool_call.get("args", {})
                    if isinstance(args, dict):
                        return args
    return {}
