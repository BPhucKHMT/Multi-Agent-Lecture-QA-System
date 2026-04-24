# Vấn đề Rò rỉ Multi-Query vào Stream UI

## 📋 Mô tả vấn đề
Hiện tại, khi hệ thống RAG thực hiện bước **Query Expansion** (sinh ra 3 câu truy vấn tìm kiếm khác nhau), các chuỗi JSON chứa danh sách các câu truy vấn này đang bị rò rỉ vào luồng streaming gửi về giao diện người dùng (Frontend).

**Triệu chứng:**
- Giao diện hiển thị một chuỗi JSON thô như `["truy vấn 1", "truy vấn 2", "truy vấn 3"]` trước khi bắt đầu hiển thị câu trả lời Markdown đẹp.
- Gây cảm giác hệ thống bị lỗi hoặc chưa hoàn thiện về mặt thẩm mỹ (UX).

## 🔍 Phân tích nguyên nhân

### 1. Cơ chế Streaming hiện tại
Trong `src/api/services/chat_service.py`, hàm `generate_stream` sử dụng `astream_events(version="v2")` để bắt các sự kiện từ LangChain.
Mặc dù đã có bộ lọc tag:
```python
if "final_answer" not in tags:
    continue
```
Và trong `src/rag_core/offline_rag.py`, bước sinh query đã được gán tag `internal_query` và tắt streaming:
```python
llm_internal = self.llm.with_config(
    tags=["internal_query"],
    run_name="query_expansion",
    streaming=False
)
```

### 2. Tại sao vẫn rò rỉ?
- **Sự cố kế thừa Tag:** Trong một số trường hợp, các sự kiện từ Runnables con có thể bị dính tag của parent chain nếu không được cô lập hoàn toàn.
- **JsonStreamCleaner chưa đủ mạnh:** `JsonStreamCleaner` trong `chat_service.py` được thiết kế để chỉ bóc tách nội dung bên trong key `"text"`. Tuy nhiên, nếu luồng tokens bắt đầu bằng một mảng JSON `[...]` thay vì đối tượng `{...}`, logic tìm `{` đầu tiên có thể bị đánh lừa hoặc bị skip nếu rơi vào chế độ `is_plain_text`.
- **LLM Final Answer "nhìn thấy" Queries:** Có khả năng LLM ở bước trả lời cuối cùng (Final Answer) đang nhận được các queries trong prompt (qua context) và vô tình lặp lại chúng ở đầu output.

## 🛠 Giải pháp đề xuất

### 1. Cô lập hoàn toàn Query Expansion
- Sử dụng `RunnableConfig` để đảm bảo tags của bước sinh query là duy nhất và không bị trộn lẫn.
- Ép kiểu output của `generate_queries` về danh sách string sạch trước khi đi vào các bước tiếp theo.

### 2. Nâng cấp `JsonStreamCleaner`
- Cải thiện logic lọc để **TUYỆT ĐỐI** bỏ qua bất kỳ nội dung nào không nằm trong cặp dấu ngoặc nhọn `{ ... }` của đối tượng JSON kết quả cuối cùng.
- Thêm cơ chế "Pre-flush" để xóa sạch buffer nếu phát hiện pattern của mảng queries `[...]`.

### 3. Kiểm tra Prompt RAG
- Đảm bảo prompt của Tutor/RAG Agent có yêu cầu nghiêm ngặt: "Chỉ trả về JSON, không lặp lại câu hỏi hay các biến thể tìm kiếm".

## ✅ Checklist triển khai

- [x] Harden `JsonStreamCleaner` in `chat_service.py`
    - [x] Strict stripping of non-JSON prefix
    - [x] Explicitly ignore query arrays `[...]`
- [x] Refine `Offline_RAG.generate_queries` in `offline_rag.py`
    - [x] Validate config and tags isolation
- [x] Update RAG Prompt for strictness
- [x] Verify with simulated stream (manual audit) với các câu hỏi phức tạp cần multi-query.

## 📝 Nhật ký thay đổi
- **2026-04-24**: Khởi tạo tài liệu phân tích lỗi.
