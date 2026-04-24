import asyncio
import os
import sys

# Thêm đường dẫn project
sys.path.append(os.getcwd())

from src.rag_core.lang_graph_rag import workflow
from src.rag_core.state import State

async def debug_stream():
    workflow = build_rag_graph()
    # Giả lập câu hỏi gây leak trong ảnh
    initial_state = {
        "messages": [{"type": "human", "content": "decision tree là gì"}]
    }
    
    print("\n--- BẮT ĐẦU DEBUG STREAM EVENTS ---\n")
    
    async for event in workflow.astream_events(initial_state, version="v2"):
        kind = event.get("event")
        tags = event.get("tags", [])
        name = event.get("name", "")
        node = event.get("metadata", {}).get("langgraph_node", "")
        
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            print(f"[{node}] [TAGS: {tags}] [NAME: {name}] TOKEN: {repr(content)}")
        elif kind == "on_chain_start":
            print(f"--- Chain Start: {name} (Node: {node}) ---")

if __name__ == "__main__":
    asyncio.run(debug_stream())
