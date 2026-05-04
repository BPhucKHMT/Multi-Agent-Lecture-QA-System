# tools — Agent Tools

`src/rag_core/tools/` chứa công cụ mà các agent có thể gọi trong workflow.

---

## Cấu trúc

```txt
tools/
└── sandbox.py  # Chạy code snippet trong môi trường giới hạn
```

---

## Sandbox dùng để làm gì?

Coding Agent dùng sandbox để:

1. chạy code nhẹ;
2. bắt lỗi runtime/syntax;
3. gửi lỗi lại cho LLM để tự sửa;
4. chỉ giải thích nếu code quá nặng hoặc không an toàn.

---

## Lưu ý an toàn

- Không mở rộng quyền sandbox nếu không cần.
- Không cho chạy tác vụ hệ thống nguy hiểm.
- Giới hạn thời gian/tài nguyên khi execute code.
- Nếu đổi output shape của sandbox, cập nhật `coding.py`.
