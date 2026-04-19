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

Thiết kế màn hình đăng nhập high-fidelity desktop cho sản phẩm học tập AI: nền sáng tươi (Blue/Cyan/Mint), card login ở giữa gồm logo, tiêu đề, email, password, nút Sign in chính và link phụ; sau khi đăng nhập thành công hiển thị ngay lựa chọn vào workspace với 2 lựa chọn lớn cạnh nhau: Chatspace Agent (TopBar bên trái) và Summary Hub (TopBar bên phải), nhấn vào lựa chọn nào thì điều hướng vào workspace tương ứng và set `active_workspace` context.

---

### P2_Workspace_Default_50_50

Preserve all previous context unless explicitly changed.

Thiết kế màn hình workspace sau login với layout chia đôi 50/50: bên trái là ChatPanel (sidebar hội thoại + vùng chat mặc định), bên phải là SummaryPanel (khu tóm tắt mặc định + danh sách video), cả hai cùng nhìn thấy rõ, có TopBar chung với tên user, search nhẹ và nút settings; style high-fidelity desktop sáng, hiện đại, dễ đọc.

---

### P3_Workspace_Chatspace_Focus_60_40

Preserve all previous context unless explicitly changed.

Delta: Trạng thái hover/focus vào Chatspace - panel trái (ChatPanel) mở rộng thành 60%, panel phải (SummaryPanel) còn 40% và được dim nhẹ (opacity ~70%). ChatPanel có các trạng thái rõ ràng gồm default, progress (streaming indicator), result, và error (kèm retry); giữ visual hierarchy mạnh cho luồng chat nhưng vẫn thấy SummaryPanel để chuyển lại nhanh.

---

### P4_Workspace_SummaryHub_Focus_40_60

Preserve all previous context unless explicitly changed.

Delta: Trạng thái hover/focus vào Summary Hub - panel phải (SummaryPanel) mở rộng thành 60%, panel trái (ChatPanel) còn 40% và dim nhẹ (opacity ~70%); trong SummaryPanel có vùng nội dung tóm tắt trung tâm và VideoRail bên phải lấy từ database (thumbnail, title, duration, selected state), hỗ trợ các trạng thái default, progress (loading), result, error kèm retry.

---

### P5_SummaryHub_Result_To_Discuss

Preserve all previous context unless explicitly changed.

Delta: User đã chọn một video từ VideoRail (set `selected_video` context). Hiển thị tiêu đề video, key points, mốc thời gian quan trọng, trạng thái confidence trong SummaryPanel, và CTA nổi bật "Thảo luận trong Chatspace". Khi bấm CTA thì tạo transition rõ ràng sang Chatspace, mang theo context `selected_video`, `summary_highlights`, `timestamp_refs`.

---

### P6_Chatspace_Ask_WithSummaryContext

Preserve all previous context unless explicitly changed.

Delta: Chatspace đã nhận context từ P5 (`selected_video`, `summary_highlights`, `timestamp_refs`). Ở đầu khung nhập có ContextPill hiển thị (video title + timestamp range). Khu chat hiển thị câu hỏi user liên quan nội dung vừa tóm tắt, assistant trả lời có citation rõ; thể hiện đủ 4 trạng thái: default, progress (streaming), result, error; vẫn giữ panel SummaryPanel nhỏ ở phải (40%) để người dùng quay lại hoặc chọn video khác.
