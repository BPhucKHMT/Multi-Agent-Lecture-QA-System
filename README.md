# 🤖 Hệ Thống Hỏi Đáp môn học tại UIT (RAG QABot)

**PUQ Q&A** là hệ thống trợ lý học tập thông minh sử dụng kiến trúc **Multi-Agent RAG (Retrieval-Augmented Generation)** để hỗ trợ sinh viên UIT tra cứu kiến thức từ các bài giảng video.

<p align="center">
  <img src="notebook_baseline/architecture.png" alt="Overall Framework" width="600"/>
</p>

---

## ✨ Tính năng nổi bật

- 🧠 **Kiến trúc Multi-Agent**: Sử dụng [LangGraph](https://www.langchain.com/langgraph) để điều phối giữa các chuyên gia:
  - **Supervisor**: Điều hướng thông minh dựa trên ý định người dùng.
  - **Tutor Agent**: Truy hồi kiến thức từ transcript video với cite nguồn chính xác.
  - **Math Agent**: Giải toán bằng SymPy, trình bày LaTeX chuyên nghiệp.
  - **Coding Agent**: Hỗ trợ viết code và debug.
  - **Quiz Agent**: Tự động sinh câu hỏi trắc nghiệm từ nội dung bài học.
- 📺 **Video Citation**: Mỗi câu trả lời từ video đều kèm theo link YouTube với timestamp chính xác.
- 🎨 **Modern UI**: Giao diện React cao cấp, mượt mà, hỗ trợ Dark Mode và render biểu thức toán học.

---

## 🏗️ Kiến trúc kỹ thuật

- **Backend**: FastAPI, LangChain, LangGraph.
- **LLM**: Google Gemini 1.5 Flash (hoặc GPT-4o).
- **Vector DB**: ChromaDB (MMR Search).
- **Embedding/Reranker**: BAAI/bge-m3 & bge-reranker-base.
- **Frontend**: 
  - **Modern**: React + Vite + Tailwind CSS.
  - **Internal**: Streamlit (Legacy).

---

## 📂 Cấu trúc dự án

```bash
├── src/                    # 🐍 Backend (Python)
│   ├── api/                # FastAPI Router & Services
│   ├── rag_core/           # Logic Multi-Agent (LangGraph)
│   ├── storage/            # Quản lý Vector DB
│   └── ingestion/          # Pipeline crawl & xử lý dữ liệu
├── frontend/               # ⚛️ Modern Web Interface (React + Vite)
├── app.py                  # 🎈 Streamlit UI (Legacy)
├── server.py               # 🚀 Backend Entry Point
├── artifacts/              # 📦 Dữ liệu runtime (Vector DB, Chunks, Videos) [Ignored]
└── ...
```

---

## 🚀 Hướng dẫn cài đặt

### 1. Chuẩn bị môi trường
Yêu cầu Python 3.12+ và Node.js 18+.

```bash
git clone https://github.com/BPhucKHMT/Rag_QABot.git
cd Rag_QABot
```

### 2. Thiết lập Backend
```bash
# Tạo môi trường ảo
python -m venv venv
source venv/Scripts/activate # Windows: venv\Scripts\activate

# Cài đặt thư viện
pip install -r requirements.txt

# Cấu hình API Keys (Copy từ .env.example)
cp .env.example .env
```

### 3. Thiết lập Frontend
```bash
cd frontend
npm install
```

### 4. Khởi chạy hệ thống
Sử dụng 2 terminal riêng biệt:

- **Terminal 1 (Backend)**: `uvicorn server:app --reload --port 8000`
- **Terminal 2 (Frontend)**: `cd frontend && npm run dev`

---

## 🔑 Biến môi trường (.env)

| Biến | Ý nghĩa |
|------|---------|
| `googleAPIKey` | API Key cho Gemini (Bắt buộc) |
| `myAPIKey` | OpenAI API Key (Tùy chọn cho Embedding) |
| `YOUTUBE_API_KEY` | Dùng để crawl dữ liệu mới từ YouTube |

---

## 🛡️ Giấy phép & Đóng góp
Dự án được phát triển phục vụ mục đích học tập tại UIT. Mọi đóng góp vui lòng tạo Pull Request hoặc Issue.
