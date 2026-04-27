# Stitch Prompt Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cập nhật `docs/stitch_frontend_prompts.md` để prompt theo trang vẫn dùng chung UI và context, tránh sinh màn hình rời rạc khi chạy Stitch.

**Architecture:** Giữ mô hình prompt theo 6 màn hình (P1..P6) nhưng thêm 3 lớp ràng buộc ở đầu tài liệu: Global Guardrails, Reusable UI Catalog, Context Injection Rules. Mỗi prompt trang chỉ mô tả phần thay đổi (delta) và luôn kế thừa context trước đó.

**Tech Stack:** Markdown docs, Stitch text prompts, ripgrep (`rg`) để kiểm tra nhất quán nội dung.

---

## File Structure (điểm chạm bắt buộc)

- **Modify:** `docs/stitch_frontend_prompts.md`
  - Thêm khối guardrails dùng chung.
  - Thêm catalog component tái sử dụng.
  - Thêm luật context xuyên màn.
  - Viết lại prompt P1..P6 theo dạng delta.
- **Reference:** `docs/superpowers/specs/2026-04-19-stitch-prompt-guardrails-design.md`
  - Là nguồn thiết kế đã được duyệt để đối chiếu phạm vi.

---

### Task 1: Khóa baseline và xác minh điểm rời rạc hiện tại

**Files:**
- Modify: `docs/stitch_frontend_prompts.md`
- Reference: `docs/superpowers/specs/2026-04-19-stitch-prompt-guardrails-design.md`

- [ ] **Step 1: Xác minh file hiện tại chưa có guardrails/catalog/context rules**

Run:
```bash
rg -n "Global Guardrails|Reusable UI Catalog|Context Injection Rules|preserve all previous context" docs/stitch_frontend_prompts.md
```

Expected: không có kết quả.

- [ ] **Step 2: Chụp nhanh nội dung 6 prompt hiện tại để đối chiếu sau sửa**

Run:
```bash
rg -n "^## P[1-6]_" docs/stitch_frontend_prompts.md
```

Expected: thấy đủ 6 heading `P1..P6`.

- [ ] **Step 3: Commit checkpoint baseline (nếu có thay đổi cục bộ trước đó)**

```bash
git --no-pager status --short
```

Expected: không có thay đổi mới từ Task 1.

---

### Task 2: Thêm Global Guardrails và Reusable UI Catalog

**Files:**
- Modify: `docs/stitch_frontend_prompts.md`

- [ ] **Step 1: Chèn khối Global Guardrails ngay sau phần “Cách dùng nhanh”**

Chèn đoạn sau:

```md
## Global Guardrails (áp dụng cho mọi prompt)
- Same product, same design system, same component library across all pages.
- Desktop-only 1440px, high-fidelity, bright Blue + Cyan + Mint.
- Keep typography, spacing, border radius, elevation consistent across all pages.
- Do not redesign from scratch between prompts; only apply requested delta.
```

- [ ] **Step 2: Chèn khối Reusable UI Catalog sau Global Guardrails**

Chèn đoạn sau:

```md
## Reusable UI Catalog (không đổi tên giữa các trang)
- `TopBar`: user info, global actions, search nhẹ.
- `ChatPanel`: sidebar conversations + message area + input.
- `SummaryPanel`: summary content area với trạng thái.
- `VideoRail`: danh sách video bên phải (thumbnail/title/duration/selected).
- `ContextPill`: hiển thị ngữ cảnh video/timestamp trong Chatspace.

### Shared states
- `default`
- `progress` (loading hoặc streaming)
- `result`
- `error` (kèm retry)
```

- [ ] **Step 3: Kiểm tra 2 section mới đã hiện diện**

Run:
```bash
rg -n "Global Guardrails|Reusable UI Catalog|Shared states|ChatPanel|SummaryPanel|ContextPill" docs/stitch_frontend_prompts.md
```

Expected: có match cho toàn bộ cụm trên.

- [ ] **Step 4: Commit Task 2**

