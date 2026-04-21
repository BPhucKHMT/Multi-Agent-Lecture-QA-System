# Split-screen Figma UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chuyển brief đã chốt thành bộ tài liệu + ui-spec có thể dùng ngay để dựng Figma high-fidelity cho layout split-screen 50/50 với hover 60/40.

**Architecture:** Dùng `docs/frontend_ui.md` làm nguồn UI/handoff chính, `docs/detailed_frontent.md` làm nguồn kỹ thuật tích hợp, và thêm một file ui-spec riêng cho pipeline `frontend/ui2figma`. Mọi thay đổi giữ nguyên phạm vi desktop và flow Summary Hub <-> Chatspace đã chốt.

**Tech Stack:** Markdown docs, Figma handoff conventions, Python CLI `frontend/ui2figma/run_text_to_ui.py`.

---

## File Structure (điểm chạm bắt buộc)

- **Modify:** `docs/frontend_ui.md`
  - Cập nhật layout behavior 50/50 -> 60/40 theo hover và screen inventory mới (login/workspace hover/context-injection).
- **Modify:** `docs/detailed_frontent.md`
  - Bổ sung mục kỹ thuật mapping với UI behavior mới (split hover và context injection trigger).
- **Create:** `frontend/ui2figma/docs/specs/2026-04-19-split-screen-workspace-ui-spec.md`
  - File spec dùng trực tiếp cho pipeline text-to-ui.
- **Create:** `docs/superpowers/specs/2026-04-19-split-screen-figma-ui-design.md`
  - Đã có sẵn; dùng làm source-of-truth cho implementation steps bên dưới.

---

### Task 1: Cập nhật UI handoff doc theo quyết định cuối

**Files:**
- Modify: `docs/frontend_ui.md`
- Reference: `docs/superpowers/specs/2026-04-19-split-screen-figma-ui-design.md`

- [ ] **Step 1: Xác minh hiện trạng chưa có đầy đủ split-hover behavior mới**

Run:
```bash
rg -n "60/40|L01_Login_Default|W02_Workspace_HoverChat_60_40|X01_ContextInjected_FromSummaryToChat" docs/frontend_ui.md
```

Expected: chưa có đủ toàn bộ các key trên.

- [ ] **Step 2: Cập nhật mục Layout + Screen inventory**

Chèn nội dung sau vào `docs/frontend_ui.md` (đúng section layout/screen inventory):

```md
- Split mặc định 50/50 trên desktop.
- Hover pane trái hoặc phải thì pane đó nở 60/40 trong ~180ms.
- Idle >= 1.2s trở lại 50/50.

Screen bổ sung:
- L01_Login_Default
- W01_Workspace_50_50_Default
- W02_Workspace_HoverChat_60_40
- W03_Workspace_HoverSummary_40_60
- X01_ContextInjected_FromSummaryToChat
```

- [ ] **Step 3: Xác minh doc đã phản ánh đúng behavior**

Run:
```bash
rg -n "50/50|60/40|180ms|1.2s|L01_Login_Default|X01_ContextInjected_FromSummaryToChat" docs/frontend_ui.md
```

Expected: có đầy đủ match.

- [ ] **Step 4: Commit Task 1**

```bash
git add docs/frontend_ui.md
git commit -m "docs: align frontend UI handoff with split-screen hover behavior"
```

---

### Task 2: Tạo ui-spec cho pipeline text-to-ui

**Files:**
- Create: `frontend/ui2figma/docs/specs/2026-04-19-split-screen-workspace-ui-spec.md`
- Reference: `docs/superpowers/specs/2026-04-19-split-screen-figma-ui-design.md`

- [ ] **Step 1: Tạo file ui-spec với cấu trúc screens/components/states/tokens**

Tạo file `frontend/ui2figma/docs/specs/2026-04-19-split-screen-workspace-ui-spec.md` với nội dung:

