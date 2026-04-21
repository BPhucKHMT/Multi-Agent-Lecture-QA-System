# Combine OCR Content vào Chunks
# Đã hoàn thành ( 12/04/2026 )

> Thiết kế chi tiết cho việc gắn OCR text (từ slide bài giảng) vào metadata của chunks, phục vụ mở rộng retrieval.

---

## 📌 Mục tiêu

Gắn nội dung OCR từ `artifacts/data_extraction/OCR/ocr_output_final/` vào metadata của chunks trong `artifacts/chunks/`, dựa trên `video_id` + timestamp range. Đồng thời xử lý trùng lặp (dedup) nội dung OCR từ các frame liên tiếp cùng slide.

---

## 🏗️ Kiến trúc tổng quan

```
OCR Files (per video_title)        Chunks (per playlist)
artifacts/data_extraction/OCR/     artifacts/chunks/
  ocr_output_final/                  cs315-máy-học-nâng-cao/
    CS315/                             semantic_chunks.json
      [CS315 - ...].json
                    │                           │
                    ▼                           ▼
              ┌──────────────────────────────────────┐
              │  src/data_pipeline/combine_content.py│
              │  1. Load OCR + Chunks                 │
              │  2. Match video_id + timestamp        │
              │  3. Dedup OCR (similarity filtering)  │
              │  4. Gắn vào metadata.ocr_content      │
              │  5. Save chunks mới                   │
              └──────────────────────────────────────┘
                              │
                              ▼
                artifacts/chunks/cs315-.../semantic_chunks.json
                  (enriched with ocr_content in metadata)
```

---

## 📊 Cấu trúc dữ liệu

### OCR Input (per file)

```json
{
    "playlist": "CS315",
    "keyframe_id": "007470",
    "image_path": "/kaggle/working/Keyframes/CS315/...",
    "ocr_text": "Khái niệm tensor\nTensor 0 chiều\nScalar\n...",
    "video_title": "[CS315 - Chương 0] Giới thiệu môn học (Phần 2)",
    "video_id": "_HLKpylxwMw",
    "url": "https://www.youtube.com/watch?v=_HLKpylxwMw",
    "timestamp": "0:02:04",
    "timestamp_seconds": 124.5
}
```

> **Lưu ý**: Một số file OCR cũ có `ocr_text` dạng JSON string lồng (`{"response": "..."}`) cần parse thêm.

### Chunk (trước khi combine)

```json
{
    "page_content": "Tiếp theo, chúng ta sẽ cùng...",
    "metadata": {
        "playlist": "PLb62OySGqC9xHEhxcX1BIX2H8oyvwOzCP",
        "video_url": "https://www.youtube.com/watch?v=_HLKpylxwMw",
        "filename": "_HLKpylxwMw",
        "title": "[CS315 - Chương 0] Giới thiệu môn học (Phần 2)",
        "start_timestamp": "0:00:14",
        "end_timestamp": "0:00:48",
        "chunk_id": 0
    }
}
```

### Chunk (sau khi combine)

```json
{
    "page_content": "Tiếp theo, chúng ta sẽ cùng...",
    "metadata": {
        "playlist": "PLb62OySGqC9xHEhxcX1BIX2H8oyvwOzCP",
        "video_url": "https://www.youtube.com/watch?v=_HLKpylxwMw",
        "filename": "_HLKpylxwMw",
        "title": "[CS315 - Chương 0] Giới thiệu môn học (Phần 2)",
        "start_timestamp": "0:00:14",
        "end_timestamp": "0:00:48",
        "chunk_id": 0,
        "ocr_content": "Ôn tập Đại số tuyến tính\nTS. Nguyễn Vinh Tiệp\nGiảng viên Khoa Khoa học Máy tính"
    }
}
```

> `page_content` **KHÔNG thay đổi** — giữ nguyên transcript sạch cho embedding.

---

## 🔗 Logic matching: OCR → Chunk

### Bước 1: Match video_id

- **Chunk** có `metadata.filename` = `"_HLKpylxwMw"` (chính là `video_id`)
- **OCR** có `video_id` = `"_HLKpylxwMw"`
- Match bằng exact string comparison

### Bước 2: Match timestamp range

Chunk có `start_timestamp` và `end_timestamp` (format `H:MM:SS`).
OCR có `timestamp_seconds`.

```python
def timestamp_to_seconds(ts: str) -> float:
    """Chuyển 'H:MM:SS' hoặc 'MM:SS' sang seconds."""
    parts = list(map(int, ts.split(':')))
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return 0
```

