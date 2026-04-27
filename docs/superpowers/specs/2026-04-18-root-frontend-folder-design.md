# Root Frontend Folder Design

## 1. Mục tiêu

Tạo một workspace frontend mới tại root (`frontend/`) để có thể chạy theo flow `cd frontend` trong tương lai, đồng thời giữ nguyên frontend Streamlit hiện tại trong `src/frontend`.

## 2. Phạm vi

### In scope
- Tạo thư mục `frontend/` ở root.
- Tạo `frontend/README.md` dạng placeholder.
- Không thay đổi luồng backend/Streamlit hiện tại.

### Out of scope
- Không init framework frontend (Vite/Next/Vue).
- Không di chuyển hoặc xóa `src/frontend`.
- Không thêm script build/run mới ở giai đoạn này.

## 3. Kiến trúc & thành phần

1. `src/frontend` (giữ nguyên): tiếp tục phục vụ giao diện Streamlit hiện tại.
2. `frontend/` (mới): namespace riêng cho frontend mới.
3. `frontend/README.md`: tài liệu entrypoint, ghi rõ đây là placeholder chờ setup framework.

## 4. Data flow sử dụng

1. Từ root project: `cd frontend`.
2. Đọc `README.md` để biết trạng thái workspace và bước tiếp theo.
3. Khi quyết định stack frontend thật, setup trực tiếp trong `frontend/` mà không ảnh hưởng `src/frontend`.

## 5. Error handling

- Nếu `frontend/` chưa có framework: README phải nêu rõ đây là thư mục placeholder, tránh hiểu nhầm “hỏng setup”.
- Nếu contributor chạy nhầm vào `src/frontend`: không đổi gì trong phase này, tài liệu sẽ tách bạch hai mục đích.

## 6. Kiểm tra hoàn tất

- `frontend/` tồn tại ở root.
- `frontend/README.md` tồn tại và đọc được.
- `src/frontend` vẫn nguyên trạng.

## 7. Tiêu chí Done

- Có thể dùng flow `cd frontend` ngay từ bây giờ.
- Có chỗ cố định để triển khai frontend mới ở phase tiếp theo.
