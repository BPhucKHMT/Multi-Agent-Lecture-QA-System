# Thiết kế build frontend React thay Streamlit (Vite + TypeScript)

## 1) Mục tiêu và phạm vi

### Mục tiêu
- Thay frontend Streamlit hiện tại bằng React theo lộ trình ít rủi ro.
- Giữ nguyên backend FastAPI và contract phản hồi RAG trong giai đoạn MVP.
- Đảm bảo trải nghiệm tương đương: chat, sidebar hội thoại, citation có timestamp.

### In scope
- Thiết kế kiến trúc frontend React mới.
- Thiết kế cấu trúc thư mục và component boundaries.
- Thiết kế state/data flow cho chat và hội thoại.
- Lộ trình migration theo phase và kế hoạch rollback.
- Rủi ro chính và chiến lược kiểm thử.

### Out of scope
- Thay đổi logic cốt lõi của RAG pipeline (`rag/`, `retriever/`, `generation/`).
- Thay đổi JSON response contract của backend.
- Triển khai persistent conversation DB trong MVP đầu tiên.

## 2) Kết luận review nhanh

| Hạng mục | Trạng thái | Nhận xét |
|---|---|---|
| Kiến trúc tổng thể | Tốt | Hướng Strangler + contract-first phù hợp và rủi ro thấp. |
| Bố cục luồng dữ liệu | Cần chi tiết thêm | Đã có flow chính, nhưng thiếu flow lỗi/edge-case theo từng bước input-output. |
| Prompt/spec chuẩn web product | Thiếu | Chưa có section chuẩn hóa prompt/spec để team dev/AI triển khai đồng nhất. |

## 3) Phương án kiến trúc đã chọn

Chọn mô hình **Strangler-fig frontend**:
- Dựng React app mới chạy song song với Streamlit.
- Giữ FastAPI làm backend duy nhất.
- Migration theo phase, có thể rollback về Streamlit khi cần.

Lý do chọn:
- Rủi ro thấp, giảm nguy cơ downtime.
- Tách rõ phạm vi frontend refactor khỏi backend RAG.
- Dễ so sánh parity giữa UI cũ và mới.

## 4) Kiến trúc tổng thể

Luồng chính:

`User -> React UI -> FastAPI /chat -> LangGraph/RAG -> JSON response -> React render`

Nguyên tắc:
- Backend contract giữ nguyên để giảm coupling khi chuyển UI.
- React là lớp hiển thị + điều phối state phía client.
- Streamlit giữ vai trò fallback trong các phase đầu.

### 4.1 Phân tầng frontend

1. **Presentation layer (`pages/`, `components/`)**
   - Nhận tương tác user, render message/citation/sidebar.
2. **Application state layer (`store/`, React Query)**
   - Điều phối state hội thoại, loading, error, retry.
3. **Integration layer (`lib/api/`, `lib/utils/`)**
   - Gọi API, parse citation, chuẩn hóa timestamp/link.
4. **Contract layer (`types/`)**
   - Định nghĩa kiểu dữ liệu request/response để tránh lệch contract backend.

## 5) Stack công nghệ frontend

- **Build tool:** Vite
- **Framework:** React
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Server-state:** React Query

## 6) Cấu trúc thư mục đề xuất (frontend)

```text
frontend/
├── public/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── providers.tsx
│   │   └── router.tsx
│   ├── pages/
│   │   └── ChatPage.tsx
│   ├── components/
│   │   ├── chat/
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageItem.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   └── CitationList.tsx
│   │   └── sidebar/
│   │       ├── ConversationList.tsx
│   │       ├── SearchBox.tsx
│   │       └── ConversationActions.tsx
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   └── chat.ts
│   │   └── utils/
│   │       ├── citation.ts
│   │       └── timestamp.ts
│   ├── store/
│   │   └── conversationStore.ts
│   ├── types/
│   │   ├── api.ts
│   │   └── rag.ts
│   └── styles/
│       └── globals.css
├── index.html
├── package.json
└── tsconfig.json
```

## 7) API contract và kiểu dữ liệu

Request tối thiểu frontend gửi về backend:

```ts
type ChatRequest = {
  conversation_id: string;
  messages: { role: "user" | "assistant"; content: string }[];
  user_message: string;
};
```

Response giữ nguyên contract hiện tại (dạng envelope):

```ts
type ChatResponseEnvelope = {
  conversation_id: string;
  response: RagResponse;
  updated_at: string;
};

type RagResponse = {
  text: string;
  video_url: string[];
  title: string[];
  filename: string[];
  start_timestamp: string[];
  end_timestamp: string[];
  confidence: ("high" | "medium" | "low" | "zero")[];
  type: "rag" | "direct" | "error";
};
```

