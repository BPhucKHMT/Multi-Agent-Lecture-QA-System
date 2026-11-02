from langgraph.graph import MessagesState

class State(MessagesState):
    agent_output: dict = {}
    response: dict = {}
    next_node: str = ""
    tool_calls: list[dict] = []
