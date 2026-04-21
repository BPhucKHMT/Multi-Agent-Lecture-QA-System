# Chatspace MVP Frontend Design (React + Vite)

## 1. Problem statement

Cần triển khai frontend mới trong thư mục `frontend/` dựa trên tài liệu hiện có và Figma, ưu tiên Chatspace MVP trước. Phạm vi MVP tập trung vào luồng chat end-to-end qua `/chat`, giữ nguyên contract backend và chưa triển khai streaming/summary trong vòng này.

## 2. Scope

### In scope
- Khởi tạo project React + Vite + TypeScript trong `frontend/`.
- Route Chatspace MVP.
- Sidebar hội thoại cơ bản.
- Message list + chat input.
- Gọi API `POST /chat`.
- Render citation theo index `[n]` với timestamp link.
- Xử lý lỗi mạng/timeout với retry.

### Out of scope
- `POST /chat/stream` (để phase sau).
- Summary Hub.
- Pixel-perfect toàn bộ theo Figma.
- Thay đổi backend contract hoặc logic RAG.

## 3. Constraints

- Giữ strict RagResponse keys: `text`, `video_url`, `title`, `filename`, `start_timestamp`, `end_timestamp`, `confidence`, `type`.
- Metadata arrays phải xử lý đồng bộ theo index.
- Nếu citation index vượt mảng thì giữ nguyên `[n]`.
- Timestamp không hợp lệ fallback `t=0`.
- Nếu metadata arrays lệch độ dài thì cảnh báo mềm, vẫn render text chính.

## 4. Architecture

Frontend tách lớp rõ để giảm rủi ro:

1. `pages/`
   - `ChatPage`: layout chính Chatspace MVP.
2. `components/`
   - `ConversationSidebar`, `MessageList`, `ChatInput`, `CitationList`.
3. `lib/api/`
   - `client.ts`: axios client + timeout/env config.
   - `chat.ts`: API call `/chat`.
4. `lib/utils/`
   - `timestamp.ts`: chuyển `HH:MM:SS` -> seconds.
   - `citation.ts`: parse citation index và map metadata.
5. `types/`
   - `api.ts`, `rag.ts` để khóa contract.
6. `store/`
   - Quản lý conversation hiện tại, messages, error/loading, retry payload gần nhất.

## 5. Data flow

1. User submit prompt từ `ChatInput`.
2. Store append optimistic user message.
3. API layer gửi `/chat` với payload conversation hiện tại.
4. Nhận `response` từ backend.
5. Parse citation trong `text`, map metadata theo index.
6. Render assistant message + citation links có timestamp.
7. Nếu lỗi, giữ user message và bật retry cho payload gần nhất.

## 6. Error handling

- Timeout/network: hiển thị error banner + retry action.
- Response thiếu metadata: render text chính và cảnh báo mềm.
- Citation lỗi index/timestamp: fallback theo rules ở mục Constraints.
- Không swallow lỗi; đưa về state hiển thị rõ cho user.

## 7. Testing strategy (MVP)

### Unit
- `timestamp_to_seconds`.
- Citation parser/remap.

### Integration
- Luồng `/chat` thành công: render text + citation link đúng timestamp.
- Luồng `/chat` lỗi: hiển thị lỗi + retry giữ payload gần nhất.

## 8. Delivery plan (single vertical slice)

1. Bootstrap project và cấu trúc source tối thiểu.
2. Implement Chatspace route + layout cơ bản.
3. Nối API `/chat` và optimistic update.
4. Implement citation mapping + timestamp URL.
5. Bổ sung handling lỗi + retry.
6. Viết unit/integration tests trong phạm vi MVP.

## 9. Success criteria

- Chạy được `frontend/` độc lập bằng Vite.
- Gửi câu hỏi qua `/chat` và nhận phản hồi hiển thị đúng.
- Citation click mở đúng timestamp.
- Lỗi mạng/timeout có thông báo và retry hoạt động.
- Không thay đổi backend contract.
