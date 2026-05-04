# frontend/src — Application Source

`frontend/src/` chứa source code chính của React app.

---

## Cấu trúc

```txt
src/
├── app/          # Root app, routes, providers
├── components/   # UI components
├── lib/          # API clients + utilities
├── pages/        # Page-level screens
├── store/        # Client state management
├── styles/       # Global CSS/Tailwind
├── types/        # TypeScript contracts
└── main.tsx      # Entry point
```

---

## Luồng render chính

```txt
main.tsx
  ↓
App providers/routes
  ↓
Page
  ↓
Components
  ↓
API client trong lib/api
  ↓
FastAPI backend
```

---

## Quy ước

- Page xử lý layout cấp màn hình.
- Component xử lý UI nhỏ/tái sử dụng.
- API call để trong `lib/api`.
- Type chung để trong `types`.
- Store dùng cho state cần chia sẻ giữa nhiều component/page.
