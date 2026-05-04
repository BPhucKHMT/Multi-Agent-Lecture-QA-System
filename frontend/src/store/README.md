# store — Client State

`frontend/src/store/` chứa state dùng chung giữa nhiều page/component, đặc biệt là trạng thái hội thoại.

---

## Vai trò

Store giúp quản lý:

- session/conversation hiện tại;
- danh sách message;
- trạng thái loading/streaming;
- lịch sử phiên chat;
- dữ liệu cần chia sẻ giữa sidebar và chat workspace.

---

## Khi nào dùng store?

Dùng store khi state:

- được nhiều component cần đọc/ghi;
- cần tồn tại khi chuyển component/page;
- không phải state UI nhỏ chỉ dùng trong một component.

Không nên đưa mọi thứ vào store. State local như mở/đóng modal nhỏ có thể dùng `useState` tại component.

---

## Quy ước

- Action đặt tên theo hành động nghiệp vụ.
- Không gọi API trực tiếp ở quá nhiều nơi khác nhau nếu store đã quản lý flow đó.
- Khi đổi shape message/session, cập nhật `src/types/`.
