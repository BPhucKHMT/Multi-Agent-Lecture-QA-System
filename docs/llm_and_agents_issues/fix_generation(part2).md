# Fix generation bị rỗng trong `/chat/stream` (GPT-5 mini)

## 1) Triệu chứng thực tế

Từ log:

- `POST /chat/stream` trả HTTP 200 nhưng response cuối bị lỗi.
- Có `CHAIN_END response_preview=` rỗng (xuất hiện 2 lần).
- Server cảnh báo:
  - `WARN empty/invalid response payload: {'text': '', ..., 'type': 'direct'}`
- Frontend nhận:
  - `Lỗi streaming: Không nhận được metadata phản hồi cuối.`

Các câu hỏi bị ảnh hưởng (ví dụ): `tạo quiz cnn`, `linear regression là gì`.

---

## 2) Luồng gây lỗi

1. `src/api/services/chat_service.py::generate_stream` đọc `on_chain_end` và lấy `output["response"]`.
2. `response` cuối cùng có `type: "direct"` nhưng `text == ""`.
3. Vì `text` rỗng, `generate_stream` đổi sang payload lỗi streaming.

Điểm mấu chốt: lỗi phát sinh **trước** lớp SSE, nằm ở logic supervisor/direct trong graph.

---

## 3) Root cause khả dĩ cao nhất

### RC1 — Parse output từ supervisor chưa tương thích ổn định với GPT-5 mini

Trong `src/rag_core/lang_graph_rag.py::node_supervisor` đang dùng:

- `llm.generate([msgs])`
- rồi cố đọc `result.generations[0][0].text` hoặc `.message.content`
- sau đó tự parse JSON để tìm tool call.

Với GPT-5 mini, output assistant có thể không nằm đúng shape mà đoạn code đang kỳ vọng (hoặc `content` rỗng / không phải text thuần), dẫn đến:

- `tool_calls` không được nhận diện
- router rơi về nhánh `direct`
- `direct` lấy `last_message.content` từ assistant nhưng giá trị rỗng.

### RC2 — Nhánh `direct` không có fallback khi content rỗng

`node_direct_answer` hiện trả thẳng `last_message.content`. Nếu content rỗng thì toàn response bị rỗng.

---

## 4) Cách fix đề xuất (ưu tiên theo thứ tự)

### Fix A (quan trọng nhất): chuẩn hóa supervisor sang message-level API

Sửa `node_supervisor`:

1. Dùng `llm.invoke(msgs)` thay vì `llm.generate([msgs])`.
2. Đọc output từ `AIMessage` một cách an toàn:
   - nếu `content` là string → dùng trực tiếp
   - nếu `content` là list block → nối text block thành chuỗi
3. Nếu model trả tool calls trong message metadata thì ưu tiên dùng tool calls đó trước khi fallback parse JSON text.
4. Nếu không parse được tool call và text rỗng, trả câu trả lời direct an toàn (không để rỗng).

### Fix B (guardrail): direct fallback không bao giờ rỗng

Sửa `node_direct_answer`:

- Nếu `last_message.content` rỗng, trả thông điệp mặc định ngắn:
  - `"Mình chưa nhận được nội dung rõ ràng, bạn thử diễn đạt lại giúp mình nhé."`
- Không fallback sang human message và không echo lại prompt người dùng.

### Fix C (quan sát lỗi tốt hơn): tăng log chẩn đoán supervisor

Thêm log ngắn trong `node_supervisor`:

- kiểu dữ liệu output (`str` / `list` / khác)
- có/không có tool_calls
- router quyết định node nào.

Mục tiêu: lần sau nhìn log biết lỗi nằm ở parse, route hay generation.

---

## 5) Test regression nên thêm

File đề xuất: `tests/rag_core/test_lang_graph_rag.py`, `tests/api/test_chat_stream.py`

1. **Supervisor trả content block/list**  
   Kỳ vọng: vẫn trích xuất text/tool_call đúng.

2. **Supervisor không tool_call + text rỗng**  
   Kỳ vọng: route `direct` nhưng `response.text` không rỗng (nhờ fallback).

3. **`/chat/stream` với response direct rỗng từ graph**  
   Kỳ vọng: metadata cuối vẫn hợp lệ và text không rỗng sau guardrail.

---

## 6) Kiểm tra sau khi fix

Dùng lại các câu hỏi đã lỗi:

- `tạo quiz cnn`
- `linear regression là gì`

Kỳ vọng:

1. Không còn `WARN empty/invalid response payload ... type='direct'`.
2. Không còn lỗi frontend: `Không nhận được metadata phản hồi cuối`.
3. Nhánh quiz phải route sang `type: "quiz"` khi prompt yêu cầu tạo quiz.

---

## 7) Nhật ký thực thi (Task 4)

### Phạm vi self-review

- `src/rag_core/lang_graph_rag.py`
- `tests/rag_core/test_lang_graph_rag.py`
- `tests/api/test_chat_stream.py`

### Kết quả triển khai theo Fix A/B/C

- **Fix A**: Đã chuyển supervisor sang `llm.invoke(msgs)`; bổ sung các hàm chuẩn hóa để đọc an toàn `AIMessage.content` (string/list block), lấy tool calls từ `message.tool_calls`, `additional_kwargs.tool_calls`, và fallback parse JSON text. Router ưu tiên `state.tool_calls` để điều hướng node.
- **Fix B**: `node_direct_answer` trả fallback mặc định `"Mình chưa nhận được nội dung rõ ràng, bạn thử diễn đạt lại giúp mình nhé."` khi direct text rỗng; không fallback sang human message, không echo prompt người dùng.
- **Fix C**: Đã bổ sung log chẩn đoán nhẹ trong `node_supervisor` (kiểu `content`, số lượng `tool_calls`, nguồn phát hiện) và trong `router` (quyết định route + nguồn `tool_calls`).

### Bằng chứng test (targeted suites)

- Lệnh: `python -m pytest tests\rag_core\test_lang_graph_rag.py tests\api\test_chat_stream.py -q`
- Kết quả: `14 passed` (lần chạy gần nhất).
- Bao phủ chính: parse tool_call từ nhiều dạng output, route quiz qua metadata tool_call, fallback direct không rỗng, stream xử lý lỗi payload rỗng và giữ metadata cuối hợp lệ.

### Hạn chế/rủi ro hiện tại

- Log chẩn đoán supervisor/router hiện là mức lightweight; mức quan sát thực tế còn phụ thuộc cấu hình logging runtime (level/handler).
