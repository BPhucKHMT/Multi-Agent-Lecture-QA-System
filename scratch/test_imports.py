
import sys
import os

# Thêm root vào sys.path để import được backend và src
sys.path.append(os.getcwd())

try:
    from backend.app.services.chat import generate_chat_stream
    print("✅ Successfully imported generate_chat_stream")
except Exception as e:
    print(f"❌ Failed to import generate_chat_stream: {e}")
    import traceback
    traceback.print_exc()
