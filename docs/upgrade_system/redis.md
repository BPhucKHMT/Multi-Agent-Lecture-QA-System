# Kế hoạch nâng cấp Redis Stack Semantic Cache cho Chat

Tài liệu này mô tả kế hoạch triển khai cache câu hỏi/câu trả lời bằng **Redis Stack local** cho hệ thống RAG QABot.
Mục tiêu chính là lưu đầy đủ lịch sử hội thoại trong DB, đồng thời dùng Redis Stack để vector search các câu hỏi tương đồng và trả lời nhanh nếu cache an toàn để tái sử dụng.

---

## 1. Quyết định thiết kế đã chốt

| Hạng mục | Quyết định |
|---|---|
| Nguồn dữ liệu bền vững | DB/PostgreSQL là source of truth |
| Vai trò Redis | Cache semantic tốc độ cao, có thể rebuild từ DB |
| Redis runtime | Redis Stack local bằng Docker |
| Phạm vi cache | Hybrid |
| Prewarm khi backend start | Load N cặp Q/A gần nhất từ DB |
| Vector search | Dùng RediSearch/Vector Search của Redis Stack |
| LLM judge | Không dùng trong plan này |

> [!IMPORTANT]
> Không dùng Redis làm nơi lưu chính rồi “sau một thời gian mới ghi DB”. Cách production hơn là ghi DB ngay, sau đó mới ghi Redis cache nếu response đủ điều kiện.

---

## 2. Bối cảnh hiện tại

Backend hiện đã có các thành phần liên quan:

| Thành phần | File | Trạng thái |
|---|---|---|
| Lưu lịch sử hội thoại | `backend/app/models/user.py` | Đã có model `ChatHistory` |
| Chat streaming service | `backend/app/services/chat.py` | Đã lưu user/assistant message |
| Redis client | `backend/app/db/redis.py` | Đã có singleton Redis client |
| Semantic cache | `backend/app/core/cache/semantic.py` | Đã có, nhưng mới match theo hash |
| Chat history API | `backend/app/api/v1/endpoints/chat.py` | Đã có `/chat/history`, `/chat/sessions` |

Luồng hiện tại trong `generate_chat_stream`:

1. Kiểm tra Redis cache bằng `SemanticCache.get(user_message)`.
2. Nếu cache hit thì stream câu trả lời từ cache.
3. Nếu cache miss thì lấy lịch sử DB, gọi LangGraph, stream token.
4. Lưu user message và assistant response vào `chat_history`.
5. Lưu response vào Redis cache.

---

## 3. Vấn đề cần sửa

### 3.1. Cache hit có thể làm thiếu câu hỏi user trong lịch sử

Hiện tại nhánh cache hit `return` sớm trước khi chạy đoạn lưu user message.
Vì vậy lịch sử DB có thể chỉ có:

```txt
assistant: <câu trả lời lấy từ cache>
```

nhưng thiếu:

```txt
user: <câu hỏi vừa hỏi>
```

Điều này làm UI lịch sử chat bị lệch cặp hỏi/đáp.

### 3.2. `SemanticCache` chưa thật sự semantic

File `backend/app/core/cache/semantic.py` đang dùng:

```python
cache_key = f"semantic_cache:hash:{hash(prompt)}"
```

Hệ quả:

- `RAG là gì?` có thể hit cache nếu hỏi lại đúng chuỗi.
- `Bạn giải thích RAG là gì được không?` sẽ bị xem là câu khác, dù ý nghĩa tương tự.

Ngoài ra `hash(prompt)` của Python không ổn định tuyệt đối giữa các process vì hash randomization.
Không nên dùng làm cache key bền vững.

### 3.3. Không phải câu trả lời nào cũng nên tái sử dụng

Nếu bot trả lời lỗi hoặc câu trả lời phụ thuộc ngữ cảnh cá nhân/session, không nên đưa vào Redis semantic cache.
Tuy nhiên vẫn nên lưu DB để audit/debug và hiển thị đúng lịch sử hội thoại.

---

