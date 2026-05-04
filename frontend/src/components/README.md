# components — UI Building Blocks

`frontend/src/components/` chứa các component giao diện tái sử dụng cho Chatspace, Sidebar, Markdown rendering và các phần UI chung.

---

## Vai trò

Components nên tập trung vào hiển thị và interaction nhỏ. Logic gọi API hoặc xử lý dữ liệu phức tạp nên để ở `lib/`, `store/` hoặc page container.

---

## Nhóm component thường gặp

```txt
components/
├── chat/      # Message list, input, markdown/code/math rendering
├── sidebar/   # Conversation/session navigation
└── shared/    # UI nhỏ dùng chung
```

---

## Quy ước

- Props rõ ràng, tránh component quá nhiều trách nhiệm.
- Text hiển thị viết tiếng Việt.
- Khi render Markdown/LaTeX/code, kiểm tra cả desktop và mobile.
- Component chat stream phải xử lý trạng thái loading/error/complete.
