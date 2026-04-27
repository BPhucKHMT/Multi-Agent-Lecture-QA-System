
# Sửa lỗi: Invalid JSON output / OUTPUT_PARSING_FAILURE (LangChain agents)

Mô tả ngắn
- Triệu chứng: "Invalid json output" hoặc lỗi JSON như `Expecting value: line 1 column 1 (char 0)` khi agent trả về kết quả (ví dụ tạo quiz). Streaming không hiện, agent báo đã thực thi nhưng không thấy code.

Nguyên nhân thường gặp
1. LLM trả text không phải JSON (extra text, explanation). 
2. LLM trả chuỗi rỗng (timeout/không có output). 
3. Prompt/format instructions không bắt buộc JSON hoặc thiếu stop sequences. 
4. Streaming/handler cấu hình sai (streaming off hoặc callback thiếu). 
5. Tool/toolkit thực thi nhưng không trả giá trị (stdout bị mất, hoặc tool trả None).

Bước khắc phục (quick checklist)
1. Log raw output
```py
resp = llm(prompt)
print('RAW OUTPUT:\n', resp)
```
2. Sử dụng StructuredOutputParser (LangChain)
```py
from langchain.output_parsers import StructuredOutputParser
from langchain.schema import OutputParserException

schema = {
  "type": "object",
  "properties": {
    "quiz": {"type":"array"}
  },
  "required": ["quiz"]
}
parser = StructuredOutputParser.from_schema(schema)
prompt = f"{instruction}\n{parser.get_format_instructions()}"
resp = llm(prompt)
try:
    parsed = parser.parse(resp)
except OutputParserException:
    # fallback to repair
    pass
```
3. Repair loop khi parse thất bại
- Ghi log raw output, sau đó gửi lại cho model prompt: "Your previous output was invalid JSON. Return only the corrected JSON matching schema:" và include original output.
- Hoặc dùng regex để extract first JSON block, rồi json.loads.

4. Đặt stop sequences & format instructions rõ ràng
- Thêm: `You must output ONLY valid JSON` và stop tokens (nếu hỗ trợ).
- Giảm temperature → 0 để tăng tính ổn định.

5. Streaming không hiện
- Kiểm tra model có hỗ trợ streaming; bật streaming=True và truyền callbacks như StreamingStdOutCallbackHandler hoặc custom callback để đẩy token lên UI (Streamlit, FastAPI SSE, v.v.).
- Ví dụ (LangChain ChatModel):
```py
chat = ChatOpenAI(streaming=True, callbacks=[StreamingStdOutCallbackHandler()], temperature=0)
```
- Với Streamlit, dùng st.empty() và cập nhật từng token từ callback.

6. Agent thực thi nhưng không hiển thị code
- Đảm bảo tool trả giá trị (return string). Nếu tool chạy subprocess, capture stdout và return nó.
- AgentExecutor(..., return_intermediate_steps=True) để debug các bước.

7. Logging & debug
- Bật verbose/DEBUG ở langchain: `import logging; logging.basicConfig(level=logging.DEBUG)`
- Ghi raw model output + prompt để dễ repro.

8. Các mẹo bổ sung
- Giới hạn max_tokens để tránh model thêm giải thích dài.
- Nếu output thường bị prefix/suffix text, trong parser dùng regex: `re.search(r"\{.*\}", raw, re.S)` trước json.loads.
- Dùng temperature=0 và deterministic prompt templates.

Ví dụ fallback repair function
```py
import re, json

def robust_load_json(raw):
    # try direct
    try:
        return json.loads(raw)
    except Exception:
        # extract first {...} or [..]
        m = re.search(r"(\{.*\}|\[.*\])", raw, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                return None
        return None
```

Tài liệu tham khảo
- LangChain OUTPUT_PARSING_FAILURE: https://python.langchain.com/docs/troubleshooting/errors/OUTPUT_PARSING_FAILURE

Nếu cần, có thể gửi:
1) prompt + raw model output (giấu API key) để mình phân tích
2) mã agent/tool đang dùng (đặc biệt phần tool return và cấu hình agent)

---
Phiên bản nhanh: nếu muốn, sẽ bổ sung ví dụ code cụ thể cho Streamlit/AgentExecutor hoặc mẫu prompt repair. (Trả lời có/không để tiếp tục.)

---

## Nhật ký xử lý (2026-04-15)

### Step 1 - Review plan + backup file sẽ sửa
- Đã review checklist trong file này.
- Đã backup các file chuẩn bị sửa:
  - `src/rag_core/agents/quiz.py` → `artifacts/backups/20260415_1302/quiz.py.bak`
  - `tests/rag_core/test_lang_graph_rag.py` → `artifacts/backups/20260415_1302/test_lang_graph_rag.py.bak`
- Tiếp theo: viết test tái hiện lỗi `OUTPUT_PARSING_FAILURE` trước khi sửa code.

### Step 2 - Tái hiện lỗi bằng test (RED)
- Đã thêm test mới: `tests/rag_core/test_quiz_json_parsing.py`.
- Kết quả chạy:
  - `pytest -q tests/rag_core/test_quiz_json_parsing.py` → **2 failed**
  - Lỗi đúng kỳ vọng: module `quiz` chưa có hàm fallback parse JSON khi output có prefix/fenced block.

### Step 3 - Root cause
- `node_quiz` đang phụ thuộc cứng vào `JsonOutputParser` trong chain `prompt | llm | parser`.
- Khi model trả về text có tiền tố mô tả hoặc markdown fence (thực tế thường gặp trên Streamlit), parser ném `OUTPUT_PARSING_FAILURE` và toàn bộ luồng trả `"Lỗi tạo quiz: Invalid json output..."`.
- Chưa có nhánh fallback để:
  1) lấy raw output từ LLM,
  2) bóc tách JSON object,
  3) validate schema quiz rồi tiếp tục render.

### Step 4 - Implement fix (GREEN)
- Sửa `src/rag_core/agents/quiz.py`:
  - Thêm `_extract_quiz_json_payload(raw)` để parse JSON từ:
    - raw JSON thuần,
    - fenced block ```json ... ```,
    - chuỗi có prefix text + JSON object.
  - Đổi flow generate:
    - Ưu tiên parse chuẩn qua `JsonOutputParser`.
    - Nếu fail, fallback gọi `prompt | llm` để lấy raw content, extract JSON, rồi `QuizOutput.model_validate(...)`.
- Kết quả test:
  - `pytest -q tests/rag_core/test_quiz_json_parsing.py tests/rag_core/test_lang_graph_rag.py` → **4 passed**.