Ràng buộc dữ liệu:
- Các mảng `video_url/title/filename/start_timestamp/end_timestamp/confidence` phải cùng độ dài.
- Citation `[n]` trong `text` map theo đúng index mảng metadata.
- Frontend không tự suy diễn/chỉnh sửa dữ liệu citation ngoài các fallback đã định nghĩa.

## 8) State management và data flow

### 8.1 Server state (React Query)
- Mutation gửi câu hỏi tới `/chat`.
- Query/mutation quản lý loading, error, retry policy.
- Cache theo `conversation_id`.

### 8.2 Client state (conversationStore)
- Danh sách hội thoại đang mở trong session.
- `current_conversation_id`.
- Message history đang hiển thị.
- Trạng thái UI cục bộ (search query, chọn conversation).

### 8.3 Data flow chi tiết theo kịch bản

#### A. Success flow (gửi câu hỏi thành công)
1. `ChatInput` phát event `submit(user_message)`.
2. Store append optimistic user message vào `messages[current_conversation_id]`.
3. API client gửi `ChatRequest` tới `/chat`.
4. Backend trả `ChatResponseEnvelope` và `RagResponse` nằm trong field `response`.
5. UI parse citation trong `text`, map metadata theo index, render link timestamp.
6. Store append assistant message và cập nhật trạng thái `idle`.

#### B. Error flow (timeout/network/API error)
1. Mutation thất bại (timeout hoặc HTTP error).
2. Store chuyển trạng thái `error`.
3. UI hiển thị error banner + action retry.
4. Không xóa optimistic user message; retry dùng lại payload gần nhất.

#### C. Citation edge flow (metadata mismatch)
1. Khi parse `[n]`, nếu `n` vượt mảng metadata thì giữ nguyên `[n]`.
2. Timestamp không hợp lệ thì fallback `0` giây.
3. Nếu độ dài metadata arrays không đồng nhất thì hiển thị cảnh báo mềm, vẫn render nội dung text chính.

#### D. Switch conversation flow
1. User chọn conversation ở sidebar.
2. Store cập nhật `current_conversation_id`.
3. MessageList đọc dữ liệu theo conversation mới và render tức thì từ local store/cache.
4. Không phát sinh request mới trừ khi user gửi prompt mới.

## 9) Chiến lược render citation

Frontend cần tái hiện hành vi Streamlit:
- Parse `[n]` trong `text`.
- Với mỗi `n`, lấy `video_url[n]`, `title[n]`, `start_timestamp[n]`.
- Convert timestamp `HH:MM:SS` sang giây để tạo URL `?t=<seconds>` hoặc `&t=<seconds>`.
- Render link trích dẫn và danh sách nguồn tham khảo.

Fallback an toàn:
- Nếu citation index vượt mảng, giữ nguyên chuỗi gốc `[n]`.
- Nếu timestamp không hợp lệ, fallback `0` giây.
- Nếu mảng không đồng nhất độ dài, hiển thị cảnh báo mềm và vẫn render text.

## 10) Roadmap migration theo phase

### Phase A — Bootstrap React app
- Khởi tạo `frontend/` với Vite + React + TS + Tailwind + React Query.
- Tạo layout khung chat và sidebar.
- Thiết lập API base URL và health check backend.

**Exit criteria**
- Frontend React chạy ổn định local.
- Có thể gọi endpoint health backend thành công.

### Phase B — Chat MVP parity
- Implement chat input/output.
- Implement conversation list + tạo mới/chuyển/xóa/reset (mức parity với UI hiện tại).
- Implement citation rendering và source list.

**Exit criteria**
- Luồng hỏi đáp chạy end-to-end qua `/chat`.
- Câu trả lời RAG hiển thị citation mở đúng video/timestamp.

### Phase C — Hardening và cutover
- Bổ sung xử lý lỗi mạng, timeout, retry hợp lý.
- Bổ sung loading skeleton và error boundary.
- Chuyển entrypoint mặc định từ Streamlit sang React (giữ Streamlit fallback).

**Exit criteria**
- React là UI mặc định trong môi trường dev/deploy mục tiêu.
- Có đường rollback rõ ràng về Streamlit.

### Phase D — Cleanup
- Cập nhật docs chạy/triển khai cho frontend mới.
- Gỡ phần phụ thuộc Streamlit không còn cần thiết.
- Chốt kế hoạch deprecate Streamlit.

**Exit criteria**
- Tài liệu đồng bộ với kiến trúc mới.
- Không còn bước vận hành bắt buộc phụ thuộc Streamlit.

## 11) Rủi ro và giảm thiểu

