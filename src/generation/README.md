# generation — LLM Factory

`src/generation/` chứa logic khởi tạo LLM client dùng bởi agents.

---

## Vai trò

Module này gom cấu hình model/API key vào một nơi để các agent không tự tạo client rải rác.

```txt
Agent
  ↓
generation/llm_model.py
  ↓
ChatOpenAI / configured LLM
```

---

## Cấu trúc

```txt
generation/
└── llm_model.py  # Hàm/helper khởi tạo model chat
```

---

## Biến môi trường liên quan

| Biến | Mục đích |
|---|---|
| `myAPIKey` | OpenAI API key |
| `OPENAI_MODEL` | Model chat mặc định |
| `OPENAI_MAX_TOKENS` | Giới hạn token nếu module đọc biến này |

---

## Lưu ý

- Không log API key.
- Nếu đổi model, kiểm tra prompt/tool-calling compatibility.
- Nếu thêm model riêng cho supervisor, giữ tên biến rõ ràng.
