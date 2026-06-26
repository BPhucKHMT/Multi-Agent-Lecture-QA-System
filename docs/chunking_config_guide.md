# Chunking Configuration Guide

## Overview

Production pipeline hỗ trợ nhiều chunking strategies. Strategy được chọn thông qua biến môi trường `CHUNK_STRATEGY`.

## Setup

1. Copy `.env.example` sang `.env` (nếu chưa có):
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` và đặt `CHUNK_STRATEGY` thành một trong các giá trị sau:
   ```
   CHUNK_STRATEGY=recursive
   CHUNK_STRATEGY=timestamp_150_50
   CHUNK_STRATEGY=timestamp_90_30
   CHUNK_STRATEGY=semantic
   CHUNK_STRATEGY=parent_child_180s_45s
   ```

   Cho semantic, có thể cấu hình thêm:
   ```
   SEMANTIC_EMBEDDING_PROVIDER=openai  # hoặc "bge"
   ```

## Available Strategies

| Strategy | Description | Requirements |
|----------|-------------|--------------|
| `recursive` | RecursiveCharacterTextSplitter (700 chars, 100 overlap) | None (baseline) |
| `timestamp_150_50` | Sliding window 150 giây, overlap 50 giây | None |
| `timestamp_90_30` | Sliding window 90 giây, overlap 30 giây | None |
| `semantic` | Semantic boundary detection dựa trên embedding similarity | **Required:** `langchain-openai` + OpenAI API key (dùng `text-embedding-3-large`) **hoặc** `langchain-huggingface` + fine-tuned BGE-M3 model tại `experiments/runs/finetune/embedding/20260616-120132` |
| `parent_child_180s_45s` | *(Not implemented)* Hierarchical: parent 180s + child 45s | - |

**Note:** Nếu dependencies cho `semantic` không đầy đủ, hệ thống sẽ tự động fallback về `recursive` và in warning.

## Output

Tất cả strategies đều ghi ra file `semantic_chunks.json` (tên file giữ nguyên để backward compatible). Metadata mỗi chunk chứa trường `chunk_strategy` để xác định strategy đã dùng.

### Metadata fields

- **Common**: `playlist`, `video_url`, `filename`, `title`, `chunk_id`, `start_timestamp`, `end_timestamp`
- **Recursive**: `chunk_strategy="recursive"`
- **Timestamp**: `chunk_strategy="timestamp_150_50"`, `window_seconds`, `overlap_seconds`, `start_seconds`, `end_seconds`
- **Semantic**: `chunk_strategy="semantic"`

## Running Pipeline

```bash
# Set strategy (ví dụ: timestamp_150_50)
export CHUNK_STRATEGY=timestamp_150_50

# Run chunking
python -m src.data_pipeline.data_loader.file_loader

# Hoặc chạy full pipeline
python -m src.data_pipeline.data_loader.pipeline
```

## Development

Thêm strategy mới:

1. Tạo class mới kế thừa `BaseChunker` trong `src/retrieval/text_splitters/chunker.py`
2. Implement method `chunk(self, documents, output_dir) -> List[dict]`
3. Thêm logic trong `TranscriptChunker.__init__()` để xử lý strategy mới
4. Test với `test_chunker.py`

## Installation for Semantic Chunker

Để dùng strategy `semantic`, cần cài đặt thêm:

```bash
# For OpenAI embeddings
pip install langchain-openai

# For BGE-M3 (fine-tuned)
pip install langchain-huggingface
# Model sẽ được tự động tải từ experiments/runs/finetune/embedding/20260616-120132
```

## Notes

- Pipeline vẫn đọc `semantic_chunks.json` không cần thay đổi code khác.
- Nếu strategy không tồn tại, hệ thống sẽ fallback về `recursive` và in warning.
- Config `CHUNK_STRATEGY` đọc từ biến môi trường, có thể set trực tiếp hoặc qua `.env`.
