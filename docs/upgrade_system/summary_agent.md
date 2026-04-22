# Summary Agent — Thiết kế nâng cấp tóm tắt video

**Ngày tạo:** 2026-04-22  
**Phạm vi:** Nâng cấp luồng Summary Hub: thay extractive → LLM-based summary + inject context vào Chatspace.

---

## 1. Vấn đề hiện tại

| Vấn đề | Chi tiết |
|--------|----------|
| **Tóm tắt không thực sự "hiểu" nội dung** | `_extractive_summary()` chỉ lấy 8 câu đầu tiên theo regex, không phân tích nội dung |
| **Context bị mất khi chuyển sang Chatspace** | `onDiscussInChat` chỉ truyền `{ title, subtitle }` — không có nội dung tóm tắt |
| **Agent không dùng summary làm ngữ cảnh** | LangGraph supervisor không nhận được context từ Summary Hub |

---

## 2. Quyết định thiết kế (đã confirm với user)

| # | Câu hỏi | Lựa chọn |
|---|---------|---------|
| 1 | Chế độ tóm tắt | **B — LLM một lần + in-memory cache theo `video_id`** |
| 2 | Inject vào Chatspace | **B — Hiển thị như tin nhắn AI đầu tiên** |
| 3 | Cấu trúc output | **B — Có cấu trúc: Mục tiêu → Khái niệm chính → Kết luận + Gợi ý** |

---

## 3. Kiến trúc tổng thể

```
[Summary Hub UI]
       │
       │ Bấm "Tóm tắt"
       ▼
POST /videos/summary { video_id }
       │
       ▼
[SummaryAgentService]
  ├── Kiểm tra cache (Dict[video_id → summary_text])
  │       ├── HIT → trả về ngay
  │       └── MISS → gọi LLM pipeline
  │              ├── Đọc transcript từ artifacts/data/
  │              ├── Nếu transcript > 12k chars → cắt đại diện
  │              ├── Gọi GPT-4o-mini với structured prompt
  │              └── Lưu vào cache → trả về
       │
       ▼
[Summary Hub UI] hiển thị tóm tắt có cấu trúc
       │
       │ Bấm "Thảo luận trong Chatspace"
       ▼
[WorkspacePage] chuyển sang Chatspace + inject summary vào messages
       │
[Chatspace] hiển thị tin nhắn AI đầu tiên = nội dung tóm tắt (như context)
       │
[User] bắt đầu chat với Agent — Agent nhận được summary trong history
```

---

## 4. Thay đổi Backend

### 4.1. `src/api/services/summary_service.py` [NEW]

File mới, tách riêng khỏi `chat_service.py` để giữ Single Responsibility.

```python
# Pseudocode
_summary_cache: Dict[str, str] = {}  # in-memory, per-process

async def summarize_with_llm(video_id: str) -> dict:
    if video_id in _summary_cache:
        return {"video_id": video_id, "summary": _summary_cache[video_id]}
    
    transcript_text = _load_transcript(video_id)  # đọc từ artifacts/data/
    if not transcript_text.strip():
        return {"video_id": video_id, "summary": "Không tìm thấy transcript."}
    
    summary = await _call_llm_summary(transcript_text)
    _summary_cache[video_id] = summary
    return {"video_id": video_id, "summary": summary}
```

### 4.2. Structured Prompt cho LLM

```
Bạn là trợ lý giáo dục chuyên tóm tắt bài giảng video.
Hãy đọc transcript sau và tạo tóm tắt theo đúng cấu trúc bên dưới.
QUAN TRỌNG: Chỉ dùng thông tin có trong transcript, không tự thêm.

Transcript:
{transcript_text}

Trả về đúng cấu trúc Markdown sau:

## 🎯 Mục tiêu bài giảng
[1-2 câu mô tả bài học muốn đạt được gì]

## 📚 Các khái niệm chính
- **[Khái niệm 1]**: [Giải thích ngắn, 1 câu]
- **[Khái niệm 2]**: [Giải thích ngắn, 1 câu]
...

## ✅ Kết luận
[2-3 câu tóm tắt điểm mấu chốt học viên cần nhớ]

## 💬 Gợi ý câu hỏi thảo luận
- [Câu hỏi 1]
- [Câu hỏi 2]
- [Câu hỏi 3]
```