## 4. Nguyên tắc production

### 4.1. DB là source of truth

Mọi câu hỏi/câu trả lời phải được lưu DB ngay khi phát sinh:

```txt
User hỏi
→ lưu user message vào DB ngay
→ cache hit hoặc miss
→ lưu assistant response vào DB ngay
→ nếu response đủ điều kiện thì ghi Redis
```

Nếu Redis crash hoặc mất data, hệ thống vẫn còn lịch sử DB và có thể prewarm lại.

### 4.2. Redis chỉ là cache có thể rebuild

Redis Stack lưu:

- prompt đã normalize;
- embedding của prompt;
- response JSON;
- metadata cache/quality;
- exact hash để hit nhanh;
- vector index để search câu hỏi tương đồng.

Redis mất dữ liệu không được làm mất lịch sử chat.

### 4.3. Không dùng LLM judge

Plan này **không dùng LLM judge** để chấm câu trả lời đúng/sai vì:

- tăng latency;
- tăng chi phí;
- judge cũng có thể sai;
- chưa cần cho phase này.

Thay vào đó dùng:

1. rule kỹ thuật để loại response lỗi;
2. heuristic chất lượng để tránh cache response nghi ngờ;
3. user feedback ở phase sau nếu cần xoá cache câu sai.

---

## 5. Bot biết câu sai bằng cách nào?

Hệ thống **không thể tự biết chắc 100% câu trả lời sai về nội dung** nếu không có ground truth hoặc user feedback.
Vì vậy ta chia thành 3 mức:

### 5.1. Lỗi chắc chắn — tự phát hiện được

Các case này không được cache:

- LangGraph exception;
- OpenAI/API error;
- timeout;
- `final_response.type == "error"`;
- response text rỗng;
- JSON output parse lỗi;
- coding/math verification fail nếu agent có verifier.

### 5.2. Nghi ngờ chất lượng thấp — dùng heuristic

Không chắc sai, nhưng không nên cache nếu có dấu hiệu:

- câu trả lời quá ngắn;
- câu hỏi RAG nhưng response không có citation/source;
- bot nói “không tìm thấy thông tin”, “không chắc”, “có thể”;
- retrieval confidence thấp nếu metadata có;
- câu hỏi phụ thuộc lịch sử chat như “câu trên”, “ý bạn vừa nói”, “code của tôi”.

### 5.3. Sai thật sự về nội dung — cần user feedback hoặc verifier chuyên biệt

Nếu bot trả lời sai nhưng format vẫn hợp lệ, hệ thống không thể tự biết chắc.
Phase này xử lý bằng cách:

- chỉ cache response vượt quality gate;
- không cache các câu phụ thuộc ngữ cảnh;
- lưu metadata để sau này có thể đánh dấu `user_reported_bad`;
- nếu có feedback xấu, xoá cache item tương ứng.

> [!NOTE]
> Feedback endpoint là phase sau, không bắt buộc trong phase semantic cache đầu tiên.

---

## 6. Thiết kế Hybrid Cache

### 6.1. Cache scope

| Scope | Ý nghĩa | Dùng khi nào |
|---|---|---|
| `global` | Mọi user có thể tái dùng | Câu hỏi kiến thức bài giảng chung |
| `user` | Chỉ user đó dùng lại | Có yếu tố cá nhân nhưng vẫn cache được |
| `none` | Không cache | Câu phụ thuộc session, code riêng, lỗi, quiz/random |

Phase đầu ưu tiên:

- cache `global` cho câu hỏi RAG kiến thức chung;
- `none` cho các case còn lại;
- `user` có thể để phase sau nếu cần.

### 6.2. Cacheable rules phase đầu

Cache nếu thỏa tất cả:

- response có `text` không rỗng;
- response không phải `type="error"`;
- response type phù hợp, ưu tiên `rag`;
- câu hỏi không phụ thuộc history/session;
- câu hỏi không chứa code block dài;
- nếu là RAG thì nên có citation/video source;
- quality status là `ok`.

Không cache nếu:

