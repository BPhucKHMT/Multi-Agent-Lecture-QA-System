# Split-screen Figma UI Design (Summary Hub + Chatspace)

**Mục tiêu:** Thiết kế high-fidelity desktop UI cho trải nghiệm sau login, gồm 2 không gian đồng thời: Chatspace (trái) và Summary Hub (phải), hỗ trợ trạng thái mặc định/có kết quả/đang trả lời/lỗi và flow thảo luận từ summary sang chat.

**Phạm vi:** Thiết kế UI/UX và prototype flow trong Figma. Không bao gồm triển khai API/backend.

---

## 1) Yêu cầu đã chốt

1. Sau login vào thẳng màn split-screen.
2. Mặc định layout 50/50.
3. User đưa chuột vào pane nào thì pane đó nở lên 60/40.
4. High-fidelity desktop, tông màu sáng tươi.
5. Có các trạng thái: mặc định, có kết quả, đang trả lời, lỗi.
6. Flow:
   - User có thể thao tác Summary Hub (chọn video, tóm tắt, bấm thảo luận sang chat).
   - Hoặc user thao tác chat bình thường ngay từ đầu.

---

## 2) Information architecture

- **Pane trái: Chatspace**
  - Conversation list
  - Message timeline
  - Input bar
- **Pane phải: Summary Hub**
  - Summary content area
  - Video list panel (lấy từ DB) đặt bên phải trong pane Summary
  - Action buttons: `Tóm tắt`, `Thảo luận`

---

## 3) Layout behavior

## 3.1 Desktop frame

- Base frame: `1440 x 1024`
- Split mặc định:
  - Left pane: 720px
  - Right pane: 720px

## 3.2 Hover expansion

- Hover left pane -> `864 / 576` (60/40)
- Hover right pane -> `576 / 864` (40/60)
- Transition:
  - Duration: ~180ms
  - Easing: ease-out
- Idle >= 1.2s, tự trở về 50/50.

---

## 4) Screen inventory (Figma frames)

1. `L01_Login_Default`
2. `W01_Workspace_50_50_Default`
3. `W02_Workspace_HoverChat_60_40`
4. `W03_Workspace_HoverSummary_40_60`
5. `S01_Summary_Default`
6. `S02_Summary_Loading`
7. `S03_Summary_WithResult`
8. `S04_Summary_Error`
9. `C01_Chat_Default`
10. `C02_Chat_Replying`
11. `C03_Chat_Error`
12. `X01_ContextInjected_FromSummaryToChat`

---

## 5) Component spec

## 5.1 Core components

- `PaneShell`
  - variants: `default`, `hovered`, `error`
- `ChatInputBar`
  - variants: `idle`, `typing`, `sending`, `disabled`
- `MessageBubble`
  - variants: `user`, `assistant`, `assistant_error`
- `SummaryPanel`
  - variants: `empty`, `loading`, `ready`, `error`
- `VideoListItem`
  - variants: `default`, `hover`, `selected`
- `ActionButton`
  - variants: `primary`, `secondary`, `ghost`, `disabled`

## 5.2 Interaction rules

- Bấm `Tóm tắt`:
  - Summary vào loading -> ready/error.
- Bấm `Thảo luận`:
  - Tạo context token gắn vào chat input area.
  - Focus vào input để user hỏi tiếp.

---

## 6) Visual style (high-fidelity, bright)

## 6.1 Color palette

- Primary: `#4F46E5`
- Accent: `#06B6D4`
- Background app: `#F8FAFC`
- Card background: `#FFFFFF`
- Text primary: `#0F172A`
- Text secondary: `#475569`
- Success: `#22C55E`
- Error: `#EF4444`

## 6.2 Typography

- Font: Inter
- Scale:
  - H1 28/36
  - H2 22/30
  - Body 14/22
  - Caption 12/18

## 6.3 Shape & elevation

- Radius:
  - Control: 10
  - Card: 14
  - Pane: 16
- Shadow:
  - `sm`: subtle borders
  - `md`: pane/card emphasis

---

## 7) States & error UX

1. **Default**
   - Cả hai pane ở trạng thái sẵn sàng.
2. **Có kết quả**
   - Summary có nội dung; chat có thể nhận context.
3. **Đang trả lời**
   - Chat hiển thị typing/streaming indicator.
4. **Lỗi**
   - Pane nào lỗi thì chỉ pane đó hiển thị lỗi + retry.
   - Pane còn lại vẫn hoạt động.

---

## 8) Prototype flow trong Figma

1. `Login -> Workspace_50_50_Default`
2. Hover test:
   - Default -> HoverChat
   - Default -> HoverSummary
   - Hover -> Default
3. Summary flow:
   - Summary_Default -> Loading -> WithResult
   - WithResult -> Thảo luận -> ContextInjected
4. Chat flow:
   - Chat_Default -> Replying -> (Success or Error)

---

## 9) Handoff checklist cho team design/dev

- Tạo page:
  - `00_Foundations`
  - `01_Components`
  - `02_Screens`
  - `03_Prototype`
- Variants naming: `state=`, `pane=`, `interaction=`.
- Auto Layout cho tất cả panel lớn.
- Annotation bắt buộc:
  - hover expansion rule (50/50 <-> 60/40)
  - state transitions
  - context injection trigger (`Thảo luận`)

---

## 10) Acceptance criteria

1. Figma có đủ 12 frame bắt buộc.
2. Hover split behavior 50/50 <-> 60/40 thể hiện rõ trong prototype.
3. Có đủ 4 trạng thái chính: mặc định/có kết quả/đang trả lời/lỗi.
4. Flow từ Summary Hub sang Chatspace qua nút `Thảo luận` được mô phỏng đầy đủ.
