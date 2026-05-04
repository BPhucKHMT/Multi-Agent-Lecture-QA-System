# Fix streaming `/chat/stream` part 2: token realtime, JSON parse, Markdown/Math/Citation

## 1) Triệu chứng hiện tại

- Trên giao diện, câu trả lời không chạy chữ theo thời gian thực.
- UI giữ trạng thái loading/status một thời gian dài, sau đó mới hiện toàn bộ câu trả lời một lần.
- Một số lượt hỏi trả về lỗi: `Không parse được JSON.`
- Cần kiểm tra lại việc render Markdown, công thức LaTeX/KaTeX, và citation dạng `[0]`, `[1]` khi streaming.

## 2) Phạm vi code liên quan

- Backend FastAPI đang chạy từ `backend/`:
  - `backend/app/api/v1/endpoints/chat.py`
  - `backend/app/services/chat.py`
- Backend legacy/local API vẫn còn logic tương tự:
  - `src/api/router.py`
  - `src/api/services/chat_service.py`
- RAG/Tutor sinh câu trả lời:
  - `src/rag_core/offline_rag.py`
  - `src/rag_core/agents/tutor.py`
- Frontend nhận SSE và render:
  - `frontend/src/lib/api/chat.ts`
  - `frontend/src/store/conversationStore.ts`
  - `frontend/src/components/chat/MessageList.tsx`
  - `frontend/src/components/chat/MarkdownRenderer.tsx`
  - `frontend/src/lib/utils/citation.ts`

## 3) Root cause chính: backend đang bỏ qua stream của final JSON answer

Trong `src/rag_core/offline_rag.py`, Tutor answer chain đang gắn tag:

```python
return self.prompt.partial(
    format_instructions=parser.get_format_instructions()
) | self.llm.with_config(tags=["final_answer_json"])
```

Nhưng `backend/app/services/chat.py` lại bỏ qua mọi token có tag `final_answer_json`:

```python
if "internal_query" in tags or "final_answer_json" in tags:
    continue
```

`src/api/services/chat_service.py` cũng có logic tương tự:

```python
if "final_answer_json" in tags:
    continue
```

Kết quả:

- LLM vẫn có thể stream token nội bộ.
- Backend chủ động không emit SSE `type=token` cho Tutor/Math/Quiz JSON answer.
- Frontend chỉ nhận `metadata` cuối stream, nên message được set bằng `metadata.text` một lần ở cuối.

Đây là nguyên nhân trực tiếp giải thích triệu chứng "đợi load xong rồi mới hiện ra".

## 4) Root cause phụ: `Không parse được JSON.`

Trong `src/rag_core/agents/tutor.py`, `node_tutor` gọi:

```python
rag_result = await answer_chain.ainvoke(...)
raw_content = rag_result.content if hasattr(rag_result, "content") else str(rag_result)
repaired = _extract_tutor_json_payload(raw_content)
```

Nếu `_extract_tutor_json_payload` không parse được JSON, node trả:

```python
"Không parse được JSON."
```

Các rủi ro hiện tại:

- `Offline_RAG.get_answer_chain()` tạo `JsonOutputParser`, nhưng chain thực tế chưa pipe qua parser; nó chỉ dùng `format_instructions` trong prompt.
- Prompt yêu cầu `text` chứa Markdown và LaTeX bên trong JSON string. LaTeX có nhiều dấu `\`, nếu LLM không escape đúng JSON (`\\theta`, `\\frac`, ...), `json.loads` dễ fail.
- LLM có thể trả thêm prefix/suffix, fenced block, hoặc JSON thiếu dấu đóng khi output dài.
- Khi parse fail, frontend vẫn nhận metadata cuối nhưng nội dung là lỗi, không có khả năng recover từ token đã stream.

## 5) Đánh giá Markdown, công thức, citation khi streaming

### Markdown

Frontend đã dùng `react-markdown` + `remark-gfm`, và có xử lý auto-close code fence/bold tạm thời khi đang stream:

- File: `frontend/src/components/chat/MarkdownRenderer.tsx`
- Cơ chế này ổn cho Markdown thường và code block đang stream dở.

Rủi ro còn lại:

- Nếu backend stream JSON thô thay vì chỉ stream nội dung `text`, Markdown sẽ vỡ.
- Nếu token bị cleaner giữ lại quá lâu do parse JSON fragment chưa đủ, UI vẫn có cảm giác không realtime.

### Công thức LaTeX/KaTeX

Frontend đã dùng:

- `remark-math`
- `rehype-katex`

Và có auto-close `$` nếu số delimiter lẻ.

Điểm ổn:

- Inline math `$...$` và block math `$$...$$` có cơ chế render.
- Streaming dở công thức ít bị crash hơn nhờ auto-close `$`.

Rủi ro còn lại:

- Prompt yêu cầu LaTeX nằm trong JSON string, nên lỗi escape JSON có thể xảy ra trước khi frontend được render.
- Nếu model sinh `\[...\]` thay vì `$...$` hoặc `$$...$$`, renderer hiện tại không đảm bảo render đúng.

### Citation `[0]`, `[1]`

Frontend có 2 đường build citation:

- Sau metadata cuối: `buildCitationItems(content, response)`
- Trong lúc stream: `buildCitationItemsFromContext(content, tempContext)`

Điểm ổn:

- Sau khi metadata tới, citation `[0]`, `[1]` có thể được map sang `response.video_url[index]`.
- Link có timestamp nếu `start_timestamp` parse được.

Rủi ro hiện tại:

- Backend gần như chưa gửi `context` sớm cho frontend, vì `_extract_stream_context()` đang tìm list object có key `page_content`, trong khi `Offline_RAG.format_doc()` trả JSON string với key `content`, `video_url`, `title`, `start_timestamp`, ...
- `Offline_RAG.get_context()` trả về string JSON, không phải list docs/raw object; event `retrieve_context` cũng cần kiểm chứng lại có đúng tên hay không.
- Khi đang stream, citation có thể chỉ hiện plain `[0]` cho tới khi metadata cuối về.
- `MarkdownRenderer` có nhánh xử lý link `cite:` nhưng `processedContent` hiện đang thay `[n]` thành link URL trực tiếp, nên nhánh `cite:` gần như không được dùng.

## 6) Hướng fix đề xuất

### Option A - Stream text từ JSON answer bằng cleaner hiện có

Ý tưởng:

- Không skip toàn bộ `final_answer_json`.
- Cho phép stream token từ node answer chính.
- Dùng `JsonStreamCleaner` để chỉ emit phần value của key `"text"` hoặc `"content"`.
- Vẫn skip `internal_query`.
- Vẫn gửi metadata cuối để cập nhật `response`, `video_url`, `title`, timestamp, confidence.

Ưu điểm:

- Ít thay đổi kiến trúc.
- Giữ contract frontend hiện tại: `token`, `context`, `metadata`, `[DONE]`.

Rủi ro:

- Cleaner phải đủ chắc với JSON escaped string, LaTeX, newline, markdown fence.
- Math/Quiz có schema khác; cần chỉ stream text phù hợp, hoặc chấp nhận chỉ metadata cho Quiz nếu UI cần component hoàn chỉnh.

### Option B - Tách final answer thành text stream + metadata parse sau

Ý tưởng:

- LLM sinh câu trả lời Markdown thuần để stream realtime.
- Sau đó tạo metadata/citation bằng bước structured output riêng hoặc post-process từ context.

Ưu điểm:

- Streaming tự nhiên hơn, ít phụ thuộc JSON string escaping.
- Markdown/LaTeX ít bị JSON phá.

Rủi ro:

- Cần thay đổi RAG contract nhiều hơn.
- Phải đảm bảo citation `[0]` khớp metadata.

### Option C - Dùng structured output/parser thật cho final metadata

Ý tưởng:

- `get_answer_chain()` nên pipe parser hoặc dùng structured output để giảm lỗi JSON.
- Nếu vẫn cần stream, stream token raw từ LLM nhưng parse final output bằng parser/fallback ở cuối.

Ưu điểm:

- Giảm lỗi `Không parse được JSON.`

Rủi ro:

- Parser thường chỉ có kết quả cuối, không tự giải quyết realtime token nếu backend vẫn skip `final_answer_json`.

## 7) Checklist triển khai

- [x] Xác định endpoint chạy chính là `backend/app/services/chat.py` hay `src/api/services/chat_service.py` trong môi trường hiện tại.
  - Kết quả: frontend đang gọi `/api/v1/chat/stream`, endpoint chính là `backend/app/services/chat.py`; vẫn cập nhật song song `src/api/services/chat_service.py` để giữ legacy/local API đồng bộ.
- [x] Sửa backend stream filter:
  - [x] Không skip toàn bộ `final_answer_json`.
  - [x] Vẫn skip `internal_query`.
  - [x] Chỉ emit token đã được `JsonStreamCleaner` bóc từ key `"text"`/`"content"`.
- [x] Harden `JsonStreamCleaner`:
  - [x] Không emit JSON structural token.
  - [x] Giữ Markdown newline, bullet, code fence.
  - [x] Không làm hỏng LaTeX escape như `\\theta`, `\\frac`, `_`, `{}`.
  - [x] Không swallow token quá lâu khi text đang stream hợp lệ.
  - Kết quả bổ sung: thay cơ chế `json.loads` trên toàn bộ chuỗi dở bằng decoder từng ký tự cho JSON string value, nên token có thể nhả ngay khi đọc được phần `"text"` thay vì đợi object hoàn chỉnh.
- [ ] Giảm lỗi JSON parse cuối:
  - [ ] Pipe `JsonOutputParser` hoặc dùng structured output cho `TutorOutput`.
  - [ ] Thêm repair fallback cho JSON lỗi escape LaTeX phổ biến.
  - [ ] Log `raw_content` preview khi parse fail để debug.
- [x] Sửa context/citation streaming:
  - [ ] Đảm bảo backend emit `type=context` ngay sau retrieval.
  - [x] Chuẩn hóa metadata cuối để frontend dùng được: `video_url`, `title`, `filename`, `start_timestamp`, `end_timestamp`, `content`.
  - [ ] Cho `buildCitationItemsFromContext()` đọc đúng `start_timestamp`/`end_timestamp`.
  - Kết quả bổ sung: `node_tutor` backfill metadata bị thiếu cho các citation `[n]` từ context retrieval, tránh card `[3]`, `[4]`, ... rơi về tiêu đề/timestamp mặc định khi LLM cite nhiều index hơn metadata trả về.
- [ ] Kiểm tra frontend render:
  - [x] Markdown thường stream dần không vỡ layout.
  - [x] Loading/status không biến mất khi token đầu chỉ là whitespace/newline.
  - [ ] Code block đang stream dở không phá UI.
  - [ ] Inline math `$...$` render ổn.
  - [ ] Block math `$$...$$` render ổn.
  - [ ] Citation `[0]`, `[1]` clickable trong lúc stream nếu đã có context.
  - [ ] Citation vẫn đúng sau metadata cuối.

## 8) Test checklist đề xuất

- [x] Unit test backend SSE: event `final_answer_json` có JSON token từng phần vẫn emit `type=token` chỉ chứa text.
- [ ] Unit test backend SSE: `internal_query` không bị stream ra UI.
- [ ] Unit test cleaner: Markdown có newline/bullet/code fence được giữ nguyên.
- [x] Unit test cleaner: LaTeX trong JSON string không làm mất token.
- [x] Unit test citation: metadata thiếu được backfill theo citation index từ context.
- [ ] Unit test parser: Tutor output có fenced JSON/prefix vẫn parse được.
- [ ] Integration/manual:
  - [ ] Hỏi câu RAG dài, UI hiện chữ dần trước metadata.
  - [ ] Hỏi câu có công thức, KaTeX render sau từng phần stream và sau metadata.
  - [ ] Hỏi câu có citation, `[0]`, `[1]` khớp URL/timestamp.
  - [ ] Không còn hiện `Không parse được JSON.` với câu hỏi RAG phổ biến.

## 9) Kết luận hiện trạng

- Vấn đề "không streaming chữ" đã được xử lý ở stream filter: backend không còn skip toàn bộ `final_answer_json`, mà bóc riêng nội dung `text` qua `JsonStreamCleaner`.
- Vấn đề delay dài vẫn còn một phần sau fix đầu tiên vì cleaner chờ `json.loads` parse được JSON string đang dở; đã đổi sang decoder từng ký tự để nhả token sớm.
- Markdown renderer frontend tương đối ổn, backend hiện chỉ stream text sạch từ field `"text"`/`"content"`.
- Công thức LaTeX/KaTeX frontend có nền tảng ổn, nhưng JSON escaping ở backend/LLM là điểm rủi ro lớn.
- Citation sau metadata cuối đã được cải thiện bằng backfill từ context theo index `[n]`; citation trong lúc streaming vẫn chưa hoàn chỉnh vì context event sớm chưa chắc được emit đúng shape.

## 10) Nhật ký thay đổi

- **2026-04-27**: Tạo tài liệu phân tích part 2 cho lỗi streaming không realtime, lỗi parse JSON, và đánh giá Markdown/Math/Citation.
- **2026-04-27**: Sửa stream filter trong `backend/app/services/chat.py` và `src/api/services/chat_service.py` để cho phép stream `final_answer_json`; thêm regression test trong `tests/api/test_chat_stream.py`; xác minh bằng reproduction script cho cả backend chính và legacy service.
- **2026-04-27**: Sửa tiếp delay streaming bằng decoder từng ký tự trong `JsonStreamCleaner`; thêm backfill citation metadata từ context trong `src/rag_core/agents/tutor.py`; bổ sung regression test cho citation metadata thiếu.
- **2026-04-27**: Sửa frontend `conversationStore` để chỉ tắt loading khi token stream đầu tiên có ký tự hiển thị; tránh trạng thái loading biến mất nhưng bubble chưa có chữ khi backend gửi whitespace/newline đầu stream.
