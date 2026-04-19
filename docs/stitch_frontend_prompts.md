# Stitch prompts theo từng trang (Desktop, High-fidelity)

## Cách dùng nhanh
- Dán **từng prompt riêng lẻ** vào Stitch (không dán gộp).
- Giữ thống nhất style: **bright Blue + Cyan + Mint**, hiện đại, sạch, nhiều khoảng trắng, bo góc mềm, đổ bóng nhẹ.
- Mỗi màn hình là **desktop first** (1440px), không sinh mobile ở bước này.

---

## Global Guardrails (áp dụng cho mọi prompt)
- Same product, same design system, same component library across all pages.
- Desktop-only 1440px, high-fidelity, bright Blue + Cyan + Mint.
- Keep typography, spacing, border radius, elevation consistent across all pages.
- Do not redesign from scratch between prompts; only apply requested delta.

---

## Reusable UI Catalog (không đổi tên giữa các trang)
- `TopBar`: user info, global actions, search nhẹ (full width, cố định ở trên).
- `SidebarNav` (trái): 15% width cố định, chứa 2 option: "Chatspace Agent" và "Summary Hub", có active state rõ.
- `ChatPanel`: sidebar hội thoại (trong 85% main) + message area + input.
- `SummaryPanel`: summary content area với trạng thái (trong 60% main khi ở Summary Hub).
- `VideoRail`: sidebar phải 25% width khi ở Summary Hub mode (danh sách video: thumbnail/title/duration/selected).
- `ContextPill`: hiển thị ngữ cảnh video/timestamp trong Chatspace khi user từ Summary Hub.

### Shared states
- `default`
- `progress` (loading hoặc streaming)
- `result`
- `error` (kèm retry)

### Layout modes
- **Chatspace Agent**: TopBar + SidebarNav (15%) + ChatPanel (85%)
- **Summary Hub**: TopBar + SidebarNav (15%) + SummaryPanel (60%) + VideoRail (25%)

---

## Context Injection Rules (xuyên toàn bộ flow)
- Maintain shared context keys: `current_user`, `active_workspace`, `selected_video`, `summary_status`, `chat_status`.
- From Summary Hub to Chatspace, preserve: `selected_video`, `summary_highlights`, `timestamp_refs`.
- Every page prompt must include: "Preserve all previous context unless explicitly changed."
- If a value is not mentioned in a page delta, keep the previous value unchanged.

---

## Per-page Delta Prompts (P1..P6)

### P1_Login_ChoiceGateway

Preserve all previous context unless explicitly changed.

Thiết kế màn hình đăng nhập high-fidelity desktop cho sản phẩm học tập AI: nền sáng tươi (Blue/Cyan/Mint), card login ở giữa gồm logo, tiêu đề, email, password, nút Sign in chính và link phụ; sau khi đăng nhập thành công hiển thị ngay lựa chọn vào workspace với 2 lựa chọn lớn cạnh nhau: "Chatspace Agent" bên trái và "Summary Hub" bên phải, nhấn vào lựa chọn nào thì điều hướng vào workspace tương ứng và set `active_workspace` context.

---

### P2_Chatspace_Agent_Mode

Preserve all previous context unless explicitly changed.

Thiết kế màn hình workspace sau chọn "Chatspace Agent" từ login gateway: layout 3 vùng: TopBar (toàn chiều rộng, user info + settings), Sidebar trái (15% width, cố định): hiển thị 2 option "Chatspace Agent" (active/highlighted) và "Summary Hub" (inactive), Main content (85% width): ChatPanel (sidebar hội thoại + vùng chat mặc định). Style high-fidelity desktop sáng, hiện đại, dễ đọc, transition mượt khi chuyển qua Summary Hub.

---

### P3_Chatspace_Agent_States

Preserve all previous context unless explicitly changed.

Delta: Trong Chatspace Agent mode, ChatPanel hiển thị các trạng thái rõ ràng gồm default (welcome message), progress (streaming indicator khi đang reply), result (message + citation), và error (thông báo lỗi + nút retry). Sidebar trái vẫn cố định 15%, Chatspace Agent vẫn active state.

---

### P4_Summary_Hub_Mode

Preserve all previous context unless explicitly changed.

Delta: User nhấn "Summary Hub" từ sidebar trái → switch sang Summary Hub mode. Layout: TopBar (cố định), Sidebar trái (15%): "Summary Hub" active, "Chatspace Agent" inactive, Main content (60%): SummaryPanel (nội dung tóm tắt + key points), Sidebar phải (25%): VideoRail (danh sách video từ database: thumbnail/title/duration/selected state). SummaryPanel hỗ trợ trạng thái default, progress (loading), result, error kèm retry.

---

### P5_Summary_Hub_Video_Selected

Preserve all previous context unless explicitly changed.

Delta: User đã chọn một video từ VideoRail (set `selected_video` context, video item trong rail có selected visual state). Hiển thị tiêu đề video, key points, mốc thời gian quan trọng, trạng thái confidence trong SummaryPanel, và CTA nổi bật "Thảo luận trong Chatspace". Layout vẫn giữ: 15% sidebar trái + 60% SummaryPanel + 25% VideoRail.

---

### P6_Chatspace_WithContext_From_Summary

Preserve all previous context unless explicitly changed.

Delta: User bấm "Thảo luận trong Chatspace" từ P5 → switch sang Chatspace Agent mode nhưng vẫn giữ context. Ở đầu khung nhập chat có ContextPill hiển thị (video title + timestamp range từ `selected_video`). Khu chat hiển thị opening message kèm context của video vừa tóm tắt, user có thể gửi câu hỏi liên quan, assistant trả lời có citation rõ. Thể hiện đủ 4 trạng thái: default, progress (streaming), result, error. Sidebar trái vẫn 15%, ChatPanel 85%.
