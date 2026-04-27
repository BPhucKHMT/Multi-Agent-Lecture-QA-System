# Nghiên cứu fix token output cao bất thường

## 1) Triệu chứng

- Số `output_tokens` cao hơn nhiều so với phần text hiển thị cho user (chỉ vài trăm chữ).
- Nghi ngờ chính: nhánh `supervisor` tiêu tốn token dư trong bước định tuyến.

---

## 2) Bằng chứng từ code hiện tại

### A. Supervisor đang chạy theo mô hình AgentExecutor (có vòng lặp agent/tool)

Trong `src/rag_core/lang_graph_rag.py`:

- Dùng `create_tool_calling_agent(...)` + `AgentExecutor(...)`.
- `AgentExecutor` đang bật `return_intermediate_steps=True`.
- Prompt supervisor có cả:
  - `MessagesPlaceholder("chat_history")`
  - `MessagesPlaceholder("agent_scratchpad")`

=> Đây là cấu hình agent loop đầy đủ, không phải one-shot router thuần.

### B. Supervisor vẫn sinh `output_text` dù mục tiêu chính chỉ là route

`node_supervisor` lấy `result["output"]` và tạo `AIMessage(content=output_text)`, sau đó mới route bằng `tool_calls`.

=> Model có xu hướng vừa "giải thích" vừa gọi tool, làm tăng completion tokens không cần thiết cho bài toán routing.

### C. Trần token của supervisor đang khá cao cho tác vụ route

Trong `src/generation/llm_model.py`:

- `OPENAI_SUPERVISOR_MAX_TOKENS` mặc định là `1024`.

=> Với nhiệm vụ route 1 tool hoặc direct, mức này quá rộng, tạo không gian cho output dài hơn mức cần thiết.

### D. Supervisor luôn nhận cả chat history

`node_supervisor` truyền `chat_history = messages[:-1]` vào prompt.

=> History dài có thể khiến model "lý luận lại bối cảnh" nhiều hơn, làm tăng token tiêu thụ tổng thể.

---

## 3) Nguyên nhân gốc (xếp hạng khả năng)

1. **Cao nhất:** Dùng AgentExecutor cho bài toán route làm phát sinh token dư từ vòng agent/tool + scratchpad.
2. **Cao:** Prompt supervisor chưa ép output tối giản tuyệt đối (model có thể trả lời diễn giải).
3. **Trung bình:** `max_tokens=1024` cho supervisor quá rộng.
4. **Trung bình:** Chat history đưa vào supervisor quá dài cho mỗi lượt.
5. **Có thể có:** Model sinh "reasoning-heavy" completion (token usage tính cả phần không hiển thị), làm output token cao dù text cuối ngắn.

---

## 4) Hướng giảm token output (ưu tiên theo tác động/độ an toàn)

## Option A (khuyến nghị): Chuyển supervisor sang one-shot tool routing

- Thay `AgentExecutor` bằng gọi model trực tiếp với tools (`bind_tools` + `invoke`), chỉ lấy `tool_calls` hoặc direct text.
- Mục tiêu: mỗi turn supervisor chỉ 1 lần gọi model, không chạy vòng agent/tool đầy đủ.

**Lợi ích:** giảm mạnh token dư.  
**Trade-off:** cần chỉnh `node_supervisor` + test routing.

## Option B (quick win): Ép output supervisor cực ngắn

- Sửa prompt supervisor: nếu gọi tool thì **không sinh nội dung giải thích**, chỉ tool-call.
- Chỉ cho phép direct text ngắn khi thật sự không gọi tool.

**Lợi ích:** đổi nhỏ, rủi ro thấp.  
**Trade-off:** vẫn còn overhead từ AgentExecutor.

## Option C (quick win): Giảm trần token supervisor

- Giảm `OPENAI_SUPERVISOR_MAX_TOKENS` từ `1024` xuống khoảng `128`–`256`.

