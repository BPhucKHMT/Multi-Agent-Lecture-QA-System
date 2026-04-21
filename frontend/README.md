# Frontend Workspace (Vite + React + TypeScript)

Thu muc nay chua workspace frontend moi su dung Vite + React + TypeScript.

## Run workspace

```bash
npm install
npm run dev
```

Build production:

```bash
npm run build
```

Chạy từ root project (tùy chọn):

```bash
npm --prefix frontend install
npm --prefix frontend run dev
npm --prefix frontend run build
```

## Chatspace MVP local run

1) Chạy backend FastAPI ở root project:

```bash
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

2) Chạy frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend mặc định gọi backend tại `http://localhost:8000` (có thể override bằng `VITE_API_BASE_URL`).

## ui2figma

Tai lieu va cac file Python cho luong text-to-ui/Figma duoc dat tai:

- `frontend/ui2figma/docs/`
- `frontend/ui2figma/*.py`