- lỗi kỹ thuật;
- text quá ngắn/rỗng;
- câu hỏi kiểu “tiếp tục”, “giải thích câu trên”, “code của tôi sai gì”; 
- coding/quiz/random generation trong phase đầu;
- response có dấu hiệu không chắc hoặc không tìm thấy thông tin.

---

## 7. Redis Stack local setup

Chạy Redis Stack bằng Docker:

```powershell
docker run -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
```

- `6379`: Redis endpoint backend dùng.
- `8001`: RedisInsight UI.

Biến môi trường đề xuất:

```env
REDIS_URL=redis://localhost:6379/0
SEMANTIC_CACHE_ENABLED=True
SEMANTIC_CACHE_BACKEND=redis_stack
SEMANTIC_CACHE_THRESHOLD=0.92
SEMANTIC_CACHE_TTL_SECONDS=86400
SEMANTIC_CACHE_PREWARM_ENABLED=True
SEMANTIC_CACHE_PREWARM_LIMIT=1000
```

---

## 8. Thiết kế dữ liệu Redis Stack

### 8.1. Key namespaces

```txt
semantic_cache:exact:{sha256(normalized_prompt)} -> item_key
semantic_cache:item:{uuid} -> Redis HASH/JSON payload
idx:semantic_cache -> RediSearch vector index
```

### 8.2. Payload của item

```json
{
  "prompt": "RAG là gì?",
  "normalized_prompt": "rag là gì?",
  "response_json": "{...}",
  "response_text": "...",
  "response_type": "rag",
  "cache_scope": "global",
  "quality_status": "ok",
  "created_at": 1714480000,
  "embedding": "<binary vector>"
}
```

### 8.3. Vector index đề xuất

```txt
Index name: idx:semantic_cache
Prefix: semantic_cache:item:
Vector field: embedding
Algorithm: HNSW
Distance metric: COSINE
Dimension: theo embedding model đang dùng
```

Nếu dùng OpenAI `text-embedding-3-small`:

```txt
Dimension: 1536
```

---

## 9. Thuật toán cache lookup

### 9.1. Normalize prompt

Trước khi tạo hash hoặc embedding, normalize nhẹ:

1. Strip khoảng trắng đầu/cuối.
2. Lowercase.
3. Gom nhiều khoảng trắng thành một.
4. Không bỏ dấu tiếng Việt để tránh mất nghĩa.

Ví dụ:

```txt
"  RAG   là gì? " -> "rag là gì?"
```

### 9.2. Exact match path

1. Tạo `normalized_prompt`.
2. Tạo SHA-256 từ `normalized_prompt`.
3. Đọc `semantic_cache:exact:{sha256}`.
4. Nếu có `item_key`, lấy payload.
5. Chỉ trả nếu `quality_status=ok` và scope hợp lệ.

### 9.3. Vector search path

Nếu exact miss:

1. Tạo embedding cho prompt mới.
2. Query `FT.SEARCH` / KNN trên Redis Stack index.
3. Filter theo:
   - `quality_status:{ok}`;
   - `cache_scope:{global}` trong phase đầu.
4. Lấy best match.
5. Nếu similarity vượt `SEMANTIC_CACHE_THRESHOLD`, trả response.
6. Nếu không đạt ngưỡng, trả `None` để service gọi LangGraph.

---

## 10. Thuật toán cache write

Sau khi LangGraph trả kết quả:

1. Lưu assistant response vào DB trước.
2. Chạy quality/cacheability filter.
3. Nếu không cacheable, dừng.
4. Normalize prompt.
5. Tạo embedding cho prompt.
6. Tạo `item_key = semantic_cache:item:{uuid}`.
7. Lưu payload vào Redis.
8. Lưu exact mapping.
9. Đảm bảo item được index bởi RediSearch.
10. Cập nhật DB metadata nếu cần `cache_item_key`.

---

## 11. Prewarm Redis từ DB khi backend start

Khi backend start:

