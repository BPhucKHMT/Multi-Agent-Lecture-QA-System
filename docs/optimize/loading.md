# Tối ưu loading RAG: Load một lần, dùng nhiều lần

## 0) Cập nhật kết quả triển khai

Đã triển khai xong Phase 1 theo hướng singleton app-level:

- Thêm `src/rag_core/resource_manager.py` để quản lý tài nguyên nặng theo lazy singleton (VectorDB/retriever, BM25/Hybrid, reranker, tutor chain, quiz resources).
- Refactor `src/rag_core/agents/tutor.py`: `get_rag_chain()` dùng `resource_manager.get_tutor_chain()`.
- Refactor `src/rag_core/agents/quiz.py`: dùng `resource_manager.get_quiz_resources()`, bỏ cache cục bộ theo agent.
- Sửa `src/api/server.py`: backend prewarm tài nguyên RAG ngay lúc startup (`prewarm_rag_resources()`), không chờ query đầu tiên mới load.
- Thêm/cập nhật test:
  - `tests/rag_core/test_resource_manager.py`
  - `tests/rag_core/test_tutor_parsing.py`
  - `tests/rag_core/test_quiz_json_parsing.py`
  - `tests/api/test_server_startup.py`
- Kết quả test liên quan: `22 passed` (rag_core + api stream + parsing + resource manager).
- Full suite hiện còn 1 lỗi nền đã tồn tại trước đó: `tests/rag_core/test_offline_rag_context.py::test_get_context_total_serialized_size_is_capped`.

---

## 1) Vấn đề hiện tại

Ở luồng RAG hiện tại (trước khi tối ưu), các tài nguyên nặng bị khởi tạo phân tán/nhân đôi giữa agents và theo process worker:

- `VectorDB()` (kèm `HuggingFaceEmbeddings`) ở `src/storage/vectorstore.py`
- `CrossEncoderReranker(...)` ở `src/rag_core/agents/tutor.py` và `src/rag_core/agents/quiz.py`
- Dựng `BM25KeywordSearch` + `HybridSearch` trong luồng tutor

Hệ quả:

- Tăng độ trễ truy vấn đầu (và đôi lúc cả truy vấn sau nếu cache không giữ đúng vòng đời process)
- Tốn RAM/VRAM và CPU/GPU do khởi tạo lặp
- Log “loading model” xuất hiện nhiều lần, khó dự đoán performance

---

## 2) Mục tiêu tối ưu

1. Chỉ load tài nguyên nặng **một lần cho mỗi process**.
2. Request sau đó chỉ **reuse** object đã có.
3. Không đổi behavior business của trả lời RAG.
4. Cho phép mở rộng prewarm khi cần.

---

## 3) Phương án chọn (A): App-level singleton cache

### Ý tưởng

Tạo một lớp quản lý tài nguyên dùng chung (ví dụ `ResourceManager`), giữ các singleton:

- `VectorDB`
- `vector_retriever`
- `documents` (phục vụ BM25)
- `bm25_retriever`
- `hybrid_retriever`
- `tutor_reranker`
- `quiz_retriever`
- `quiz_reranker`
- `tutor_rag_chain`

Mỗi getter có lazy init:

- Nếu resource chưa có: khởi tạo + lưu cache
- Nếu đã có: trả về ngay

### Tại sao chọn A

- Đúng nhu cầu hiện tại: “load 1 lần rồi dùng về sau”
- Ít thay đổi kiến trúc tổng thể, chỉ thay điểm khởi tạo tài nguyên
- Giữ được single-route hiện tại, không ép refactor lớn

---

## 4) Thiết kế kỹ thuật đề xuất

## 4.1 Tạo module quản lý tài nguyên

**File đề xuất:** `src/rag_core/resource_manager.py`

Nội dung chính:

