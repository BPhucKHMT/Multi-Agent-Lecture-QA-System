# Detailed Frontend Implementation Guide

## 1) Mục tiêu tài liệu

Tài liệu này mô tả **thuần triển khai kỹ thuật frontend** cho hệ thống mới:
- Cấu trúc code.
- API cần gọi.
- ENV cần cấu hình.
- Cách cài đặt, chạy, build, deploy.
- Các quy tắc state/data handling để hỗ trợ nhiều user.

**Không bao gồm** chi tiết mỹ thuật UI/visual design. Phần đó nằm ở `docs/frontend_ui.md`.

---

## 2) Current status và target

## 2.1 Current status

- Backend FastAPI hiện có endpoint:
  - `GET /`
  - `POST /chat`
  - `POST /chat/stream` (SSE)
- Frontend Streamlit đang chạy production baseline.
- Workspace `frontend/` là nơi build React mới.

## 2.2 Target

- Frontend React + TypeScript + Vite.
- Tách 2 khu vực:
  1. Summary Hub (dashboard tĩnh, trigger summarize).
  2. Chatspace (hội thoại, citation, streaming).
- Hỗ trợ multi-user tạm bằng `anonymous_user_id + device_id` ở localStorage (hybrid-ready cho phase auth/redis sau).

---

## 3) Prerequisites & setup

## 3.1 Runtime requirements

- Node.js 20+
- npm 10+
- Python 3.12+ (để chạy backend local)

## 3.2 Bootstrap frontend workspace

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install @tanstack/react-query axios react-router-dom
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

## 3.3 Run local

Terminal 1 (backend):
```bash
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2 (frontend):
```bash
cd frontend
npm run dev
```

---

## 4) ENV configuration (frontend)

Tạo file `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT_MS=360000
VITE_ENABLE_STREAMING=true
VITE_ENABLE_SUMMARY_HUB=true
VITE_LOG_LEVEL=info
```

## 4.1 ENV notes

- `VITE_API_BASE_URL`: base URL cho API backend.
- `VITE_API_TIMEOUT_MS`: timeout request (ms).
- `VITE_ENABLE_STREAMING`: bật luồng SSE từ `/chat/stream`.
- `VITE_ENABLE_SUMMARY_HUB`: bật route Summary Hub.
- `VITE_LOG_LEVEL`: `debug|info|warn|error`.

---

## 5) API integration map

## 5.1 Health check

- **GET** `/`
- Mục đích: kiểm tra backend khả dụng khi app khởi động.

## 5.2 Chat API (non-stream)

- **POST** `/chat`
- Request:

```json
{
  "conversation_id": "string",
  "messages": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ],
  "user_message": "string"
}
```

- Response envelope:

```json
{
  "conversation_id": "string",
  "response": { "text": "...", "type": "rag" },
  "updated_at": "ISO8601"
}
```

`response` bên trong phải tương thích format RAG hiện có:

```ts
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

## 5.3 Chat streaming API

- **POST** `/chat/stream`
- Request giống `/chat`.
- Response là SSE:
  - `data: {"type":"token","content":"..."}`
  - `data: {"type":"metadata","response":{...}}`
  - `data: [DONE]`

## 5.4 Summary API status

- Theo hướng kiến trúc mở rộng, Summary Hub cần endpoint summarize riêng (ví dụ `POST /summarize`).
- **Hiện trạng:** endpoint này chưa được chuẩn hóa trong API hiện tại.
- **Khuyến nghị khi triển khai frontend:**
  1. Tạo adapter `summary.ts` với interface rõ ràng ngay từ đầu.
  2. Gắn feature flag `VITE_ENABLE_SUMMARY_HUB`.
  3. Khi backend chốt endpoint thật, chỉ đổi adapter.

---

## 6) User context & state model (multi-user ready)

## 6.1 User context tạm

Lưu trong localStorage:

```ts
type UserContext = {
  anonymous_user_id: string;
  device_id: string;
};
```

## 6.2 Namespace keys

```ts
type SummaryKey = `summary:${string}:${string}`; // summary:{user_id}:{video_id}
type ChatKey = `chat:${string}:${string}`; // chat:{user_id}:{conversation_id}
```

Mọi cache/store key phải có prefix theo user để tránh leak dữ liệu.

## 6.3 Header chuẩn hóa (khuyến nghị)

Đính kèm trên mọi request:
- `X-Anonymous-User-Id`
- `X-Device-Id`

---

## 7) Frontend source tree đề xuất

```text
frontend/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── providers.tsx
│   │   └── router.tsx
│   ├── pages/
│   │   ├── SummaryHubPage.tsx
│   │   └── ChatPage.tsx
│   ├── components/
│   │   ├── summary/
│   │   ├── chat/
│   │   └── sidebar/
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── chat.ts
│   │   │   └── summary.ts
│   │   └── utils/
│   │       ├── citation.ts
│   │       ├── timestamp.ts
│   │       └── userContext.ts
│   ├── store/
│   │   ├── conversationStore.ts
│   │   └── summaryStore.ts
│   ├── types/
│   │   ├── api.ts
│   │   └── rag.ts
│   └── styles/
│       └── globals.css
└── ...
```

---

## 8) Error handling contract (frontend)

1. Timeout/network:
   - Giữ optimistic user message.
   - Hiển thị retry action.
2. SSE metadata missing:
   - Fallback text error + type `error`.
3. Citation index out-of-range:
   - Giữ nguyên `[n]`.
4. Invalid timestamp:
   - Fallback `t=0`.
5. Metadata arrays lệch độ dài:
   - Cảnh báo mềm, vẫn render text chính.

---

## 9) Build / deploy / rollback

## 9.1 Build commands

```bash
cd frontend
npm run build
npm run preview
```

## 9.2 Deploy strategy

- Phase đầu: chạy React song song Streamlit.
- Chuyển default UI sang React khi parity đạt yêu cầu.

## 9.3 Rollback

- Nếu lỗi nghiêm trọng frontend React:
  - Chuyển default UI về Streamlit.
  - Backend không cần rollback nếu contract không đổi.

---

## 10) Testing checklist cho frontend

## 10.1 Unit

- `timestamp_to_seconds`
- citation parser/remap
- user context key builder

## 10.2 Integration

- `/chat` end-to-end render đúng citation.
- `/chat/stream` token + metadata hoàn chỉnh.
- 2 user contexts song song không trộn cache.

## 10.3 Smoke

- Backend + frontend chạy local đồng thời.
- Summary Hub -> Chatspace giữ ngữ cảnh video.

---

## 11) Liên kết tài liệu

- UI/UX và Figma handoff: `docs/frontend_ui.md`
- Kiến trúc mở rộng hệ thống: `docs/upgrade_system/expand_system.md`
- Kiến trúc build frontend tổng quan: `frontend/docs/build_frontend.md`