1. Kết nối Redis Stack.
2. Đảm bảo vector index tồn tại.
3. Query N cặp Q/A gần nhất từ `chat_history`.
4. Ghép assistant message với user message ngay trước nó trong cùng `session_id`.
5. Chạy lại cacheability filter.
6. Nếu hợp lệ và chưa có exact key, index vào Redis.

Cấu hình:

```env
SEMANTIC_CACHE_PREWARM_ENABLED=True
SEMANTIC_CACHE_PREWARM_LIMIT=1000
```

> [!WARNING]
> Không load toàn bộ lịch sử DB khi start. Chỉ load N cặp Q/A gần nhất để tránh startup chậm và tốn RAM.

---

## 12. Thay đổi file dự kiến

### 12.1. `backend/app/services/chat.py`

Mục tiêu: DB ghi ngay, Redis cache sau.

Thay đổi dự kiến:

1. Lấy lịch sử cũ từ DB.
2. Build `langchain_messages` từ lịch sử cũ.
3. Append `HumanMessage(content=user_message)`.
4. Lưu `ChatHistory(role="user")` vào DB.
5. Kiểm tra cache policy cho user message.
6. Nếu cacheable candidate:
   - search Redis Stack;
   - nếu hit, stream cached response;
   - lưu `ChatHistory(role="assistant", agent_type="cache")` vào DB;
   - return.
7. Nếu miss hoặc không cacheable:
   - chạy LangGraph;
   - lưu assistant response vào DB;
   - nếu response đạt quality gate thì index vào Redis.

### 12.2. `backend/app/core/cache/semantic.py`

Mục tiêu: dùng Redis Stack vector search thay vì Python `hash(prompt)`.

Thay đổi dự kiến:

- Thêm normalize prompt.
- Thêm SHA-256 exact key.
- Thêm tạo/check RediSearch index.
- Thêm vector lookup bằng KNN.
- Thêm set item với embedding + metadata.
- Thêm delete item theo key để dùng cho feedback phase sau.

### 12.3. `backend/app/core/config.py`

Thêm cấu hình:

```python
SEMANTIC_CACHE_BACKEND: str
SEMANTIC_CACHE_THRESHOLD: float
SEMANTIC_CACHE_TTL_SECONDS: int
SEMANTIC_CACHE_PREWARM_ENABLED: bool
SEMANTIC_CACHE_PREWARM_LIMIT: int
```

### 12.4. `.env.example`

Thêm biến mẫu:

```env
REDIS_URL=redis://localhost:6379/0
SEMANTIC_CACHE_ENABLED=True
SEMANTIC_CACHE_BACKEND=redis_stack
SEMANTIC_CACHE_THRESHOLD=0.92
SEMANTIC_CACHE_TTL_SECONDS=86400
SEMANTIC_CACHE_PREWARM_ENABLED=True
SEMANTIC_CACHE_PREWARM_LIMIT=1000
```

### 12.5. Startup/prewarm module

Thêm hoặc sửa startup hook để:

- gọi `ensure_index()`;
- prewarm N Q/A gần nhất nếu bật config.

---

## 13. Điều chỉnh theo code hiện tại

Sau khi review code hiện tại, cần bổ sung 4 điểm bắt buộc trước khi triển khai.

### 13.1. Semantic cache cần Redis client riêng cho vector binary

File `backend/app/db/redis.py` hiện tạo Redis client với:

```python
decode_responses=True
```

Cấu hình này phù hợp cho auth/rate limit vì Redis trả về `str`, nhưng Redis Stack vector field thường cần ghi embedding dạng binary bytes.
Nếu dùng cùng client `decode_responses=True`, có thể lỗi khi ghi/đọc vector binary.

Hướng triển khai:

- Giữ client hiện tại cho auth/rate limit.
- Thêm helper tạo Redis client riêng cho semantic cache với `decode_responses=False`.
- Semantic cache dùng client binary này để gọi `FT.CREATE`, `HSET`, `FT.SEARCH`.

Ví dụ ý tưởng:

```python
def get_redis_binary() -> redis.Redis:
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=False,
        socket_timeout=5,
        socket_connect_timeout=5,
    )
```

