# Text-to-UI Figma Orchestrator Design

## 1. Mục tiêu

Xây pipeline từ văn bản markdown có cấu trúc sang Figma tự động bằng MCP, sau đó dừng để review thủ công. Chỉ khi user xác nhận `OK` thì mới chuyển sang bước generate code giao diện.

## 2. Phạm vi

### In scope
- Đầu vào: `ui-spec.md` có cấu trúc rõ (screens, components, states).
- Tạo/đồng bộ UI trong Figma qua Framelink Figma MCP.
- Sinh báo cáo diff sau mỗi lần sync.
- Cổng review thủ công `OK/revise`.

### Out of scope
- Auto-deploy frontend.
- Tự chọn stack codegen ngay ở phase hiện tại (để user chọn sau).

## 3. Kiến trúc tổng thể

> Ghi chú vị trí code: toàn bộ module triển khai đặt dưới `frontend/ui2figma/` (không đặt trong `src/`).

1. `spec_parser`
   - Parse markdown thành `UISpec` JSON chuẩn.
   - Validate field bắt buộc.
2. `figma_mapper`
   - Map `UISpec` -> Figma operations (frame, auto layout, text, instance).
3. `mcp_executor`
   - Gọi MCP server để apply operations lên file Figma.
4. `review_gate`
   - Dừng pipeline, chờ user xác nhận `OK` hoặc `revise`.
5. `codegen_adapter`
   - Chạy sau review `OK`; chuyển spec + metadata thành input cho bước sinh code UI.

## 4. Data flow

1. User cung cấp/cập nhật `ui-spec.md`.
2. `spec_parser` parse và validate.
3. `figma_mapper` tạo danh sách operations.
4. `mcp_executor` tạo/cập nhật nodes trong Figma.
5. Hệ thống tạo `sync_report`:
   - created/updated nodes
   - warnings
   - unmapped components
6. `review_gate`:
   - `OK` -> mở `codegen_adapter`
   - `revise` -> quay lại bước 1 với patch spec.

## 5. Contract dữ liệu đề xuất

```json
{
  "meta": { "project": "string", "version": "string" },
  "screens": [
    {
      "id": "home",
      "name": "Home",
      "layout": { "direction": "vertical", "gap": 16, "padding": 24 },
      "components": [
        { "type": "header", "props": { "title": "..." } },
        { "type": "card-list", "props": { "items": [] } }
      ],
      "states": ["default", "loading", "error"]
    }
  ],
  "design_tokens": {
    "colors": {},
    "typography": {},
    "spacing": {}
  }
}
```

## 6. Error handling

- **Validation error**: thiếu field bắt buộc -> fail sớm + trả line/section markdown gây lỗi.
- **Mapping error**: component chưa hỗ trợ -> ghi `unmapped` trong report, không bỏ qua im lặng.
- **MCP runtime error**: retry giới hạn + log command, payload rút gọn, node-id liên quan.

## 7. Testing strategy

1. Parser unit tests
   - markdown hợp lệ -> parse đúng schema
   - markdown thiếu field -> lỗi đúng vị trí
2. Mapper golden tests
   - `UISpec` mẫu -> expected operations cố định
3. MCP smoke test
   - 1 spec nhỏ -> tạo được page/frame chính trong Figma
4. Review gate test
   - `revise` không cho qua codegen
   - `OK` mới cho chạy codegen

## 8. Definition of Done

- Parse được markdown spec chuẩn và báo lỗi rõ nếu sai.
- Sync được Figma cho các component lõi.
- Có `sync_report` rõ ràng cho create/update/unmapped.
- Review gate hoạt động đúng logic `OK/revise`.
- Sẵn sàng nối sang phase generate code UI.

## 9. Gợi ý thực thi ngay

1. Chốt schema markdown `ui-spec.md` v1.
2. Làm parser + validator trước.
3. Làm mapper cho nhóm component lõi (header, button, input, card, list).
4. Nối MCP executor và tạo report.
5. Thêm review gate rồi mới mở phase codegen.
