# types — TypeScript Contracts

`frontend/src/types/` chứa type/interface dùng chung trong React app.

---

## Vai trò

Types giúp đồng bộ contract giữa frontend và backend:

- user/auth response;
- chat message/session;
- SSE stream event;
- video metadata;
- RAG response/citation.

---

## Khi nào sửa types?

- Backend response schema đổi.
- Thêm field mới vào chat metadata.
- Thêm page/API mới cần contract rõ ràng.
- Refactor message/session state.

---

## Quy ước

- Type đặt tên rõ nghiệp vụ: `ChatMessage`, `ConversationSession`, `VideoMetadata`.
- Không dùng `any` nếu có thể mô tả shape.
- Nếu field optional do backend không luôn trả, đánh dấu `?` rõ ràng.