OCR frame thuộc chunk nếu:
```
chunk.start_seconds <= ocr.timestamp_seconds <= chunk.end_seconds
```

### Mapping tên thư mục OCR ↔ Chunks

| OCR folder | Chunks folder |
|-----------|---------------|
| `CS114/` | `cs114-máy-học/` |
| `CS116/` | `cs116-lập-trình-python-cho-máy-học/` |
| `CS315/` | `cs315-máy-học-nâng-cao/` |
| `CS431/` | `cs431-các-kĩ-thuật-học-sâu-và-ứng-dụng/` |

> Mapping này cần hardcode hoặc dùng metadata.json của mỗi playlist để xác định.

---

## 🧹 Dedup OCR

### Vấn đề

Nhiều keyframe liên tiếp chụp cùng 1 slide → OCR text gần giống hoặc giống hệt.

Ví dụ thực tế (video `_HLKpylxwMw`, timestamps 0:00:24 → 0:01:21):
```
Frame 001442: "Ôn tập Đại số tuyến tính"
Frame 001871: "Ôn tập Đại số tuyến tính"
Frame 002300: "Ôn tập Đại số tuyến tính"
Frame 002728: "Ôn tập Đại số tuyến tính"
Frame 003157: "Ôn tập Đại số tuyến tính"
Frame 003586: "Ôn tập Đại số tuyến tính"
Frame 004014: "Ôn tập Đại số tuyến tính"
Frame 004443: "Ôn tập Đại số tuyến tính"
Frame 004872: "tập Đại số tuyến tính"     ← near-duplicate (bị cắt)
```

### Thuật toán dedup

```python
from difflib import SequenceMatcher

# Các pattern cần loại bỏ (footer, watermark)
NOISE_PATTERNS = [
    "Trường Đại học Công nghệ Thông tin",
    "ĐHQG-HCM",
    "đhqg-hcm",
]

SIMILARITY_THRESHOLD = 0.85  # >= 85% giống → coi là duplicate
MIN_OCR_LENGTH = 10          # OCR text < 10 ký tự → bỏ

def clean_ocr_text(text: str) -> str:
    """Loại bỏ noise patterns và normalize."""
    for pattern in NOISE_PATTERNS:
        text = text.replace(pattern, "")
    # Loại bỏ dòng trống thừa
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)

def parse_ocr_text(raw_text: str) -> str:
    """Parse OCR text, xử lý trường hợp JSON string lồng."""
    import json
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict) and "response" in parsed:
            return parsed["response"]
    except (json.JSONDecodeError, TypeError):
        pass
    return raw_text

def dedup_ocr_frames(frames: list) -> list[str]:
    """
    Dedup các OCR frames đã sort theo timestamp.
    Trả về danh sách OCR text unique.
    """
    if not frames:
        return []

    unique_texts = []
    last_kept = ""

    for frame in frames:
        text = parse_ocr_text(frame["ocr_text"])
        text = clean_ocr_text(text)

        # Bỏ text quá ngắn
        if len(text) < MIN_OCR_LENGTH:
            continue

        # So sánh similarity với text cuối cùng đã giữ
        if last_kept:
            ratio = SequenceMatcher(None, last_kept, text).ratio()
            if ratio >= SIMILARITY_THRESHOLD:
                continue  # duplicate, bỏ qua

        unique_texts.append(text)
        last_kept = text

    return unique_texts
```

### Gộp kết quả

Các OCR text unique được nối bằng `\n---\n` để phân tách rõ ràng các slide khác nhau:

```python
ocr_content = "\n---\n".join(unique_texts)
```

---

## 📂 File mới: `src/data_pipeline/combine_content.py`

### Pseudocode

