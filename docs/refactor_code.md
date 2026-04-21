# Kế Hoạch Tái Cấu Trúc Toàn Bộ Dự Án (Enterprise Standard)

## 📌 Bối cảnh và Vấn đề
Được review từ `AGENTS.md` và mã nguồn hiện tại, kiến trúc dự án đang dàn trải toàn bộ logic (App, API server gốc, data loading, machine learning models) ở chung một cấp đồng lõi (`final_project/`). Các thư mục output (artifacts) đang trộn lẫn với source code. Điều này gây khó khăn trong:
1. **Khả năng dễ đọc & bảo trì**: Cấu trúc không rõ ràng giữa tầng Service, tầng Data Pipeline, và tầng Core Retrieval.
2. **Quản lý Import/Export**: Có rủi ro bị tuần hoàn (circular imports).
3. **Debug & Triển khai**: Khó chạy đơn lẻ. Logs không có cấu trúc chuẩn, `print()` nằm rải rác.
4. **Mở rộng code**: Sẽ rất khó cho lập trình viên mới (hoặc các AI Agent khác) khi tham gia vào làm việc.

---

## 🏗️ Cấu Trúc Thư Mục Doanh Nghiệp Đề Xuất (Domain-Driven Structure)

Chúng ta gom nhóm tất cả mã nguồn vào thư mục `src/`, phân hoạch rõ ràng theo Domain. Dữ liệu sẽ để hết vào `artifacts/` và cấu hình tách bạch `config/`.

```text
final_project/
├── src/                          # 🧠 TOÀN BỘ MÃ NGUỒN CHÍNH
│   ├── api/                      # Cổng giao tiếp API backend
│   │   ├── routes.py             
│   │   └── server.py             # FastAPI entry (đổi từ server.py)
│   ├── frontend/                 # UI giao diện người dùng
│   │   ├── app.py                # Streamlit entry (đổi từ app.py)
│   │   └── components/           
│   ├── rag/                      # Luồng chính tạo nên RAG
│   │   ├── lang_graph_rag.py     
│   │   └── offline_rag.py        
│   ├── retrieval/                # Chứa thuật toán và Vector Store thao tác
│   │   ├── retrievers/           # hybrid, keyword... (từ retriever/)
│   │   ├── text_splitters/       # Semantic chunking...
│   │   └── storage/              # Kết nối ChromaDB (từ src/storage/)
│   ├── generation/               # Xử lý Prompt, Parsing & gọi LLM
│   │   └── llm_model.py          
│   ├── data_pipeline/            # 🔄 pipeline data end-to-end
│   │   ├── steps/                # Download, Scene Detect, OCR, Preprocess
│   │   ├── pipeline.py           # Master Extract Pipeline Orchestrator
│   │   └── combine_content.py    # Combine OCR & chunk
│   ├── core/                     # Phần lõi trung tâm: logs, configs, utils
│   │   ├── config.py             # Nạp biến từ .env, yaml tập trung nhất
│   │   ├── logger.py             # Custom logging (ghi rõ lỗi, thời gian)
│   │   └── exceptions.py         # Lỗi custom cho toàn Project
│   └── main.py                   # Script tổng chạy các module phụ nhanh.
│
├── tests/                        # 🧪 Unit Tests và Integration Tests
│   ├── test_rag/
│   ├── test_pipeline/
│   └── conftest.py
│
├── artifacts/                    # 📦 TẤT CẢ DỮ LIỆU ĐƯỢC SINH RA (Giữ ngoài src)
│   ├── data_raw/                 # Transcripts ban đầu
│   ├── chunks_cache/             # semantic_chunks.json
│   ├── database_semantic/        # File SQLite của ChromaDB
│   ├── data_extraction/          # SceneJSON, Keyframes, OCR JSON
│   └── videos/                   # Video tải xuống
│
├── config/                       # Các File Config (không phải source code)
│   └── settings.yaml             # File thiết lập chung (thay cho config.yaml)
│
├── scripts/                      # Tool build, deploy hoặc test bash script
├── docs/                         # Chứa các file document thiết kế
├── requirements.txt
├── .env.example
├── Dockerfile
└── docker-compose.yaml
```

---

## 🛠️ Quy Trình Chuyển Đổi (Migration Plan)

Nhằm đảm bảo dự án không bị lỗi đứt gãy, quá trình chuyển dịch sẽ chia theo các pha sau:

