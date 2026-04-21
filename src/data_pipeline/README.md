# 🧠 Data Pipeline Module

Module này chịu trách nhiệm thu thập, xử lý và làm giàu dữ liệu từ YouTube để nạp vào hệ thống RAG. Nó kết hợp cả thông tin âm thanh (Transcript) và hình ảnh (OCR từ Slide bài giảng).

## 🏗️ Kiến trúc Workflow (8 Steps)

Hệ thống hoạt động theo mô hình Parallel-then-Merge (Song song sau đó Gộp):

```
Luồng A: Transcript
Step 1: Crawl Metadata/Transcript (coordinator.py)
Step 2: Preprocess & Spelling Fix (preprocess.py)
Step 3: Semantic Chunking (file_loader.py)
          │
          ▼
Step 7: Combine Content (combine_content.py) ◄── Step 6: OCR Keyframes (ocr_processor.py)
          │                                        ▲
          ▼                                        │
Step 8: Index to Vector DB (pipeline.py)      Step 5: Scene & Keyframe (scene_detector.py)
                                                   ▲
                                                   │
                                              Step 4: Download Video (video_downloader.py)
                                              Luồng B: Visual (Visual Extraction)
```

## 📂 Thành phần module

- **`data_loader/pipeline.py`**: Entry point chính. Điều phối toàn bộ 8 bước.
- **`data_loader/coordinator.py`**: Quản lý YouTube API, lấy playlist info và transcript (API/Whisper).
- **`data_loader/video_downloader.py`**: Tải video (yt-dlp) và lấy thông số kỹ thuật (với OpenCV).
- **`data_loader/scene_detector.py`**: Sử dụng AI (TransNetV2) để phát hiện các đoạn chuyển cảnh slide.
- **`data_loader/keyframe_extractor.py`**: Trích xuất các khung hình đại diện từ mỗi cảnh quay.
- **`data_loader/ocr_processor.py`**: Sử dụng EasyOCR để đọc chữ trên slide và gán timestamp.
- **`combine_content.py`**: Thuật toán logic để gộp thông tin OCR vào metadata của từng đoạn transcript.
- **`data_loader/pipeline_state.py`**: Quản lý tiến độ (Status) và sao lưu dữ liệu (Backup).
- **`data_loader/utils.py`**: Tiện ích quản lý đường dẫn động và config.

## 🚀 Hướng dẫn vận hành

### 1. Cấu hình
Mở file `config.yaml` ở root project để thêm playlist:
```yaml
playlists:
  - url: "https://www.youtube.com/playlist?list=..."
    enabled: true
```

### 2. Chạy Pipeline
Mọi lệnh đều được thực hiện thông qua module `pipeline`:

```bash
# Chạy toàn bộ 8 bước cho tất cả playlist đã enable
python -m src.data_pipeline.data_loader.pipeline

# Chỉ chạy cho 1 playlist cụ thể (folder name)
python -m src.data_pipeline.data_loader.pipeline --playlist "cs114-may-hoc"

# Bỏ qua phần tải và xử lý video (chỉ lấy transcript)
python -m src.data_pipeline.data_loader.pipeline --skip-visual

# Xem trạng thái tiến độ của các playlist
python -m src.data_pipeline.data_loader.pipeline --status
```

## 🛡️ Cơ chế an toàn (Safety)

- **Backup**: Trước khi thay đổi các file quan trọng (như Index hay Chunks), hệ thống sẽ tạo một bản sao tại `artifacts/backups/`.
- **State Management**: Nếu pipeline bị ngắt quãng (mất điện, lỗi mạng), bạn có thể kiểm tra `--status` để biết chính xác bước nào đã xong và chạy tiếp từ đó.
- **Dynamic Paths**: Mọi dữ liệu được lưu trữ cách ly theo tên playlist trong thư mục `artifacts/`, đảm bảo không bị ghi đè lẫn nhau.

## ⚠️ Lưu ý kỹ thuật

- **GPU Acceleration**: Các bước OCR (Step 6) và Scene Detection (Step 5) sẽ tự động sử dụng CUDA nếu có GPU. Nếu chạy trên CPU, thời gian xử lý sẽ lâu hơn khoảng 5-10 lần.
- **YouTube Blocking**: Nếu bị YouTube chặn IP (thường xảy ra ở Step 1 hoặc Step 4), hệ thống sẽ ghi log và tạm dừng. Bạn nên sử dụng Proxy hoặc chờ 24h trước khi chạy lại.