### 4.3. Xử lý transcript dài

Transcript có thể rất dài (>50k chars). Chiến lược:
- Giới hạn **24,000 ký tự đầu** (tương đương ~6k tokens).
- Nếu transcript > 24k: lấy 12k đầu + 12k cuối để bao quát phần mở đầu và kết luận.

```python
def _trim_transcript(text: str, max_chars: int = 24000) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n\n[...]\n\n" + text[-half:]
```

### 4.4. Output Format LLM — Spec bắt buộc

> **Quan trọng:** Frontend dùng `MarkdownRenderer` (`ReactMarkdown + remarkGfm`). LLM **PHẢI** trả đúng Markdown chuẩn để render đẹp tự động — không cần component riêng.

**Cấu trúc output bắt buộc:**

```markdown
## 🎯 Mục tiêu bài giảng
[1-2 câu mô tả bài học muốn đạt được gì]

## 📚 Các khái niệm chính
- **[Khái niệm 1]**: [Giải thích ngắn, 1 câu]
- **[Khái niệm 2]**: [Giải thích ngắn, 1 câu]
- **[Khái niệm 3]**: [Giải thích ngắn, 1 câu]

## ✅ Kết luận
[2-3 câu tóm tắt điểm mấu chốt học viên cần nhớ]

## 💬 Gợi ý câu hỏi thảo luận
- [Câu hỏi 1]
- [Câu hỏi 2]
- [Câu hỏi 3]
```

**Quy tắc format LLM phải tuân thủ:**

| Quy tắc | Chi tiết |
|---------|---------|
| Dùng `##` cho heading (không dùng `#` hay `###`) | `prose-headings` của Tailwind render `h2` đẹp nhất |
| Dùng `**bold**` cho term chính | `prose-strong:text-violet-950` sẽ highlight màu tím |
| Dùng bullet `- ` (không dùng `*`) | `remarkGfm` parse bullet chuẩn |
| Không dùng bảng (table) | Tránh overflow trong mobile, list dễ đọc hơn |
| Không dùng code block (``` ```) | Summary không cần code |
| Tối đa ~600 từ | Giữ token history nhẹ khi inject vào Chatspace |

**Ví dụ output chuẩn:**

```markdown
## 🎯 Mục tiêu bài giảng
Bài giảng giới thiệu AutoML — công nghệ tự động hóa quá trình xây dựng mô hình học máy, giúp giảm bớt công sức chuyên môn và mở rộng khả năng ứng dụng ML.

## 📚 Các khái niệm chính
- **AutoML**: Tự động hóa quy trình từ tiền xử lý dữ liệu đến chọn mô hình và tối ưu tham số.
- **NAS (Neural Architecture Search)**: Kỹ thuật tự động tìm kiếm kiến trúc mạng neural tối ưu.
- **HPO (Hyperparameter Optimization)**: Tự động điều chỉnh siêu tham số thay vì thử thủ công.

## ✅ Kết luận
AutoML không thay thế Data Scientist mà giúp họ tập trung vào bài toán business thay vì tối ưu kỹ thuật. Các thư viện phổ biến gồm Auto-sklearn, H2O AutoML và Google AutoML.

## 💬 Gợi ý câu hỏi thảo luận
- AutoML có thể áp dụng cho bài toán nào trong thực tế?
- Sự khác biệt giữa NAS và HPO là gì?
- Khi nào nên dùng AutoML thay vì xây model thủ công?
```

### 4.5. `src/api/router.py` — Sửa endpoint


```python
# Thay summarize_video (sync) bằng summarize_with_llm (async)
@router.post("/videos/summary", response_model=VideoSummaryResponse)
async def video_summary(request: VideoSummaryRequest):
    return await summarize_with_llm(request.video_id)
```

