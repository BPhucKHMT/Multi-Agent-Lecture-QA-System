# storage — Vector Store Management

`src/storage/` chứa wrapper quản lý vector database cho RAG.

---

## Vai trò

Module này kết nối và thao tác với ChromaDB persistent store nằm trong `artifacts/database_semantic/`.

```txt
Data pipeline
  ↓
Create chunks + embeddings
  ↓
storage/vectorstore.py
  ↓
ChromaDB persistent directory
  ↓
Runtime retrieval
```

---

## Cấu trúc

```txt
storage/
└── vectorstore.py  # ChromaDB wrapper/helper
```

---

## Lưu ý

- Không hardcode path nếu đã có env như `PUQ_VECTOR_DB_DIR`.
- Nếu đổi embedding model/dim, cần rebuild vector DB.
- Retrieval quality phụ thuộc dữ liệu trong ChromaDB và metadata chunk.