- Biến singleton cấp module cho từng resource
- `threading.Lock()` để tránh race-condition khi nhiều request cùng vào cold-start
- Hàm public dạng:
  - `get_vector_db()`
  - `get_hybrid_retriever()`
  - `get_tutor_chain()`
  - `get_quiz_resources()` (trả retriever + reranker)
  - `prewarm_all_resources()` (tùy chọn)

## 4.2 Chuyển Tutor Agent sang dùng ResourceManager

**File sửa:** `src/rag_core/agents/tutor.py`

- Bỏ khởi tạo tài nguyên trực tiếp trong `get_rag_chain()`
- `get_rag_chain()` chỉ gọi `resource_manager.get_tutor_chain()`
- Giữ nguyên flow `node_tutor`, chỉ thay nguồn chain

## 4.3 Chuyển Quiz Agent sang dùng ResourceManager

**File sửa:** `src/rag_core/agents/quiz.py`

- Bỏ (hoặc giảm vai trò) cache riêng `_quiz_retriever`, `_quiz_reranker`
- Dùng chung từ `resource_manager.get_quiz_resources()`
- Giữ nguyên logic sinh quiz hiện có

## 4.4 Tránh nhân bản cache giữa nhiều chỗ

- Không giữ nhiều cache song song (một phần ở tutor, một phần ở quiz, một phần ở module khác)
- Chốt “single source of truth” tại `resource_manager.py`

---

## 5) Lộ trình triển khai chi tiết (step-by-step)

## Giai đoạn 1 — Chuẩn hóa tải tài nguyên

1. Tạo `src/rag_core/resource_manager.py` với singleton + lock + getter cơ bản.
2. Port logic dựng `VectorDB`, `documents`, BM25, Hybrid vào manager.
3. Port logic dựng `CrossEncoderReranker` cho tutor/quiz vào manager.

## Giai đoạn 2 — Cắm vào luồng hiện tại

1. Sửa `src/rag_core/agents/tutor.py` dùng `get_tutor_chain()`.
2. Sửa `src/rag_core/agents/quiz.py` dùng `get_quiz_resources()`.
3. Đảm bảo không còn khởi tạo nặng lặp trong từng request path.

## Giai đoạn 3 — Warmup và quan sát

1. (Tùy chọn) thêm prewarm khi app start để giảm cold-start query đầu.
2. Thêm log/metric:
   - thời gian init từng resource
   - số lần init (kỳ vọng: 1/process)
   - latency p50/p95 trước và sau tối ưu

## Giai đoạn 4 — Hardening

1. Thêm cơ chế fail-fast nếu model load lỗi (thay vì retry vô hạn).
2. Thêm hướng dẫn vận hành cho môi trường nhiều worker (mỗi worker vẫn load 1 lần riêng).

---

## 6) Kiểm thử đề xuất

## 6.1 Functional

- Query tutor/quiz vẫn đúng format output cũ.
- Citation/timestamp không đổi semantics.

## 6.2 Performance

- So sánh latency query đầu và query thứ 2+.
- Kiểm tra log init: mỗi resource chỉ init 1 lần/process.

## 6.3 Concurrency

- Bắn nhiều request song song ở cold-start, đảm bảo không double-init do race.

---

## 7) Rủi ro và cách giảm thiểu

1. **Tốn RAM lâu dài do cache giữ object nặng**
   - Theo dõi memory footprint, cân nhắc policy khởi động theo profile máy.

2. **Nhiều worker vẫn load nhiều lần**
   - Đây là expected behavior theo process model; cần sizing worker phù hợp.

3. **Cache stale khi đổi dữ liệu/DB**
   - Bổ sung hook invalidation hoặc restart policy khi re-index xong.

---

## 8) Kết luận ngắn

Với nhu cầu hiện tại, phương án A (singleton app-level + lazy init + reuse) là cách ít rủi ro và hiệu quả nhất để xử lý tình trạng “mỗi lần retrieve RAG lại load từ đầu”.
