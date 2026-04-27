# Chatspace MVP Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Triển khai Chatspace MVP trong `frontend/` bằng React + Vite + TypeScript, gọi `/chat` và render citation timestamp đúng contract hiện tại.

**Architecture:** Dùng vertical-slice: dựng một luồng hoàn chỉnh từ `ChatInput` đến API `/chat` và render `MessageList` + `CitationList`. Tách rõ `types`, `lib/api`, `lib/utils`, `store`, `components`, `pages` để dễ kiểm soát contract và fallback. Streaming (`/chat/stream`) và Summary Hub để phase sau.

**Tech Stack:** React 18, Vite, TypeScript, Axios, React Query, React Router, Tailwind CSS, Vitest.

---

## File Structure

- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/postcss.config.js`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/styles/globals.css`
- Create: `frontend/src/app/App.tsx`
- Create: `frontend/src/app/providers.tsx`
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/pages/ChatPage.tsx`
- Create: `frontend/src/components/chat/ChatInput.tsx`
- Create: `frontend/src/components/chat/MessageList.tsx`
- Create: `frontend/src/components/chat/CitationList.tsx`
- Create: `frontend/src/components/sidebar/ConversationSidebar.tsx`
- Create: `frontend/src/lib/api/client.ts`
- Create: `frontend/src/lib/api/chat.ts`
- Create: `frontend/src/lib/utils/timestamp.ts`
- Create: `frontend/src/lib/utils/citation.ts`
- Create: `frontend/src/lib/utils/userContext.ts`
- Create: `frontend/src/store/conversationStore.ts`
- Create: `frontend/src/types/rag.ts`
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/src/lib/utils/timestamp.test.ts`
- Create: `frontend/src/lib/utils/citation.test.ts`
- Create: `frontend/src/lib/api/chat.test.ts`
- Modify: `frontend/README.md`
- Modify: `frontend/docs/build_frontend.md` (update checklist tiến độ theo AGENTS.md)

### Task 1: Bootstrap React workspace in `frontend/`

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig*.json`, `frontend/vite.config.ts`, `frontend/index.html`
- Create: `frontend/src/main.tsx`, `frontend/src/styles/globals.css`, `frontend/src/vite-env.d.ts`
- Modify: `frontend/README.md`
- Test: `npm --prefix frontend run build`

- [ ] **Step 1: Write the failing build check**

```bash
npm --prefix frontend run build
```

Expected: FAIL vì chưa có `package.json`/Vite project.

- [ ] **Step 2: Add minimal project config**

```json
{
  "name": "puq-chatspace-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.59.20",
    "axios": "^1.7.7",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.0.1",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.14",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.4"
  }
}
```

```tsx
// frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/App";
import "./styles/globals.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 3: Install dependencies**

Run: `npm --prefix frontend install`  
Expected: install complete, lockfile created.

- [ ] **Step 4: Run build to verify bootstrap passes**

Run: `npm --prefix frontend run build`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/tsconfig.app.json frontend/tsconfig.node.json frontend/vite.config.ts frontend/index.html frontend/src/main.tsx frontend/src/styles/globals.css frontend/src/vite-env.d.ts frontend/README.md
git commit -m "feat(frontend): bootstrap react vite workspace"
```

### Task 2: Define API contracts and client for `/chat`

**Files:**
- Create: `frontend/src/types/rag.ts`, `frontend/src/types/api.ts`
- Create: `frontend/src/lib/api/client.ts`, `frontend/src/lib/api/chat.ts`
- Create: `frontend/src/lib/api/chat.test.ts`
- Test: `npm --prefix frontend run test -- src/lib/api/chat.test.ts`

- [ ] **Step 1: Write failing API contract test**

```ts
// frontend/src/lib/api/chat.test.ts
import { describe, expect, it } from "vitest";
import { normalizeChatResponse } from "./chat";

