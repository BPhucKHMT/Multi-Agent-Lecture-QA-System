# Stitch Prompt Guardrails Design

## 1. Bài toán

File `docs/stitch_frontend_prompts.md` hiện đã có 6 prompt theo màn hình, nhưng thiếu lớp ràng buộc dùng chung nên khi chạy Stitch dễ sinh UI rời rạc giữa các page.

Mục tiêu lần này là giữ nguyên cách làm “prompt theo từng trang” nhưng bổ sung cấu trúc để:
- tái sử dụng UI nhất quán;
- giữ context xuyên trang;
- giảm drift về layout, component, token và trạng thái.

## 2. Phạm vi

- **Trong phạm vi:** cập nhật duy nhất `docs/stitch_frontend_prompts.md`.
- **Ngoài phạm vi:** không đổi `docs/frontend_ui.md`, không thêm toolchain mới, không đổi flow nghiệp vụ đã chốt (P1 -> P6).

## 3. Cấu trúc tài liệu đề xuất (Guardrail-first)

`docs/stitch_frontend_prompts.md` sẽ được tổ chức lại thành 4 khối:

1. **Global Guardrails**  
   Quy định “same product / same design system / same tokens / same components”, desktop 1440, high-fidelity, palette Blue-Cyan-Mint.

2. **Reusable UI Catalog**  
   Danh mục thành phần bắt buộc tái sử dụng xuyên màn: `TopBar`, `ChatPanel`, `SummaryPanel`, `VideoRail`, `ContextPill`, cùng tên states chuẩn.

3. **Context Injection Rules**  
   Chuẩn context dùng chung cho mọi prompt:
   - `current_user`
   - `active_workspace`
   - `selected_video`
   - `summary_status`
   - `chat_status`
   
   Và rule bắt buộc khi chuyển Summary -> Chatspace: giữ `selected_video`, `summary_highlights`, `timestamp_refs`.

4. **Per-page Delta Prompts (P1..P6)**  
   Mỗi prompt chỉ mô tả phần thay đổi so với baseline, luôn có dòng “preserve all previous context unless explicitly changed”.

## 4. Data flow & điều hướng context

- `P1` tạo điểm vào và chọn workspace.
- `P2` thiết lập baseline split 50/50.
- `P3` và `P4` chỉ đổi focus ratio + dim behavior.
- `P5` tạo `selected_video` + `summary_highlights`.
- `P6` nhận context từ `P5` và render `ContextPill` + opening message theo video đã chọn.

Context được coi là state liên tục của cùng một product, không phải 6 màn độc lập.

## 5. Consistency rules

Checklist bắt buộc cho từng prompt:
- Không đổi tên component đã chuẩn hóa trong catalog.
- Không đổi palette/token ngoài guardrails.
- Không phá vỡ ratio layout đã chỉ định (50/50 hoặc 60/40).
- Luôn có trạng thái bắt buộc: default, progress (loading/streaming), result, error.
- Không phát sinh component mới nếu đã có trong catalog.

## 6. Kiểm thử tài liệu

Kiểm theo checklist sau khi sửa file:
- Prompt P1..P6 đều có câu neo context.
- Các component names xuất hiện nhất quán giữa các prompt.
- Có thể đọc tài liệu theo thứ tự từ trên xuống để dựng cùng một hệ UI liên tục.

## 7. Kết quả kỳ vọng

Sau khi áp dụng thiết kế này, Stitch nhận được prompt theo trang nhưng vẫn bị “khóa mềm” bởi guardrails + reusable catalog + context rules, từ đó giảm đáng kể hiện tượng UI rời rạc.