### 13.2. Embedding cache độc lập với embedding của RAG core

RAG core hiện dùng ChromaDB với embedding mặc định trong `src/storage/vectorstore.py`:

```txt
BAAI/bge-m3
```

Trong khi semantic cache hiện tại ở `backend/app/core/cache/semantic.py` đang dùng:

```txt
OpenAI text-embedding-3-small
```

Phase này sẽ tiếp tục dùng `text-embedding-3-small` cho semantic cache vì:

- code cache hiện tại đã dùng OpenAI embedding;
- dimension cố định 1536, dễ tạo Redis vector index;
- không cần load thêm model local nặng trong backend chat service;
- semantic cache không bắt buộc phải dùng cùng embedding với ChromaDB.

Cấu hình cần ghi rõ:

```env
SEMANTIC_CACHE_EMBEDDING_MODEL=text-embedding-3-small
SEMANTIC_CACHE_VECTOR_DIM=1536
```

### 13.3. Prewarm phải bỏ qua Q/A pair không hợp lệ

`chat_history` hiện không có `turn_id` hoặc `parent_message_id`, chỉ có:

```txt
user_id, session_id, role, content, created_at
```

Vì vậy prewarm phải ghép cặp theo thứ tự thời gian trong cùng `user_id + session_id`:

```txt
user message -> assistant message ngay sau đó
```

Cần skip nếu gặp các case:

- assistant không có user message ngay trước đó;
- user message không có assistant response;
- assistant content rỗng;
- assistant `metadata_json.type == "error"`;
- pair cũ bị lệch do bug cache hit trước đây thiếu user message;
- response không vượt quality/cacheability filter.

Prewarm không được giả định dữ liệu lịch sử luôn sạch.

### 13.4. Redis/prewarm lỗi không được làm backend fail startup

`backend/app/main.py` hiện đã có `lifespan` và background prewarm RAG resource.
Redis semantic prewarm nên đi theo hướng tương tự:

- `ensure_index()` có thể chạy lúc startup nhưng phải catch exception;
- prewarm N Q/A nên chạy background task;
- nếu Redis chưa bật hoặc Docker Redis Stack chưa chạy, backend vẫn phải start bình thường;
- lỗi Redis chỉ log warning/error, không crash API.

Nguyên tắc:

```txt
Redis cache unavailable -> fallback LangGraph/RAG + DB history bình thường
```

---

## 14. Checklist triển khai

- [x] Cập nhật config/env cho Redis Stack semantic cache.
- [x] Sửa `generate_chat_stream` để lưu câu hỏi user trước cache lookup.
- [x] Thêm cacheability/quality filter không dùng LLM judge.
- [x] Sửa `SemanticCache` dùng SHA-256 exact key.
- [x] Tạo Redis Stack vector index.
- [x] Lưu embedding + response + quality metadata vào Redis item.
- [x] Thêm vector search similarity bằng RediSearch KNN.
- [x] Thêm prewarm N cặp Q/A gần nhất từ DB khi backend start.
- [x] Cập nhật `.env.example`.
- [ ] Kiểm thử cache hit vẫn lưu đủ user + assistant vào DB.
- [ ] Kiểm thử câu hỏi tương tự có thể hit cache nếu vượt threshold.
- [ ] Kiểm thử response lỗi/nghi ngờ không được cache.
- [x] Cập nhật trạng thái checklist trong chính file này sau khi triển khai từng bước.

---

## 14. Rủi ro và giới hạn

### 14.1. Có thể trả nhầm nếu threshold thấp

Nếu `SEMANTIC_CACHE_THRESHOLD` quá thấp, câu hỏi gần giống nhưng khác ý có thể lấy nhầm đáp án.
Đề xuất bắt đầu từ `0.92` hoặc `0.95`.

Ví dụ rủi ro:

```txt
"RAG là gì?"
"RAG khác fine-tuning như thế nào?"
```

Hai câu cùng chủ đề nhưng yêu cầu khác nhau.
Threshold cao giúp giảm rủi ro này.