### Phase 1: Tạo Skeleton Mới & Định tuyến Lại Path
1. Tạo folder `src/` và các sub-directories. Tạo file trống `__init__.py` ở mỗi folder.
2. Di dời lần lượt:
   - `server.py` → `src/api/`
   - `app.py` → `src/frontend/`
   - Nhóm các modules `generation`, `rag` → `src/`
   - Nhóm `vector_store`, `text_splitters`, `retriever` → `src/retrieval/`
   - Nhóm `data_loader`, `preprocess`, module `data_extraction` → `src/data_pipeline/`
3. Cập nhật biến đường dẫn lưu trữ, trỏ toàn bộ đến nhánh lưu trữ của thư mục gốc `artifacts/`. Thống nhất định nghĩa hằng số PATH ở `src/core/config.py`.

### Phase 2: Cập Nhật Import Paths & Giải Quyết Circular Dependency
1. Chỉnh lại file import trong toàn bộ script, ví dụ: 
   - Thay vì `from data_loader.coordinator import ...`
   - Chuyển thành `from src.data_pipeline.coordinator import ...`
2. Đảm bảo config được chia sẻ từ module `core` duy nhất.

### Phase 3: Chuẩn hóa Format Code, TypeHint, Log và Comment
1. **Type hints**: Thêm định dạng Type cho tham số và đối số trả về của gần như 100% hàm để dễ debug: `def get_db() -> VectorDB:`
2. **Centralized Logging thay cho Print**:
   - Thay thế các lệnh `print()` thuần thúy thành lệnh `logger.info()`, `logger.error()`, `logger.warning()`.
   - Setup logger output cho ra thời gian chạy, tiến trình / module gọi log, giúp phân định rạch ròi bug phát sinh ở phần LLM, ở phần Data Extraction, hay Database.
3. **Vietnamese Docstring**: Áp dụng format chuẩn, ví dụ:
   ```python
   def process_ocr_pipeline(video_id: str) -> bool:
       """
       Hàm bóc tách chữ từ Keyframes sử dụng EasyOCR.
       
       Args:
           video_id (str): Định danh duy nhất của video từ YouTube.
           
       Returns:
           bool: Tình trạng thực thi (Thành công / Thất bại).
       """
       pass
   ```
4. **Code Formatter**: Vận hành script tự động format code như `ruff` hoặc `black` theo chuẩn độ chuẩn.

---

## 📊 Trạng thái thực thi hiện tại

Mọi thay đổi dưới đây đã được AI Agent thực hiện để tuân thủ kiến trúc mới:

- [x] **Pha 1: Cơ sở hạ tầng thư mục**
    - [x] Tạo `src/frontend/` và di dời `app.py`
    - [x] Tạo `src/api/` và di dời `server.py`
    - [x] Đổi tên `src/ingestion/` thành `src/data_pipeline/`
    - [x] Di dời `text_splitters/` sang `src/retrieval/` để tối ưu hóa context retrieval
    - [x] Chuẩn hóa `artifacts/` chứa toàn bộ dữ liệu runtime (chunks, db, videos, ocr)

- [x] **Pha 2: Cập nhật mã nguồn & Refactor Import**
    - [x] Cập nhật toàn bộ tuyệt đối import `from src.ingestion...` thành `from src.data_pipeline...`
    - [x] Cập nhật import cho `text_splitters` trong `file_loader.py` và `lang_graph_rag.py`
    - [x] Đồng nhất hóa cơ chế nạp cấu hình thông qua `src/shared/config.py` (nếu có cập nhật)

- [ ] **Pha 3: Verification & Polish**
    - [ ] Kiểm tra tính ổn định của Backend (FastAPI) với cấu trúc mới
    - [ ] Kiểm tra tính ổn định của Frontend (Streamlit)
    - [ ] Chạy full pipeline thử nghiệm cho playlist `CS315`
    - [ ] Áp dụng Type hints và Centralized Logging cho các module lõi

---

## 🐞 Cải Thiện Yếu Tố Debug
- **Track Status Chi Tiết**: Rút kinh nghiệm file Data extraction với `pipeline_state.json`. Mở rộng ra cho toàn dự án: một state manager/logger ghi nhận tiến độ. Chức năng RAG thất bại có thể bắt lỗi traceback rõ ràng xem bước nào gây ra.
- **Graceful Error Handling**: Bọc API FastAPI thông qua Error handler toàn cục. Bảo đảm response trả JSON Error chuẩn mực thay vì internal error không rõ ràng (khi rớt mạng Youtube hay LLM bị rate limit).

Việc áp dụng kiến trúc Micro/Modularized Monolith này đảm bảo Code Base gọn gàng, có tính module cao, và sẵn sàng giao quyền can thiệp cho nhiều Developer (hay AI Agents khác) mở rộng mà ít rủi ro trùng lặp hay hỏng chéo nhất.