**Lợi ích:** thực thi nhanh, kiểm soát cost tức thì.  
**Trade-off:** nếu đặt quá thấp có thể làm route lỗi ở prompt phức tạp.

## Option D (quick win): Rút gọn chat history cho supervisor

- Chỉ truyền `N` message gần nhất (ví dụ 4–8), hoặc summary ngắn thay vì full history.

**Lợi ích:** giảm context + giảm xu hướng giải thích dài.  
**Trade-off:** có thể giảm độ chính xác route ở hội thoại dài.

## Option E (tuỳ chọn): Dùng model rẻ/nhỏ riêng cho supervisor

- Đặt `OPENAI_SUPERVISOR_MODEL` riêng, tối ưu cho classification/tool-choice.

**Lợi ích:** giảm chi phí tổng.  
**Trade-off:** cần benchmark độ chính xác route.

---

## 5) Kế hoạch đo lường để xác nhận hiệu quả

Đo trước/sau cho cùng tập câu hỏi (ít nhất gồm: chào hỏi, tutor, coding, math, quiz):

1. `supervisor_output_tokens` trung bình/median/p95.
2. `total_output_tokens` toàn workflow.
3. Tỷ lệ route đúng (tutor/coding/math/quiz/direct).
4. Độ dài text trả về cho user (để đảm bảo không cắt cụt chất lượng).

Nên log tách theo node để thấy phần tiết kiệm đến từ supervisor hay node downstream.

---

## 6) Checklist triển khai đề xuất

- [x] Thử **Option C + B** trước (giảm max token + siết prompt) để có quick win.
- [x] Chạy regression routing/stream:
  - `pytest -q tests\rag_core\test_lang_graph_rag.py tests\api\test_chat_stream.py`
- [x] In token metrics trong backend để so sánh trước/sau trên cùng test set:
  - chat thường: `[TOKEN METRICS] mode=chat input=<...> output=<...> total=<...>`
  - stream: `[TOKEN METRICS] mode=stream input=<...> output=<...> total=<...>`
- [x] Sửa lệch metric stream `0/0` khi supervisor chạy:
  - Chỉ ẩn **token text** từ `supervisor`, nhưng vẫn cộng `usage_metadata` từ `on_chat_model_end`.
- [x] Sửa fallback route khi supervisor trả rỗng (`tool_call_count=0`, `output=""`):
  - Nếu input không phải greeting, fallback có kiểm soát sang `AskTutor` thay vì rơi `direct` rỗng.
- [x] Bổ sung log để giải thích lệch `output_tokens` vs text hiển thị:
  - `[TOKEN BREAKDOWN] per_node=<node:in/out,...> visible_chars=<...> visible_tokens_estimate=<...>`
  - Dùng để thấy token cao đến từ node nào (đặc biệt `tutor`) và so với lượng text thực tế render.
- [x] Siết prompt tutor để giảm completion dư:
  - Đổi sang ràng buộc ưu tiên chất lượng: trả lời đủ ý theo độ phức tạp, tránh lan man/lặp ý, chỉ trích dẫn nguồn cần thiết.
- [ ] User chạy cùng test set trên UI để ghi số liệu before/after thực tế.
- [ ] Nếu giảm chưa đủ, triển khai **Option A** (one-shot routing, bỏ AgentExecutor loop).
- [ ] Re-run regression + benchmark token lần 2.
- [ ] Chốt cấu hình supervisor model/max_tokens theo kết quả thực nghiệm.

---

## 7) Kết luận ngắn

Khả năng cao token dư đến từ việc dùng **AgentExecutor-style supervisor** cho nhiệm vụ routing đơn giản. Nên ưu tiên quick win (siết prompt + giảm `OPENAI_SUPERVISOR_MAX_TOKENS`), sau đó chuyển sang one-shot routing nếu cần cắt chi phí mạnh và ổn định hơn.
