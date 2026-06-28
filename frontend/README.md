# Frontend — React Web Interface

`frontend/` là giao diện web của PUQ Q&A, xây dựng bằng React + Vite + TypeScript + Tailwind CSS. Frontend gọi FastAPI backend để đăng nhập, stream chat AI, xem lịch sử hội thoại và truy cập Summary Hub.

---

## Cấu trúc thư mục chi tiết

```txt
frontend/
├── .dockerignore
├── ARCHITECTURE.md           # Kiến trúc frontend chi tiết (tiếng Việt)
├── Dockerfile
├── README.md
├── index.html
├── package.json              # React 18 + Vite 7 + TypeScript + Tailwind
├── package-lock.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── vite.config.ts
├── dist/                     # Build production output
│   ├── index.html
│   └── assets/
├── src/
│   ├── main.tsx              # React entry point
│   ├── vite-env.d.ts
│   ├── README.md
│   ├── app/
│   │   ├── App.tsx           # Root app component
│   │   ├── providers.tsx     # Zustand + Context provider
│   │   ├── router.tsx        # React Router routes
│   │   └── layouts/
│   │       └── MainLayout.tsx # Layout chính (sidebar + content)
│   ├── components/
│   │   ├── README.md
│   │   ├── chat/
│   │   │   ├── ChatInput.tsx        # Input gửi câu hỏi
│   │   │   ├── CitationList.tsx     # Hiển thị citation/video timestamps
│   │   │   ├── MarkdownRenderer.tsx # Render Markdown + code + math
│   │   │   ├── MathComponent.tsx    # Render LaTeX (KaTeX)
│   │   │   ├── MessageList.tsx      # Danh sách messages
│   │   │   ├── MessageList.test.tsx # Test MessageList
│   │   │   └── QuizComponent.tsx    # Render quiz UI
│   │   ├── shared/
│   │   │   └── Icons.tsx            # Lucide React icons tập trung
│   │   └── sidebar/
│   │       └── ConversationSidebar.tsx # Sidebar lịch sử chat
│   ├── lib/
│   │   ├── README.md
│   │   ├── api/
│   │   │   ├── client.ts            # Base fetch API client
│   │   │   ├── client.test.ts       # Test client
│   │   │   ├── chat.ts              # Chat streaming API (SSE)
│   │   │   ├── chat.test.ts         # Test chat API
│   │   │   └── videos.ts            # Videos API
│   │   └── utils/
│   │       ├── citation.ts          # Citation formatting
│   │       ├── citation.test.ts     # Test citation
│   │       ├── timestamp.ts         # Timestamp formatting
│   │       └── timestamp.test.ts    # Test timestamp
│   ├── pages/
│   │   ├── README.md
│   │   ├── GatewayPage.tsx      # Entry: login/register/workspace selector
│   │   ├── LoginPage.tsx        # Trang đăng nhập
│   │   ├── RegisterPage.tsx     # Trang đăng ký
│   │   └── WorkspacePage.tsx    # Workspace chính (Chatspace + Summary Hub)
│   ├── store/
│   │   ├── README.md
│   │   ├── conversationStore.ts    # Zustand store cho chat state
│   │   └── conversationStore.test.ts
│   ├── styles/
│   │   └── globals.css         # Global CSS + Tailwind entry
│   └── types/
│       ├── README.md
│       ├── api.ts              # API response types
│       ├── app.ts              # App-level types
│       └── rag.ts              # RAG-specific types
└── ui2figma/                   # Tool xuất UI sang Figma (separate)
    ├── __init__.py
    ├── README.md
    ├── docs/
    │   └── plans/
    │       └── 2026-04-18-text-to-ui-figma-implementation.md
    │   └── specs/
    │       └── 2026-04-18-text-to-ui-figma-design.md
    ├── figma_mapper.py
    ├── mcp_client.py
    ├── mcp_executor.py
    ├── orchestrator.py
    ├── review_gate.py
    ├── run_text_to_ui.py
    ├── spec_models.py
    ├── spec_parser.py
    └── tests/
        ├── test_cli_runner.py
        ├── test_figma_mapper.py
        ├── test_mcp_client.py
        ├── test_orchestrator.py
        ├── test_review_gate.py
        └── test_spec_parser.py
```

---

## Công nghệ

- React 18 + TypeScript 5.6 + Vite 7
- Tailwind CSS 3.4 + PostCSS
- React Router 7
- Framer Motion 12 (animations)
- react-markdown + remark-gfm + remark-math + rehype-katex (Markdown + LaTeX)
- react-syntax-highlighter (code highlighting)
- KaTeX 0.16 (LaTeX math rendering)
- Lucide React (icons)
- Zustand (state management)
- Vitest (testing)

---

## Scripts

```powershell
npm --prefix frontend install    # Cài dependencies
npm --prefix frontend run dev    # Chạy Vite dev server (port 5173)
npm --prefix frontend run build  # Type-check + build production
npm --prefix frontend run preview # Preview build local
npm --prefix frontend run test   # Chạy Vitest
```

---

## Luồng chính UI

```txt
Login/Register
↓
Gateway Selector
├─ Chatspace
│   ↓
│   POST /api/v1/chat/stream (SSE)
│   ↓
│   Render token/context/metadata
│
└─ Summary Hub
    ↓
    Video list + summary + jump to chat
```

---

## API integration

Frontend gọi backend qua `src/lib/api/`:

| Module | Endpoints |
|---|---|
| `client.ts` | Base fetch wrapper, auth token injection |
| `chat.ts` | Stream chat, history, sessions (SSE) |
| `videos.ts` | Danh sách video và metadata |

Chat dùng **SSE streaming**. Backend gửi events:

```json
{"type":"status","status":"Đang truy hồi tri thức..."}
{"type":"token","content":"Nội dung trả lời..."}
{"type":"context","docs":[]}
{"type":"metadata","conversation_id":"...","response":{}}
```

---

## Quy ước khi sửa frontend

- UI text viết tiếng Việt.
- Component nên nhỏ, tập trung một nhiệm vụ.
- Logic gọi API để trong `src/lib/api/`, không nhét trực tiếp vào component lớn.
- Kiểu dữ liệu API để trong `src/types/`.
- Khi sửa chat stream, kiểm tra đủ event `status`, `token`, `context`, `metadata`, `error`, `[DONE]`.