1. **Sai lệch hành vi citation giữa Streamlit và React**
   - Giảm thiểu: viết unit test cho hàm parse/remap citation.
2. **State hội thoại không đồng bộ với backend in-memory**
   - Giảm thiểu: chuẩn hóa thứ tự append message và xử lý lỗi mutation.
3. **UX regression trong thao tác sidebar**
   - Giảm thiểu: integration test cho create/switch/delete/reset conversation.
4. **Độ trễ API ảnh hưởng cảm nhận người dùng**
   - Giảm thiểu: loading states rõ ràng, timeout/retry có kiểm soát.

## 12) Kế hoạch kiểm thử

### Unit tests (frontend)
- `timestamp_to_seconds`.
- `citation remap` và URL builder.
- Guard kiểm tra đồng nhất độ dài mảng metadata.

### Integration tests (frontend)
- Gửi câu hỏi -> nhận phản hồi -> render citation.
- Chuyển hội thoại và giữ đúng message list.
- Xử lý lỗi API và fallback UI.

### Smoke tests (end-to-end)
- Backend FastAPI + React frontend chạy đồng thời.
- Hỏi một câu có citation, mở link đúng timestamp.

## 13) Rollout và rollback

Rollout:
- Bật React theo môi trường (dev -> staging -> production).
- Giữ Streamlit chạy song song trong thời gian ổn định ban đầu.

Rollback:
- Nếu phát sinh lỗi nghiêm trọng ở React, chuyển traffic/UI default về Streamlit.
- Không cần rollback backend vì contract không đổi trong MVP.

## 14) Prompt chuẩn web product (template dùng cho team dev/AI)

Mục này dùng như prompt/spec chuẩn hóa để triển khai đồng nhất giữa dev team và AI coding tools.

```text
Bạn là frontend engineer cho sản phẩm Q&A RAG của UIT.

[Product context]
- Mục tiêu: thay Streamlit UI bằng React UI, giữ nguyên FastAPI contract.
- Không thay đổi logic RAG backend và không phá vỡ JSON response contract.

[Target users]
- Sinh viên cần hỏi đáp nhanh, mở citation theo timestamp để kiểm chứng nguồn.

[Core user journeys]
1) Gửi câu hỏi và nhận câu trả lời có citation.
2) Chuyển giữa các conversation và giữ đúng history.
3) Retry khi lỗi mạng/timeout mà không mất ngữ cảnh.

[Functional requirements]
- Chat input/output parity với Streamlit.
- Citation parse và mở đúng video + timestamp.
- Sidebar hỗ trợ tạo/chuyển/xóa/reset conversation.

[Non-functional requirements]
- UI phản hồi nhanh (optimistic update cho user message).
- Error states rõ ràng, retry có kiểm soát.
- Tách lớp code rõ: components, store, api, utils, types.

[Contract constraints]
- RagResponse fields bắt buộc: text, video_url, title, filename, start_timestamp, end_timestamp, confidence, type.
- Metadata arrays phải được xử lý đồng bộ theo index citation.

[Acceptance criteria]
- E2E hỏi đáp qua /chat thành công.
- Citation bấm mở đúng timestamp.
- Luồng lỗi mạng hiển thị đúng và retry hoạt động.
- Không thay đổi backend contract.
```

## 15) Tiêu chí hoàn thành

- React frontend đạt parity chức năng chat chính so với Streamlit hiện tại.
- Không làm thay đổi response contract RAG.
- Người dùng mở được citation chính xác theo timestamp.
- Có tài liệu vận hành rõ cho frontend mới và phương án rollback.
- Có prompt/spec chuẩn web product để triển khai đồng nhất.

## 16) Checklist triển khai

- [x] Bootstrap React workspace.
- [x] Chatspace MVP `/chat`.
- [x] Citation timestamp fallback.
- [x] Error + retry cơ bản.

## 17) Tiến độ và kiểm chứng (Task5 review fix)

- Đã cập nhật tài liệu `/chat` theo envelope `{"conversation_id","response","updated_at"}`; `RagResponse` được giữ nested trong `response`.
- Đã làm rõ lệnh chạy trong `frontend/README.md` cho ngữ cảnh chạy từ thư mục `frontend`.

Kết quả lệnh kiểm chứng:
- `npm --prefix frontend run test`: pass (`4` test files, `9` tests).
- `npm --prefix frontend run build`: pass.
- `pytest -q tests`: fail baseline `2` tests (`tests/rag_core/test_offline_rag_context.py::test_get_context_total_serialized_size_is_capped`, `tests/rag_core/agents/test_math_agent.py::test_generate_derivation_formats_verification_formulas_as_latex`) và nằm ngoài phạm vi frontend/docs.
