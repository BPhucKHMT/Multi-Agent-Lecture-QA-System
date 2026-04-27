# Fix streaming `/chat/stream`: hiển thị token realtime thay vì dồn kết quả cuối

## 1) Triệu chứng

- Người dùng gửi query (ví dụ: `code linear regression`) nhưng UI không hiện chữ chạy dần.
- Frontend đứng ở trạng thái "đang xử lý" khá lâu, sau đó nhận toàn bộ nội dung một lần.
- Trải nghiệm giống non-streaming, không đúng kỳ vọng SSE realtime.

---

## 2) Root cause

Trong `src/api/services/chat_service.py::generate_stream`:

- Event `on_chat_model_stream` đã được nhận từ `workflow.astream_events(...)`.
- Nhưng nhánh này đang `continue` và **không emit** SSE `type=token`.
- Kết quả: backend chỉ gửi `metadata` ở cuối (`type=metadata`) + `[DONE]`, nên frontend không có token để render incremental.

---

## 3) Cách fix đã chọn (Option A)

### Mục tiêu

- Stream token thật từ backend theo SSE.
- Giữ nguyên metadata/citation render ở cuối để không phá format response hiện có.

### Thay đổi chính

1. **Backend emit token realtime**
   - File: `src/api/services/chat_service.py`
   - Thêm helper `_extract_stream_token_content(chunk)` để chuẩn hóa token text từ stream chunk.
   - Khi nhận `on_chat_model_stream`, emit:
   ```json
   {"type":"token","content":"..."}
   ```
   - Vẫn giữ event cuối:
   ```json
   {"type":"metadata","response":{...}}
   ```
   và `data: [DONE]`.

2. **Frontend không cần đổi contract**
   - File: `src/frontend/app.py`
   - Frontend đã có xử lý `type=token` (`full_text += content`, render placeholder) và `type=metadata` cuối stream.
   - Sau khi backend emit token đúng, UI tự hiển thị dần theo token như mong muốn.

---

## 4) Test checklist (regression)

### Unit test đã cập nhật

- File: `tests/api/test_chat_stream.py`
- Đổi kỳ vọng từ "không có token" sang:
  - payload đầu là `type=token`
  - payload cuối là `type=metadata`

### Lệnh kiểm tra

```bash
python -m pytest tests\api\test_chat_stream.py::test_generate_stream_emits_token_before_metadata -q
python -m pytest tests\api\test_chat_stream.py -q
```

---

## 5) Tiêu chí hoàn tất

- Khi hỏi query sinh code (ví dụ linear regression), nội dung trả lời xuất hiện tăng dần theo token trên UI.
- Metadata cuối vẫn được nhận và render đầy đủ (text hoàn chỉnh + citation/video metadata).
- Luồng stream vẫn kết thúc bằng `data: [DONE]`.