### 14.2. Embedding call làm cache miss tốn thêm thời gian

Khi exact miss, hệ thống cần gọi embedding model trước khi quyết định semantic hit/miss.
Đây là trade-off giữa tốc độ cache và khả năng hit câu tương tự.

### 14.3. Redis local không thay thế DB production

Redis local phù hợp dev/demo hoặc chạy cùng server.
Nếu deploy production nhiều instance, cần Redis server dùng chung hoặc Redis Cloud/managed Redis Stack.

### 14.4. Hệ thống không tự biết chắc mọi câu sai

Quality gate chỉ giúp loại lỗi kỹ thuật và response đáng nghi.
Sai nội dung tinh vi cần user feedback hoặc verifier chuyên biệt theo agent.
Plan này không dùng LLM judge.

---

## 15. Tiêu chí hoàn thành

Sau khi triển khai, hệ thống được xem là đạt nếu:

1. Câu hỏi user luôn được lưu vào DB dù cache hit hay miss.
2. Câu trả lời assistant luôn được lưu vào DB dù cache hit hay miss.
3. Hỏi lại đúng câu sẽ hit exact cache.
4. Hỏi câu tương tự có thể hit Redis Stack vector cache nếu similarity vượt threshold.
5. Response lỗi/rỗng/nghi ngờ không được ghi vào Redis cache.
6. Backend start có thể prewarm N Q/A gần nhất từ DB.
7. Nếu Redis hoặc cache lỗi, hệ thống vẫn fallback gọi LangGraph bình thường.
8. Không làm thay đổi API contract hiện tại của frontend.

---

## 16. Kế hoạch kiểm thử thủ công

### Case 1: Cache miss lần đầu

Input:

```txt
RAG là gì?
```

Kỳ vọng:

- Backend gọi LangGraph.
- DB có `user: RAG là gì?`.
- DB có `assistant: ...`.
- Nếu response đạt quality gate, Redis có cache item mới.

### Case 2: Exact cache hit

Input lần sau:

```txt
RAG là gì?
```

Kỳ vọng:

- Backend trả status cache hit.
- Không cần gọi LangGraph.
- DB vẫn lưu thêm `user` và `assistant` cho lần hỏi này.

### Case 3: Semantic cache hit

Input:

```txt
Bạn giải thích RAG là gì được không?
```

Kỳ vọng:

- Nếu similarity vượt threshold, backend trả từ Redis cache.
- DB vẫn lưu đủ cặp hỏi/đáp.

### Case 4: Semantic miss đúng

Input:

```txt
So sánh RAG và fine-tuning?
```

Kỳ vọng:

- Không lấy nhầm câu trả lời `RAG là gì?` nếu similarity dưới threshold hoặc intent khác.
- Backend gọi LangGraph để sinh câu trả lời mới.

### Case 5: Response lỗi không cache

Tạo case lỗi hoặc response `type="error"`.

Kỳ vọng:

- DB có thể lưu response để audit/debug.
- Redis không có item mới cho response lỗi.

### Case 6: Prewarm

1. Restart backend.
2. Backend tạo Redis index nếu chưa có.
3. Backend load N Q/A gần nhất từ DB.
4. Hỏi lại câu gần đây.

Kỳ vọng:

- Có thể hit Redis cache sau prewarm.

---

## 17. Ghi chú triển khai

- Không đổi cấu trúc bảng DB trong phase đầu; dùng `metadata_json` để lưu cache metadata.
- Không đổi response format SSE hiện tại.
- Không đổi frontend nếu API `/chat/stream`, `/chat/history`, `/chat/sessions` giữ nguyên.
- Nên log nhẹ cache hit type để debug:
  - `exact_hit`
  - `semantic_hit`
  - `miss`
  - `skip_not_cacheable`
- Không log nội dung nhạy cảm nếu sau này có dữ liệu riêng tư.
- Feedback endpoint đánh dấu câu trả lời sai là phase sau, chưa triển khai trong plan này.