describe("normalizeChatResponse", () => {
  it("returns strict rag response shape", () => {
    const output = normalizeChatResponse({
      conversation_id: "c1",
      response: { text: "hello", type: "direct" }
    });
    expect(output.response.text).toBe("hello");
    expect(output.response.video_url).toEqual([]);
    expect(output.response.start_timestamp).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/lib/api/chat.test.ts`  
Expected: FAIL because `normalizeChatResponse` chưa tồn tại.

- [ ] **Step 3: Implement minimal API types and normalize logic**

```ts
// frontend/src/types/rag.ts
export type ConfidenceLevel = "high" | "medium" | "low" | "zero";

export type RagResponse = {
  text: string;
  video_url: string[];
  title: string[];
  filename: string[];
  start_timestamp: string[];
  end_timestamp: string[];
  confidence: ConfidenceLevel[];
  type: "rag" | "direct" | "error";
};
```

```ts
// frontend/src/types/api.ts
import type { RagResponse } from "./rag";

export type ChatMessage = { role: "user" | "assistant"; content: string };
export type ChatRequest = { conversation_id: string; messages: ChatMessage[]; user_message: string };
export type ChatResponseEnvelope = { conversation_id: string; response: Partial<RagResponse>; updated_at?: string };
export type NormalizedChatResponse = { conversation_id: string; response: RagResponse; updated_at?: string };
```

```ts
// frontend/src/lib/api/chat.ts
import type { ChatRequest, ChatResponseEnvelope, NormalizedChatResponse } from "../../types/api";
import { apiClient } from "./client";

export function normalizeChatResponse(payload: ChatResponseEnvelope): NormalizedChatResponse {
  const response = payload.response ?? {};
  return {
    conversation_id: payload.conversation_id,
    updated_at: payload.updated_at,
    response: {
      text: String(response.text ?? ""),
      video_url: response.video_url ?? [],
      title: response.title ?? [],
      filename: response.filename ?? [],
      start_timestamp: response.start_timestamp ?? [],
      end_timestamp: response.end_timestamp ?? [],
      confidence: response.confidence ?? [],
      type: (response.type as "rag" | "direct" | "error") ?? "error"
    }
  };
}

export async function postChat(request: ChatRequest) {
  const { data } = await apiClient.post<ChatResponseEnvelope>("/chat", request);
  return normalizeChatResponse(data);
}
```

```ts
// frontend/src/lib/api/client.ts
import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const timeout = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 360000);

export const apiClient = axios.create({
  baseURL,
  timeout,
  headers: { "Content-Type": "application/json" }
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/lib/api/chat.test.ts`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/rag.ts frontend/src/types/api.ts frontend/src/lib/api/client.ts frontend/src/lib/api/chat.ts frontend/src/lib/api/chat.test.ts
git commit -m "feat(frontend): add chat api contract and normalizer"
```

### Task 3: Build citation + timestamp utilities with tests

**Files:**
- Create: `frontend/src/lib/utils/timestamp.ts`, `frontend/src/lib/utils/citation.ts`
- Create: `frontend/src/lib/utils/timestamp.test.ts`, `frontend/src/lib/utils/citation.test.ts`
- Test: `npm --prefix frontend run test -- src/lib/utils/timestamp.test.ts src/lib/utils/citation.test.ts`

- [ ] **Step 1: Write failing utility tests**

```ts
// frontend/src/lib/utils/timestamp.test.ts
import { describe, expect, it } from "vitest";
import { timestampToSeconds } from "./timestamp";

describe("timestampToSeconds", () => {
  it("converts HH:MM:SS", () => {
    expect(timestampToSeconds("00:01:30")).toBe(90);
  });
  it("fallbacks invalid timestamp to 0", () => {
    expect(timestampToSeconds("bad")).toBe(0);
  });
});
```

```ts
// frontend/src/lib/utils/citation.test.ts
import { describe, expect, it } from "vitest";
import { buildCitationItems } from "./citation";

describe("buildCitationItems", () => {
  it("maps citation index to metadata", () => {
    const items = buildCitationItems("Text [0]", {
      video_url: ["https://youtube.com/watch?v=abc"],
      title: ["Video A"],
      filename: ["a.txt"],
      start_timestamp: ["00:00:05"],
      end_timestamp: ["00:00:10"],
      confidence: ["high"]
    });
    expect(items[0].href).toContain("t=5");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm --prefix frontend run test -- src/lib/utils/timestamp.test.ts src/lib/utils/citation.test.ts`  
Expected: FAIL because utils chưa tồn tại.

- [ ] **Step 3: Implement utility functions**

```ts
// frontend/src/lib/utils/timestamp.ts
export function timestampToSeconds(value: string): number {
  const parts = value.split(":").map((part) => Number(part));
  if (parts.length !== 3 || parts.some((part) => Number.isNaN(part) || part < 0)) {
    return 0;
  }
  return parts[0] * 3600 + parts[1] * 60 + parts[2];
}
```

```ts
// frontend/src/lib/utils/citation.ts
import { timestampToSeconds } from "./timestamp";

type CitationMeta = {
  video_url: string[];
  title: string[];
  filename: string[];
  start_timestamp: string[];
  end_timestamp: string[];
  confidence: string[];
};

export type CitationItem = {
  index: number;
  label: string;
  href: string;
  title: string;
  warning?: string;
};

export function buildCitationItems(text: string, meta: CitationMeta): CitationItem[] {
  const matches = [...text.matchAll(/\[(\d+)\]/g)];
  return matches.map((match) => {
    const index = Number(match[1]);
    const video = meta.video_url[index];
    const seconds = timestampToSeconds(meta.start_timestamp[index] ?? "");
    if (!video) {
      return { index, label: `[${index}]`, href: "", title: "", warning: "out_of_range" };
    }
    const sep = video.includes("?") ? "&" : "?";
    return {
      index,
      label: `[${index}]`,
      href: `${video}${sep}t=${seconds}`,
      title: meta.title[index] ?? meta.filename[index] ?? `Source ${index}`
    };
  });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm --prefix frontend run test -- src/lib/utils/timestamp.test.ts src/lib/utils/citation.test.ts`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/utils/timestamp.ts frontend/src/lib/utils/citation.ts frontend/src/lib/utils/timestamp.test.ts frontend/src/lib/utils/citation.test.ts
git commit -m "feat(frontend): add citation and timestamp utils"
```

### Task 4: Implement conversation store and Chatspace UI vertical slice

**Files:**
- Create: `frontend/src/store/conversationStore.ts`
- Create: `frontend/src/components/chat/ChatInput.tsx`
- Create: `frontend/src/components/chat/MessageList.tsx`
- Create: `frontend/src/components/chat/CitationList.tsx`
- Create: `frontend/src/components/sidebar/ConversationSidebar.tsx`
- Create: `frontend/src/pages/ChatPage.tsx`
- Create: `frontend/src/app/App.tsx`, `frontend/src/app/providers.tsx`, `frontend/src/app/router.tsx`
- Test: `npm --prefix frontend run build`

- [ ] **Step 1: Create failing build expectation for missing route/components**

Run: `npm --prefix frontend run build`  
Expected: FAIL because App/router/components chưa hoàn thiện.

- [ ] **Step 2: Implement minimal store and UI components**

```ts
// frontend/src/store/conversationStore.ts
import type { ChatMessage } from "../types/api";

export type ConversationState = {
  conversationId: string;
  messages: ChatMessage[];
  isSending: boolean;
  error: string | null;
};

export const initialConversationState: ConversationState = {
  conversationId: crypto.randomUUID(),
  messages: [],
  isSending: false,
  error: null
};
```

```tsx
// frontend/src/pages/ChatPage.tsx
import { useState } from "react";
import { postChat } from "../lib/api/chat";
import { MessageList } from "../components/chat/MessageList";
import { ChatInput } from "../components/chat/ChatInput";
import { ConversationSidebar } from "../components/sidebar/ConversationSidebar";
import { buildCitationItems } from "../lib/utils/citation";

export function ChatPage() {
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; content: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const conversationId = "chatspace-mvp";

  const handleSend = async (content: string) => {
    const nextMessages = [...messages, { role: "user", content } as const];
    setMessages(nextMessages);
    setError(null);
    try {
      const payload = await postChat({
        conversation_id: conversationId,
        messages: nextMessages,
        user_message: content
      });
      const citations = buildCitationItems(payload.response.text, payload.response);
      const citationText = citations.length > 0 ? `\n\nSources: ${citations.map((item) => item.label).join(" ")}` : "";
      setMessages((prev) => [...prev, { role: "assistant", content: `${payload.response.text}${citationText}` }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl gap-4 p-4">
      <ConversationSidebar />
      <section className="flex flex-1 flex-col gap-3">
        {error ? <div className="rounded-md border border-red-300 bg-red-50 p-2 text-sm">{error}</div> : null}
        <MessageList messages={messages} />
        <ChatInput onSend={handleSend} />
      </section>
    </main>
  );
}
```

```tsx
// frontend/src/components/chat/ChatInput.tsx
import { FormEvent, useState } from "react";

type Props = { onSend: (value: string) => Promise<void> | void };

export function ChatInput({ onSend }: Props) {
  const [value, setValue] = useState("");
  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    await onSend(trimmed);
    setValue("");
  };
  return (
    <form onSubmit={onSubmit} className="flex gap-2">
      <input className="flex-1 rounded-md border px-3 py-2" value={value} onChange={(e) => setValue(e.target.value)} />
      <button className="rounded-md bg-black px-3 py-2 text-white" type="submit">Send</button>
    </form>
  );
}
```

```tsx
// frontend/src/components/chat/MessageList.tsx
type Message = { role: "user" | "assistant"; content: string };
type Props = { messages: Message[] };

export function MessageList({ messages }: Props) {
  return (
    <div className="flex min-h-[400px] flex-1 flex-col gap-2 rounded-xl border p-3">
      {messages.map((message, idx) => (
        <div key={`${message.role}-${idx}`} className={message.role === "user" ? "self-end rounded-lg bg-slate-100 p-2" : "rounded-lg bg-white p-2"}>
          {message.content}
        </div>
      ))}
    </div>
  );
}
```

```tsx
// frontend/src/components/chat/CitationList.tsx
import type { CitationItem } from "../../lib/utils/citation";

type Props = { items: CitationItem[] };

export function CitationList({ items }: Props) {
  if (items.length === 0) return null;
  return (
    <div className="rounded-xl border p-3">
      <h3 className="mb-2 text-sm font-semibold">Nguồn tham khảo</h3>
      {items.map((item) => (
        <a key={item.index} className="block text-sm text-blue-600 underline" href={item.href} target="_blank" rel="noreferrer">
          {item.label} {item.title}
        </a>
      ))}
    </div>
  );
}
```

```tsx
// frontend/src/components/sidebar/ConversationSidebar.tsx
export function ConversationSidebar() {
  return (
    <aside className="w-72 rounded-xl border p-3">
      <h2 className="mb-2 text-sm font-semibold">Conversations</h2>
      <button className="w-full rounded-md border px-2 py-1 text-sm">New conversation</button>
    </aside>
  );
}
```

- [ ] **Step 3: Wire router/providers and render ChatPage**

```tsx
// frontend/src/app/router.tsx
import { createBrowserRouter } from "react-router-dom";
import { ChatPage } from "../pages/ChatPage";

export const router = createBrowserRouter([{ path: "/", element: <ChatPage /> }]);
```

```tsx
// frontend/src/app/providers.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { router } from "./router";

const client = new QueryClient();
export function AppProviders() {
  return (
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
```

```tsx
// frontend/src/app/App.tsx
import { AppProviders } from "./providers";

export function App() {
  return <AppProviders />;
}
```

- [ ] **Step 4: Run build to verify vertical slice passes**

Run: `npm --prefix frontend run build`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store/conversationStore.ts frontend/src/components/chat/ChatInput.tsx frontend/src/components/chat/MessageList.tsx frontend/src/components/chat/CitationList.tsx frontend/src/components/sidebar/ConversationSidebar.tsx frontend/src/pages/ChatPage.tsx frontend/src/app/App.tsx frontend/src/app/providers.tsx frontend/src/app/router.tsx
git commit -m "feat(frontend): implement chatspace mvp vertical slice"
```

### Task 5: Docs + final verification

**Files:**
- Modify: `frontend/README.md`
- Modify: `frontend/docs/build_frontend.md` (Checklist triển khai)
- Test: `npm --prefix frontend run test`, `npm --prefix frontend run build`, `pytest -q tests`

- [ ] **Step 1: Update frontend run guide**

```md
## Chatspace MVP local run

~~~bash
npm --prefix frontend install
npm --prefix frontend run dev
~~~

Yêu cầu backend chạy tại `http://localhost:8000`.
```

- [ ] **Step 2: Update `frontend/docs/build_frontend.md` checklist progress**

Thêm/đánh dấu checklist cho:
- Bootstrap React workspace.
- Chatspace MVP `/chat`.
- Citation timestamp fallback.
- Error + retry cơ bản.

- [ ] **Step 3: Run complete verification**

Run: `npm --prefix frontend run test && npm --prefix frontend run build && pytest -q tests`  
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/README.md frontend/docs/build_frontend.md
git commit -m "docs(frontend): update mvp runbook and progress checklist"
```