```python
"""
Gắn OCR content vào metadata của semantic chunks.

Cách dùng:
    python -m src.data_pipeline.combine_content
    python -m src.data_pipeline.combine_content --playlist CS315
    python -m src.data_pipeline.combine_content --dry-run
"""

def build_ocr_index(ocr_dir: str) -> dict:
    """
    Đọc tất cả file OCR trong 1 thư mục playlist.
    Trả về dict: {video_id: [list of OCR frames sorted by timestamp]}
    """
    # 1. Đọc tất cả file JSON trong ocr_dir
    # 2. Gộp vào dict theo video_id
    # 3. Sort mỗi list theo timestamp_seconds
    pass

def match_ocr_to_chunk(chunk: dict, ocr_frames: list) -> str:
    """
    Tìm các OCR frames nằm trong timestamp range của chunk.
    Dedup và trả về ocr_content string.
    """
    # 1. Parse start_timestamp, end_timestamp → seconds
    # 2. Filter frames: start_seconds <= frame.timestamp_seconds <= end_seconds
    # 3. Dedup (dedup_ocr_frames)
    # 4. Join thành string
    pass

def combine_for_playlist(playlist_ocr_dir: str, chunks_file: str, output_file: str):
    """
    Xử lý 1 playlist: load chunks + OCR, match, save.
    """
    # 1. Load chunks từ semantic_chunks.json
    # 2. Build OCR index
    # 3. Với mỗi chunk:
    #    a. Lấy video_id từ chunk.metadata.filename
    #    b. Lấy OCR frames cho video đó
    #    c. Match timestamp range → ocr_content
    #    d. Gắn vào chunk.metadata.ocr_content
    # 4. Save chunks mới
    pass

def main():
    """Entry point: xử lý tất cả hoặc 1 playlist."""
    pass
```

### Mapping thư mục

```python
PLAYLIST_MAPPING = {
    "CS114": "cs114-máy-học",
    "CS116": "cs116-lập-trình-python-cho-máy-học",
    "CS315": "cs315-máy-học-nâng-cao",
    "CS431": "cs431-các-kĩ-thuật-học-sâu-và-ứng-dụng",
}
```

---

## 🔍 Mở rộng Retrieval (Phase 2 — tùy chọn)

Sau khi OCR đã gắn vào metadata, mở rộng retrieval pipeline:

### Option A: Mở rộng BM25

Sửa `retriever/keyword_search.py` để khi xây dựng BM25 index, gộp thêm `metadata.ocr_content` vào text search:

```python
# Hiện tại BM25 chỉ index trên page_content
texts = [doc.page_content for doc in documents]

# Mở rộng: gộp page_content + ocr_content
texts = [
    doc.page_content + "\n" + doc.metadata.get("ocr_content", "")
    for doc in documents
]
```

### Option B: Retriever OCR riêng

Tạo thêm BM25 retriever chỉ search trên `ocr_content`, rồi gộp vào `EnsembleRetriever`:

```python
# src/retrieval/retrievers/hybrid_search.py
self.retriever = EnsembleRetriever(
    retrievers=[vector_retriever, keyword_retriever, ocr_retriever],
    weights=[0.4, 0.3, 0.3],
    k=40
)
```

### Option C: Enrich context cho LLM

Sửa `src/rag/offline_rag.py` → `format_doc()` để khi truyền context cho LLM, gắn thêm OCR content:

```python
def format_doc(self, docs):
    for doc in docs:
        ocr = doc.metadata.get("ocr_content", "")
        # Thêm OCR vào context nếu có
        formatted.append(f'{{"content": {content}, "slide_text": "{ocr}", ...}}')
```

> **Recommendation**: Bắt đầu với **Option A** (đơn giản nhất, ít thay đổi code).

---

## ✅ Checklist thực thi

- [x] Tạo file `src/data_pipeline/combine_content.py`
- [x] Implement `build_ocr_index()` — đọc & index OCR theo video_id
- [x] Implement `parse_ocr_text()` — xử lý cả JSON lồng và plain text
- [x] Implement `clean_ocr_text()` — strip noise patterns
- [x] Implement `dedup_ocr_frames()` — similarity-based dedup (advanced subset check)
- [x] Implement `match_ocr_to_chunk()` — timestamp range matching
- [x] Implement `combine_for_playlist()` — orchestrate toàn bộ
- [x] Test trên CS315 (xác nhận gộp 406/466 chunks)
- [x] Chạy cho tất cả 4 playlists (CS114, CS116, CS315, CS431)
- [ ] (Phase 2) Mở rộng BM25 retriever để search trên ocr_content

---

## ⚠️ Lưu ý

1. **Không sửa `page_content`** — giữ nguyên transcript cho embedding/vector search
2. **Backup chunks trước khi chạy** — hoặc save ra file mới trước
3. **ChromaDB cần rebuild** nếu muốn OCR vào metadata của vector store (metadata trong ChromaDB là string, không hỗ trợ full-text search)
4. **OCR text format**: Một số file CS114 có `ocr_text` dạng `{"response": "..."}`, cần parse trước
5. **Timestamp edge case**: Một số chunk có `start_timestamp = None` → bỏ qua matching cho chunk đó
