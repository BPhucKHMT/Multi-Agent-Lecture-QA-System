# pages — Route-Level Screens

`frontend/src/pages/` chứa các màn hình cấp route/page của ứng dụng.

---

## Vai trò

Page chịu trách nhiệm:

- bố cục cấp màn hình;
- gọi store/API ở mức workflow;
- nối các component lại với nhau;
- xử lý loading/error cấp trang.

---

## Luồng page thường gặp

```txt
Route
  ↓
Page component
  ↓
Fetch/init data
  ↓
Render layout + components
  ↓
User interaction
  ↓
Store/API update
```

---

## Quy ước

- Không để page phình quá lớn; tách UI nhỏ sang `components/`.
- Không duplicate API logic giữa nhiều page; đưa vào `lib/api` hoặc store.
- Page text/empty state/error state viết tiếng Việt.
