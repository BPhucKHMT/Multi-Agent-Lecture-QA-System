# Change Generation (OpenAI gpt-5-mini)

**Goal:** Chuyển runtime chính sang dùng `myAPIKey` với model mặc định `gpt-5-mini`, thay cho cấu hình hiện tại.

## 1. Cấu hình môi trường

```env
myAPIKey=your_openai_api_key
OPENAI_MODEL=gpt-5-mini
OPENAI_SUPERVISOR_MODEL=gpt-5-mini
```

**Ghi chú:**
- Runtime gọi trực tiếp OpenAI qua LangChain `ChatOpenAI` với `myAPIKey`.
- Không dùng biến URL gateway/proxy cho runtime.

## 2. File code cần sửa trong runtime hiện tại

| File | Trạng thái | Nội dung |
|---|---|---|
| `src/generation/llm_model.py` | Cần sửa | `get_llm()` và `get_supervisor_llm()` ưu tiên `myAPIKey`, model mặc định `gpt-5-mini` |
| `src/rag_core/lang_graph_rag.py` | Rà soát | Giữ nguyên luồng gọi `get_supervisor_llm()` |
| `src/rag_core/agents/tutor.py` | Rà soát | Giữ nguyên luồng gọi `get_llm()` |
| `src/rag_core/agents/coding.py` | Rà soát | Giữ nguyên luồng gọi `get_llm()` |
| `src/rag_core/agents/math.py` | Rà soát | Giữ nguyên luồng gọi `get_llm()` |
| `src/rag_core/agents/quiz.py` | Rà soát | Giữ nguyên luồng gọi `get_llm()` |

## 3. Kế hoạch format lại tài liệu

1. Đổi tiêu đề và Goal theo mục tiêu mới (`myAPIKey + gpt-5-mini`).
2. Chuẩn hóa cấu trúc cố định: `Cấu hình môi trường` → `File code cần sửa` → `Checklist`.
3. Loại bỏ các block cũ không còn thuộc scope hiện tại (worker refactor chi tiết, kế hoạch cũ cho Gemini).
4. Giữ checklist ngắn gọn, bám đúng code đang tồn tại trong `src/`.

## 4. Checklist triển khai

- [x] Cập nhật `src/generation/llm_model.py` để ưu tiên `myAPIKey` và default model `gpt-5-mini`.
- [x] Rà soát điểm gọi từ `src/rag_core/*` để giữ nguyên behavior routing.
- [x] Format lại tài liệu `docs/upgrade_system/Change_Generation.md` theo scope hiện tại.
- [ ] Chạy test và xác nhận không phát sinh lỗi mới ngoài baseline.

## 5. Khác biệt chính so với cấu hình cũ

- Runtime không còn ưu tiên `googleAPIKey` cho generation/supervisor.
- Model mặc định đổi sang `gpt-5-mini`.
- Không còn fallback cấu hình cũ trong runtime.
