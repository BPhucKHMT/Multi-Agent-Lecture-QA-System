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
| `OPENAI_MODEL` | Model chat mặc định (`gpt-6-luna`) |
| `OPENAI_SUPERVISOR_MODEL` | Model dự phòng khi Experiential Jev lỗi (`gpt-6-luna`) |
| `EXPERIENTIAL_API_KEY` | API key server-side Experiential Labs (`xpl_...`) |

---

## Lưu ý

- Supervisor gửi route và các trường quiz dạng typed tới `POST https://api.experientiallabs.ai/v1/systemone` với model `jev-latest`.
- Request giữ nguyên nội dung hội thoại; số câu, độ khó, ngôn ngữ, dạng câu, số lựa chọn, ẩn đáp án/giải thích được đánh giá trong cùng lượt. Các trường ẩn dùng kiểu `noul`.
- Quiz hỗ trợ trắc nghiệm (mặc định 4 lựa chọn A–D), đúng/sai và trả lời ngắn. Số lựa chọn người dùng chỉ định được giữ; đầu ra được kiểm tra đúng số lựa chọn.
- Nếu thiếu credential, API/route lỗi hoặc output không hợp lệ, Supervisor fallback sang GPT-6 Luna qua `ChatOpenAI`.
- Không log API key.