---

## 5. Thay đổi Frontend

### 5.1. Type `DiscussionContext` — Thêm trường `summaryText`

**File:** `frontend/src/types/app.ts`

```typescript
// Trước
export type DiscussionContext = {
  title: string;
  subtitle: string;
};

// Sau
export type DiscussionContext = {
  title: string;
  subtitle: string;
  summaryText?: string;  // Nội dung tóm tắt đầy đủ
};
```

### 5.2. `WorkspacePage.tsx` — Truyền summaryText khi chuyển sang Chatspace

```typescript
// Trong SummaryHubPanel, hàm onDiscussInChat gọi:
onDiscussInChat({
  title: selectedVideo.title,
  subtitle: `video_id=${selectedVideo.video_id}`,
  summaryText: summaryText,  // THÊM MỚI
});
```

### 5.3. `WorkspacePage.tsx` — Inject summary thành tin nhắn AI đầu tiên

Khi `summaryContext` được set, thêm một `ConversationMessage` giả làm tin nhắn AI đầu tiên vào `messages` thông qua `addMessage`:

```typescript
const handleDiscussInChat = (context: DiscussionContext) => {
  setSummaryContext(context);
  
  // Inject summary vào Chatspace như tin nhắn AI đầu tiên
  if (context.summaryText) {
    addMessage({
      role: "assistant",
      content: `📋 **Tóm tắt video: ${context.title}**\n\n${context.summaryText}`,
    });
  }
  
  handleSectionChange("chatspace");
};
```

**Tại sao cơ chế này hoạt động:**
- `addMessage()` thêm tin nhắn vào `messages` state trong `conversationStore`.
- Khi user gửi câu hỏi, `sendPrompt` build payload: `messages: toApiMessages([...messages, optimisticUserMessage])`.
- `toApiMessages` serialize **tất cả** messages kể cả tin nhắn summary đã inject → backend nhận được summary trong `chat_history`.
- Supervisor Agent thấy summary trong history → trả lời đúng chủ đề.

### 5.4. `ChatInput.tsx` — Bug fix: Bỏ disabled khi có contextPill

> ⚠️ **Bug hiện tại (dòng 67):** Input bị khóa khi có `contextPill`, khiến user **không thể gõ câu hỏi** sau khi chuyển sang Chatspace.

```typescript
// TRƯỚC (bug — input bị lock khi contextPill active)
disabled={blocked || !!contextPill}

// SAU (fix — luôn cho phép gõ, contextPill chỉ là UI indicator)
disabled={blocked}
```

### 5.5. `WorkspacePage.tsx` — Clear context khi user clear conversation

```typescript
// Khi user bấm "New Conversation"
const handleNewConversation = () => {
  clearConversation();
  setSummaryContext(null);  // Reset context pill
};
```


---

## 6. Luồng dữ liệu đầy đủ (Sequence Diagram)

```
User         SummaryHub UI      Backend API    LLM (GPT-4o-mini)  Chatspace
 │                │                  │                │               │
 │─── chọn video ─▶                  │                │               │
 │─── bấm Tóm tắt ▶                  │                │               │
 │                │─── POST /videos/summary ──────────▶               │
 │                │                  │── check cache  │               │
 │                │                  │  (MISS)        │               │
 │                │                  │──── gọi GPT ───▶               │
 │                │                  │◀── structured summary ─────────│
 │                │                  │── lưu cache    │               │
 │                │◀─── { summary } ──                │               │
 │◀── hiển thị ───│                  │                │               │
 │                │                  │                │               │
 │─ bấm Thảo luận ▶                  │                │               │
 │                │                  │                │               │
 │                ╔══════════════════════════════════════════════════╗ │
 │                ║  addMessage({ role:"assistant", content:summary })║ │
 │                ║  setSummaryContext({ title, summaryText })        ║ │
 │                ║  navigate → /workspace/chatspace                  ║ │
 │                ╚══════════════════════════════════════════════════╝ │
 │                                                              │       │
 │◀────────────────────────── Chatspace hiển thị tin nhắn AI ──────────│
 │─── gõ câu hỏi ────────────────────────────────────────────────────▶ │
 │                                                               │       │
 │                (summary đã có trong messages history, Agent thấy) │  │
```

