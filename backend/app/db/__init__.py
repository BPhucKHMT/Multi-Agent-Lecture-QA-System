"""
Module này sẽ thực hiện các công việc:
- Khởi tạo kết nối đến cơ sở dữ liệu (PostgreSQL qua SQLAlchemy)
- Cung cấp các helper functions để tương tác với cơ sở dữ liệu (ví dụ: get_db)
- Quản lý kết nối đến Redis (Upstash) cho các chức năng như blacklist JTI, rate limit, semantic cache
"""
