# Frontend — React Web Interface

`frontend/` là giao diện web của PUQ Q&A, xây dựng bằng React + Vite + TypeScript + Tailwind CSS. Frontend gọi FastAPI backend để đăng nhập, stream chat AI, xem lịch sử hội thoại và truy cập Summary Hub.

---

## Chạy frontend

Từ root project:

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

Hoặc vào thư mục frontend:

```powershell
cd frontend
npm install
npm run dev
```

App mặc định chạy tại:

```txt
http://localhost:5173
```

Backend cần chạy tại:

```txt
http://localhost:8000
```

---

## Scripts

| Lệnh | Mục đích |
|---|---|
| `npm run dev` | Chạy Vite dev server |
| `npm run build` | Type-check + build production |
| `npm run preview` | Preview build local |
| `npm run test` | Chạy Vitest |

---

## Cấu trúc thư mục

```txt
frontend/
├── src/
│   ├── app/          # App shell, routing, providers
│   ├── components/   # UI components tái sử dụng
│   ├── lib/          # API clients và utilities
│   ├── pages/        # Page-level screens
│   ├── store/        # State/conversation management
│   ├── styles/       # Global CSS/Tailwind entry
│   ├── types/        # TypeScript types
│   └── main.tsx      # React entry point
├── docs/             # Tài liệu frontend nếu có
├── ui2figma/         # Tool/phần phụ trợ xuất UI sang Figma
├── package.json
├── vite.config.ts
└── tailwind.config.js
```

---

## Luồng chính UI

```txt
Login/Register
  ↓
Gateway Selector
  ├─ Chatspace
  │    ↓
  │  POST /api/v1/chat/stream
  │    ↓
  │  Render SSE token/context/metadata
  │
  └─ Summary Hub
       ↓
     Video list + summary + jump to chat
```

---

## API integration

Frontend gọi backend qua các module trong `src/lib/api/`.

Các nhóm API chính:

- auth: login/register/refresh/logout;
- chat: stream message, history, sessions;
- videos: danh sách video và metadata;
- summary: tóm tắt video/bài giảng.

Chat dùng **SSE streaming**. Backend gửi các event dạng JSON:

```json
{"type":"status","status":"Đang truy hồi tri thức..."}
{"type":"token","content":"Nội dung trả lời..."}
{"type":"context","docs":[]}
{"type":"metadata","conversation_id":"...","response":{}}
```

---

## Công nghệ

- React 18
- TypeScript
- Vite
- Tailwind CSS
- React Router
- Framer Motion
- React Markdown + GFM
- KaTeX cho LaTeX/math
- Lucide React icons
- Vitest

---

## Quy ước khi sửa frontend

- UI text viết tiếng Việt.
- Component nên nhỏ, tập trung một nhiệm vụ.
- Logic gọi API để trong `src/lib/api/`, không nhét trực tiếp vào component lớn.
- Kiểu dữ liệu API để trong `src/types/`.
- Khi sửa chat stream, kiểm tra đủ event `status`, `token`, `context`, `metadata`, `error`, `[DONE]`.
