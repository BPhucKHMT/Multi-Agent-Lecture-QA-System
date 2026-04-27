# Frontend UI Design Spec (Figma-first)

## 1) Mục tiêu tài liệu

Tài liệu này mô tả **thuần thiết kế giao diện** cho frontend mới, dùng để dựng Figma và thống nhất UX/UI giữa team design - product - frontend.

**Không bao gồm** chi tiết kỹ thuật triển khai (API, ENV, install, build). Các phần đó nằm ở `docs/detailed_frontent.md`.

---

## 2) Product context (góc nhìn UI)

- Sản phẩm có 2 không gian chính:
  1. **Summary Hub**: không gian đọc tóm tắt học liệu.
  2. **Chatspace**: không gian hỏi đáp đa đặc vụ.
- User chính: sinh viên cần đọc nhanh, sau đó đào sâu qua chat và citation video timestamp.
- Trải nghiệm mong muốn:
  - Từ Summary Hub chuyển mượt sang Chatspace.
  - Nhìn citation rõ, bấm được đúng timestamp.
  - Giao diện rõ trạng thái (loading / empty / error / retry).

---

## 3) Information architecture

## 3.1 Global navigation

- Top-level routes:
  - `Summary Hub`
  - `Chatspace`
  - `Settings` (nhẹ, ưu tiên session/device context)
- Điều hướng chính:
  - Summary Hub -> nút “Thảo luận về video này” -> Chatspace (kèm ngữ cảnh video).

## 3.2 Page hierarchy

1. **Summary Hub Page**
   - Header + search/filter.
   - Danh sách video card.
   - Summary panel.
2. **Chatspace Page**
   - Sidebar conversation.
   - Main message area.
   - Chat input và status.

---

## 4) Screen inventory cho Figma

Tạo tối thiểu các frame sau:

1. `S01_SummaryHub_Default`
2. `S02_SummaryHub_Loading`
3. `S03_SummaryHub_Empty`
4. `S04_SummaryHub_Error`
5. `S05_SummaryHub_WithSummary`
6. `C01_Chatspace_Default`
7. `C02_Chatspace_Streaming`
8. `C03_Chatspace_ErrorRetry`
9. `C04_Chatspace_CitationExpanded`
10. `C05_Chatspace_EmptyConversation`

---

## 5) Layout blueprint

## 5.1 Summary Hub

- Desktop (>= 1280):
  - Cột trái: video list / filters.
  - Cột phải: summary detail.
- Tablet (768-1279):
  - 2 cột co giãn, ưu tiên summary.
- Mobile (< 768):
  - Chuyển tab “Danh sách / Tóm tắt”.

## 5.2 Chatspace

- Desktop:
  - Sidebar trái cố định (~280px).
  - Main chat phải co giãn.
- Tablet:
  - Sidebar collapse icon.
- Mobile:
  - Sidebar dạng drawer.
  - Input sticky bottom.

---

## 6) Component inventory (Figma components)

## 6.1 Summary Hub components

- `VideoCard`
  - Variants: default / hovered / selected / disabled.
- `SummaryPanel`
  - Variants: empty / loading / ready / error.
- `ActionButtonDiscuss`
  - Primary CTA sang Chatspace.

## 6.2 Chatspace components

- `ConversationListItem`
  - Variants: active / idle / unread / hovered.
- `MessageBubble`
  - Variants: user / assistant / system.
- `CitationChip`
  - Variants: default / hovered / visited / broken.
- `ChatInputBar`
  - Variants: idle / typing / sending / disabled.
- `InlineErrorNotice`
  - Variants: retryable / non-retryable.

---

## 7) Design tokens

## 7.1 Color roles

- `bg/base`, `bg/subtle`, `bg/card`
- `text/primary`, `text/secondary`, `text/muted`
- `brand/primary`, `brand/primary-hover`
- `state/success`, `state/warn`, `state/error`, `state/info`
- `citation/link`, `citation/link-hover`

## 7.2 Typography

- Heading: 32 / 24 / 20 / 16
- Body: 16 / 14
- Caption: 12
- Code-inline/citation label: mono 12-13

## 7.3 Spacing & radius

- Spacing scale: 4, 8, 12, 16, 24, 32
- Radius scale: 8 (control), 12 (card), 16 (panel)
- Shadow levels: sm / md / lg

---

## 8) Interaction states bắt buộc

- **Loading**: skeleton rõ vùng dữ liệu.
- **Empty**: message + CTA cụ thể.
- **Error**: thông báo + nút retry.
- **Streaming**: con trỏ đang gõ cho Chatspace.
- **Disabled**: nút/input không khả dụng phải giảm tương phản hợp lý.

---

## 9) Responsive specs

- Breakpoints:
  - `sm`: 640
  - `md`: 768
  - `lg`: 1024
  - `xl`: 1280
- Quy tắc:
  - Không cắt mất citation.
  - Không để input bị bàn phím che (mobile).
  - Sidebar trên mobile luôn đóng/mở bằng thao tác rõ ràng.

---

## 10) Accessibility checklist (UI)

- Contrast text tối thiểu WCAG AA.
- Focus ring rõ cho control tương tác.
- Kích thước touch target >= 44px.
- Có trạng thái keyboard focus cho:
  - video card
  - conversation item
  - citation link
  - input submit
- Icon-only button phải có label trong design annotation.

---

## 11) Figma handoff checklist

- Tên frame theo chuẩn: `Sxx_...`, `Cxx_...`.
- Component set đặt trong `UI Kit / Components`.
- Variants đặt tên thống nhất: `state=`, `size=`, `type=`.
- Dùng Auto Layout cho toàn bộ panel chính.
- Tạo prototype flow:
  - Summary Hub -> Discuss -> Chatspace
  - Chat retry
  - Citation click
- Gắn annotation cho:
  - hành vi loading/error
  - responsive switch
  - states ưu tiên cho dev.

---

## 12) Definition of done cho UI spec

- Có đủ toàn bộ frame bắt buộc.
- Có design tokens + component variants rõ ràng.
- Có prototype cho luồng chính Summary Hub <-> Chatspace.
- Designer và frontend có thể implement mà không cần đoán thêm behavior UI.