```md
# Split-screen Workspace UI Spec

## Meta
- project: PUQ Frontend
- version: 1.0
- platform: desktop
- fidelity: high-fidelity

## Screens
1. L01_Login_Default
2. W01_Workspace_50_50_Default
3. W02_Workspace_HoverChat_60_40
4. W03_Workspace_HoverSummary_40_60
5. S01_Summary_Default
6. S02_Summary_Loading
7. S03_Summary_WithResult
8. S04_Summary_Error
9. C01_Chat_Default
10. C02_Chat_Replying
11. C03_Chat_Error
12. X01_ContextInjected_FromSummaryToChat

## Components
- PaneShell(default|hovered|error)
- ChatInputBar(idle|typing|sending|disabled)
- MessageBubble(user|assistant|assistant_error)
- SummaryPanel(empty|loading|ready|error)
- VideoListItem(default|hover|selected)
- ActionButton(primary|secondary|ghost|disabled)

## States
- default
- with_result
- replying
- error

## Interaction
- split_default: 50/50
- split_hover: 60/40
- split_transition_ms: 180
- split_idle_reset_ms: 1200
- discuss_action: inject_context_to_chat

## Tokens
- primary: #4F46E5
- accent: #06B6D4
- app_bg: #F8FAFC
- card_bg: #FFFFFF
- text_primary: #0F172A
- text_secondary: #475569
- success: #22C55E
- error: #EF4444
```

- [ ] **Step 2: Chạy pipeline ở chế độ review gate**

Run:
```bash
python frontend\ui2figma\run_text_to_ui.py --spec frontend\ui2figma\docs\specs\2026-04-19-split-screen-workspace-ui-spec.md --review revise
```

Expected: pipeline parse spec và dừng ở review gate (không đi codegen).

- [ ] **Step 3: Commit Task 2**

```bash
git add frontend/ui2figma/docs/specs/2026-04-19-split-screen-workspace-ui-spec.md
git commit -m "docs: add ui2figma spec for split-screen workspace"
```

---

### Task 3: Đồng bộ technical doc và hoàn tất kiểm tra chéo

**Files:**
- Modify: `docs/detailed_frontent.md`
- Test/Verify: `docs/frontend_ui.md`, `frontend/ui2figma/docs/specs/2026-04-19-split-screen-workspace-ui-spec.md`

- [ ] **Step 1: Bổ sung mục technical mapping trong implementation doc**

Chèn vào `docs/detailed_frontent.md` một section:

```md
## UI Behavior Mapping (Split-screen)
- Desktop workspace mặc định 50/50.
- Hover pane: 60/40, transition ~180ms, idle reset ~1200ms.
- Action "Thảo luận" từ Summary Hub inject context video sang Chatspace.
- FE event cần phát: `summary.discuss.clicked` với payload `{ video_id, video_title }`.
```

- [ ] **Step 2: Chạy kiểm tra nhất quán thuật ngữ giữa 3 tài liệu**

Run:
```bash
rg -n "50/50|60/40|Thảo luận|inject context|ContextInjected" docs/frontend_ui.md docs/detailed_frontent.md frontend/ui2figma/docs/specs/2026-04-19-split-screen-workspace-ui-spec.md
```

Expected: các keyword xuất hiện nhất quán ở cả 3 file.

- [ ] **Step 3: Commit Task 3**

```bash
git add docs/detailed_frontent.md docs/frontend_ui.md frontend/ui2figma/docs/specs/2026-04-19-split-screen-workspace-ui-spec.md
git commit -m "docs: synchronize UI and implementation docs for split-screen figma flow"
```

---

### Task 4: Final verification snapshot

**Files:**
- Verify only:
  - `docs/frontend_ui.md`
  - `docs/detailed_frontent.md`
  - `frontend/ui2figma/docs/specs/2026-04-19-split-screen-workspace-ui-spec.md`

- [ ] **Step 1: Kiểm tra không còn placeholder**

Run:
```bash
rg -n "TBD|TODO|implement later|fill in details" docs/frontend_ui.md docs/detailed_frontent.md frontend/ui2figma/docs/specs/2026-04-19-split-screen-workspace-ui-spec.md
```

Expected: không có kết quả.

- [ ] **Step 2: Chụp trạng thái file thay đổi cuối**

Run:
```bash
git --no-pager status --short
```

Expected: chỉ chứa các file docs/spec liên quan task này.

- [ ] **Step 3: Commit tổng kết (nếu còn thay đổi chưa commit)**

```bash
git add docs/frontend_ui.md docs/detailed_frontent.md frontend/ui2figma/docs/specs/2026-04-19-split-screen-workspace-ui-spec.md
git commit -m "docs: finalize split-screen figma handoff package"
```
