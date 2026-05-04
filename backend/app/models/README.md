# models — SQLAlchemy Models

`backend/app/models/` chứa ORM models cho PostgreSQL.

---

## Vai trò

Models định nghĩa bảng dữ liệu chính của backend:

- user account;
- auth/session metadata nếu có;
- chat history;
- metadata JSON cho response AI.

---

## Model quan trọng

```txt
User
  ↓ 1-n
ChatHistory
```

`ChatHistory` lưu cả hai role:

```txt
role = "user"      -> question
role = "assistant" -> response
```

Nhờ vậy PostgreSQL luôn giữ lịch sử đầy đủ, kể cả khi Redis cache hit.

---

## Nguyên tắc

- Thay đổi schema production nên đi qua Alembic migration.
- Không lưu secret plaintext.
- JSON metadata chỉ nên chứa thông tin response/citation/cache cần thiết.
