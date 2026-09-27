"""Smoke test Supervisor routing through Experiential Labs Jev with Luna fallback.

Run:
    python scripts/test_supervisor_live.py
    python scripts/test_supervisor_live.py "Tính tích phân của hàm e^x dx"
"""
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(dotenv_path=ROOT_DIR / ".env", override=True)

from langchain_core.messages import HumanMessage
from src.rag_core.lang_graph_rag import node_supervisor
from src.generation.jev_router import (
    JEV_MODEL,
    close_jev_http_client,
    open_jev_http_client,
)


SAMPLE_QUESTIONS = [
    ("Toán học", "Tính đạo hàm của hàm số y = x^3 - 3x^2 + 2 tại x = 1"),
    ("Lập trình", "Viết hàm tìm kiếm nhị phân (binary search) bằng Python"),
    ("Tạo Quiz", "Tạo cho mình 3 câu hỏi trắc nghiệm về giải thuật sắp xếp nhanh QuickSort"),
    ("Bài giảng UIT", "Mô hình mạng Transformer có cấu trúc Multi-Head Attention hoạt động ra sao?"),
    ("Chào hỏi xã giao", "Xin chào bạn, hôm nay thời tiết thế nào?"),
]


async def run_query(query: str, category: str = "Tùy chọn"):
    print(f"\n{'='*70}")
    print(f"📌 [Thể loại]: {category}")
    print(f"❓ [Câu hỏi]: {query}")
    print("-" * 70)

    state = {
        "messages": [HumanMessage(content=query)],
    }

    try:
        result = await node_supervisor(state)
        tool_calls = result.get("tool_calls", [])

        if not tool_calls:
            print("⚠️  Supervisor không trả về tool call nào.")
            return

        for idx, call in enumerate(tool_calls, 1):
            name = call.get("name")
            args = call.get("args", {})
            print(f"🎯 Route {idx}: Chuyển đến Agent -> \033[92m[{name}]\033[0m")
            print(f"📦 Tham số truyền vào: {args}")

    except Exception as e:
        print(f"❌ Lỗi khi điều phối: {type(e).__name__}")


async def main():
    experiential_key = os.getenv("EXPERIENTIAL_API_KEY", "").strip()
    openai_key = os.getenv("myAPIKey", "").strip()
    print("\n" + "=" * 70)
    print("🧪 KIỂM TRA EXPERIENTIAL JEV SUPERVISOR (FALLBACK: GPT-6 LUNA)")
    print("=" * 70)
    print(f"🔹 Experiential API Key: {'✅ Đã cấu hình' if experiential_key else '❌ Chưa có (dùng fallback)'}")
    print(f"🔹 Jev Model: {JEV_MODEL}")
    print(f"🔹 OpenAI Fallback Key: {'✅ Đã cấu hình' if openai_key else '❌ Chưa có'}")
    print(f"🔹 OpenAI Fallback Model: {os.getenv('OPENAI_SUPERVISOR_MODEL', 'gpt-6-luna')}")

    open_jev_http_client()
    try:
        if len(sys.argv) > 1:
            await run_query(" ".join(sys.argv[1:]), category="User Input")
            return

        print("\nĐang chạy kiểm tra 5 câu hỏi mẫu đại diện cho các Agent...")
        for category, question in SAMPLE_QUESTIONS:
            await run_query(question, category)
        print("\n" + "=" * 70)
        print("✅ Hoàn thành kiểm tra tất cả các trường hợp định tuyến.")
        print("=" * 70 + "\n")
    finally:
        await close_jev_http_client()


if __name__ == "__main__":
    asyncio.run(main())