---

## 7. Checklist triển khai

### Backend
- [x] Tạo `src/api/services/summary_service.py` với `summarize_with_llm()` + cache + `_trim_transcript()`
- [x] Viết structured prompt cho LLM summary
- [x] Sửa `src/api/router.py`: đổi `summarize_video` → `summarize_with_llm` (async)
- [x] Xóa hàm `_extractive_summary()` và `summarize_video()` khỏi `chat_service.py`

### Frontend
- [x] Thêm field `summaryText?: string` vào type `DiscussionContext` (`types/app.ts`)
- [x] Sửa `onDiscussInChat()` trong `SummaryHubPanel` để truyền `summaryText`
- [x] Sửa handler chuyển sang Chatspace: gọi `addMessage()` inject tin nhắn AI trước khi navigate
- [x] Thêm `addMessage` vào `useConversationStore()` destructure ở `WorkspacePage`
- [x] Bug fix `ChatInput.tsx`: bỏ `disabled={!!contextPill}` để user gõ được sau khi chuyển từ Summary Hub
- [ ] Clear `summaryContext` khi user bấm "New Conversation" *(kiểm tra lại — `clearConversation` hiện tại không clear summaryContext)*

### Testing
- [ ] Test cache: bấm Tóm tắt video 2 lần → lần 2 phải trả ngay (không gọi LLM)
- [ ] Test Chatspace: sau khi bấm "Thảo luận", tin nhắn AI đầu tiên phải là bản tóm tắt
- [ ] Test Agent context: gõ câu hỏi liên quan đến video → Agent trả lời đúng chủ đề
- [ ] Test edge case: video không có transcript → hiển thị thông báo rõ ràng


---

## 8. Rủi ro & Lưu ý

| Rủi ro | Mức độ | Giải pháp |
|--------|--------|-----------|
| Transcript quá dài làm LLM bị lỗi context | Trung bình | Trim 24k chars (head+tail strategy) |
| Cache in-memory bị xóa khi restart server | Thấp | Chấp nhận được — lần đầu mất vài giây |
| LLM trả sai cấu trúc Markdown | Thấp | Prompt rõ ràng; nếu lỗi fallback về extractive |
| User inject summary quá dài làm history nặng | Thấp | Summary được cắt hợp lý (~500-800 tokens) |

### 📌 Lộ trình nâng cấp Cache (Production)

Cache hiện tại dùng `Dict` in-memory là phù hợp cho **giai đoạn phát triển (MVP)**. Khi deploy production với nhiều workers, cần migrate sang **Redis**:

```python
# Production: thay Dict bằng Redis (~10 phút migration)
import redis.asyncio as redis
_redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

async def summarize_with_llm(video_id: str) -> dict:
    cached = await _redis.get(f"summary:{video_id}")
    if cached:
        return {"video_id": video_id, "summary": cached.decode()}
    ...
    await _redis.setex(f"summary:{video_id}", 604800, summary)  # TTL 7 ngày
```

**Lý do Redis phù hợp cho use-case này:**
- Summary video rất ổn định (transcript không đổi) → TTL 7 ngày là hợp lý.
- Chi phí tạo 1 summary ~$0.01 + 5-10s → rất đáng cache.
- Khi chạy `uvicorn --workers N`, Dict in-memory **không chia sẻ** giữa các workers — Redis giải quyết hoàn toàn.

---

## 9. Phụ thuộc & Không thay đổi

- **Không thay đổi**: LangGraph workflow, RAG pipeline, schema `/chat` endpoint
- **Phụ thuộc**: `generation/llm_model.py` → `get_llm()` (tái dụng model đã có)
- **Phụ thuộc**: `src/api/services/chat_service.py` → `_build_transcript_index()` (tái dụng hàm đọc transcript)