```bash
git add docs/stitch_frontend_prompts.md
git commit -m "docs: add stitch global guardrails and reusable UI catalog"
```

---

### Task 3: Thêm Context Injection Rules xuyên màn

**Files:**
- Modify: `docs/stitch_frontend_prompts.md`

- [ ] **Step 1: Chèn section Context Injection Rules trước P1**

Chèn đoạn sau:

```md
## Context Injection Rules (xuyên toàn bộ flow)
- Maintain shared context keys: `current_user`, `active_workspace`, `selected_video`, `summary_status`, `chat_status`.
- From Summary Hub to Chatspace, preserve: `selected_video`, `summary_highlights`, `timestamp_refs`.
- Every page prompt must include: "Preserve all previous context unless explicitly changed."
- If a value is not mentioned in a page delta, keep the previous value unchanged.
```

- [ ] **Step 2: Kiểm tra section context đã đủ key và rule**

Run:
```bash
rg -n "current_user|active_workspace|selected_video|summary_status|chat_status|summary_highlights|timestamp_refs|Preserve all previous context" docs/stitch_frontend_prompts.md
```

Expected: có đủ các key/rule nêu trên.

- [ ] **Step 3: Commit Task 3**

```bash
git add docs/stitch_frontend_prompts.md
git commit -m "docs: add stitch context injection rules across pages"
```

---

### Task 4: Viết lại P1..P6 thành Per-page Delta Prompts

**Files:**
- Modify: `docs/stitch_frontend_prompts.md`

- [ ] **Step 1: Cập nhật mỗi prompt P1..P6 để mở đầu bằng câu neo context**

Với từng prompt `P1..P6`, thêm câu mở đầu:

```md
Preserve all previous context unless explicitly changed.
```

- [ ] **Step 2: Chuẩn hóa prompt theo “delta only” (không mô tả lại toàn bộ app)**

Áp dụng quy tắc:

```md
- P1 chỉ mô tả login + gateway chọn workspace.
- P2 chỉ mô tả baseline workspace 50/50.
- P3 chỉ mô tả delta focus Chatspace 60/40 + dim Summary.
- P4 chỉ mô tả delta focus Summary 40/60 + video rail emphasis.
- P5 chỉ mô tả delta có kết quả summary + CTA thảo luận.
- P6 chỉ mô tả delta context đã inject sang chat + hỏi đáp theo video.
```

- [ ] **Step 3: Kiểm tra đủ 6 prompt đều có câu neo context**

Run:
```bash
rg -n "Preserve all previous context unless explicitly changed" docs/stitch_frontend_prompts.md
```

Expected: có đúng 6 kết quả (mỗi prompt 1 dòng).

- [ ] **Step 4: Commit Task 4**

```bash
git add docs/stitch_frontend_prompts.md
git commit -m "docs: rewrite stitch page prompts as context-preserving deltas"
```

---

### Task 5: Consistency pass cuối cho chống rời rạc

**Files:**
- Modify: `docs/stitch_frontend_prompts.md`

- [ ] **Step 1: Kiểm tra tên component không bị drift**

Run:
```bash
rg -n "TopBar|ChatPanel|SummaryPanel|VideoRail|ContextPill" docs/stitch_frontend_prompts.md
```

Expected: các tên xuất hiện nhất quán, không có biến thể tên khác.

- [ ] **Step 2: Kiểm tra trạng thái bắt buộc đã được nhắc đủ**

Run:
```bash
rg -n "default|progress|result|error|retry|streaming|loading" docs/stitch_frontend_prompts.md
```

Expected: có đủ trạng thái chính và tín hiệu retry/progress.

- [ ] **Step 3: Kiểm tra ràng buộc layout ratio vẫn đúng**

Run:
```bash
rg -n "50/50|60/40|40/60|dim" docs/stitch_frontend_prompts.md
```

Expected: có đầy đủ ratio cho baseline và 2 trạng thái focus.

- [ ] **Step 4: Commit Task 5**

```bash
git add docs/stitch_frontend_prompts.md
git commit -m "docs: finalize stitch anti-fragmentation consistency pass"
```
