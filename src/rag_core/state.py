from langgraph.graph import MessagesState
from typing import Any, Dict

class State(MessagesState):
    agent_output: dict = {}
    response: dict = {}
    next_node: str = ""
    tool_calls: list[dict] = []
