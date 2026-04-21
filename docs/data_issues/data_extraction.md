# Data Extraction Pipeline — Tích hợp vào `data_loader/`
# Đã hoàn thành ( 12/04/2026 )

> Mở rộng `data_loader/pipeline.py` hiện tại thành pipeline end-to-end: 2 luồng song song (transcript + visual) merge tại bước cuối, tạo ra chunks hoàn chỉnh gồm cả OCR content.

---

## 📌 Bối cảnh

### Hiện tại: `DataPipeline` có 3 steps

```
Crawl transcript ──► Preprocess transcript ──► Chunk + Index
```

### Mục tiêu: Mở rộng thành 2 luồng song song

```
 ┌─── Luồng Transcript ──────────────────────────────────────┐
 │ Step 1: Crawl ──► Step 2: Preprocess ──► Step 3: Chunk    │
 └───────────────────────────────────────────────┬────────────┘
                                                 │
                                            Step 7: Combine ──► Step 8: Index
                                                 │
 ┌─── Luồng Visual ─────────────────────────────┬────────────┐
 │ Step 4: Download ──► Step 5: Scene+Keyframe ──► Step 6: OCR│
 └────────────────────────────────────────────────────────────┘
```

- **Hai luồng chạy độc lập**, không phụ thuộc nhau
- **Merge tại Step 7** (Combine): ghép OCR vào metadata của chunks
- **Step 8** (Index): đưa chunks hoàn chỉnh vào Vector DB

---

## 📂 Cấu trúc file — mở rộng `data_loader/`

```
data_loader/
├── pipeline.py              # [MODIFY] Mở rộng DataPipeline, thêm luồng visual
├── coordinator.py           # [EXISTING] YouTube playlist crawl
├── youtube_fetchers.py      # [EXISTING] Transcript fetch (API + Whisper)
├── preprocess.py            # [EXISTING] Transcript spelling
├── file_loader.py           # [EXISTING] Load + chunk transcripts
│
├── video_downloader.py      # [NEW] Step 4 — Download video (yt-dlp)
├── scene_detector.py        # [NEW] Step 5a — TransNetV2 scene detection
├── keyframe_extractor.py    # [NEW] Step 5b — Extract keyframes từ scenes
├── ocr_processor.py         # [NEW] Step 6 — OCR + preprocess
├── combine_content.py       # [NEW] Step 7 — Merge OCR vào chunk metadata
└── pipeline_state.py        # [NEW] State tracking + backup
```

> **Notebooks giữ nguyên** trong `data_extraction/` để tham khảo. Code production là `.py` trong `data_loader/`.

---

## 🔗 Mapping thư mục (Dynamic qua `config.yaml`)

Thay vì hardcode `COURSE_MAPPING`, hệ thống sẽ tự động quét `config.yaml` để lấy danh sách các playlist có `enabled: true`.
Đường dẫn của từng playlist sẽ được **tự động sinh ra (dynamic generation)** dựa trên tên của playlist (lấy qua API của YouTube).

Ví dụ quy tắc sinh tự động trong `pipeline.py`:

```python
# Mẫu hàm lấy đường dẫn động trong pipeline.py
def get_playlist_paths(folder_name: str) -> dict:
    """
    folder_name: tên viết thường có gạch nối (VD: 'cs114-máy-học')
    được tạo từ ConfigBasedCoordinator / PlaylistMetadataFetch.
    """
    return {
        "videos_dir": f"artifacts/videos/{folder_name}",
        "data_dir": f"artifacts/data/{folder_name}",
        "chunks_dir": f"artifacts/chunks/{folder_name}",
        "scene_dir": f"artifacts/data_extraction/SceneJSON/{folder_name}",
        "keyframes_dir": f"artifacts/data_extraction/Keyframes/{folder_name}",
        "ocr_dir": f"artifacts/data_extraction/OCR/ocr_output_final/{folder_name}"
    }
```

Bằng cách này, khi bạn dán URL bất kỳ playlist nào vào `config.yaml`, pipeline sẽ tự sinh đầy đủ các thư mục mà không cần phải định nghĩa code!

---

## 📋 Chi tiết từng module mới

### `video_downloader.py` — Step 4

Download video từ YouTube playlist bằng `yt-dlp`.

```python
class VideoDownloader:
    """Download videos từ YouTube playlist."""
    
    def download_playlist(self, playlist_url: str, output_dir: str) -> dict:
        """
        Download tất cả video trong playlist.
        Skip nếu file đã tồn tại.
        Return: {"completed": N, "skipped": N, "failed": N}
        """
        # Gọi yt-dlp via subprocess
        # Format: "{idx:02d} - {title}.{format_id}.mp4"
        # --download-archive downloaded.txt để track đã tải
        pass
    
    def get_video_fps(self, video_dir: str) -> dict:
        """
        Lấy FPS của tất cả video trong thư mục.
        Return: {video_path: fps}
        Lưu vào video_fps.json
        """
        # Dùng ffmpeg.probe() hoặc cv2
        pass
```

**Dependencies**: `yt-dlp` (subprocess), `ffmpeg-python` hoặc `opencv-python`

---

### `scene_detector.py` — Step 5a

Scene detection bằng TransNetV2.

```python
class SceneDetector:
    """Phát hiện scene boundaries bằng TransNetV2."""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Log device info
        
    def detect_scenes(self, video_path: str) -> list:
        """
        Detect scene boundaries cho 1 video.
        Return: [[start_frame, end_frame], ...]
        """
        pass
    
    def process_playlist(self, videos_dir: str, output_dir: str) -> dict:
        """
        Process tất cả video trong playlist.
        Skip nếu output JSON đã tồn tại.
        Save: {output_dir}/{video_id}.json
        """
        pass
```

**Dependencies**: `tensorflow` (TransNetV2), `torch` (GPU detection)

> **GPU**: Auto-detect CUDA. Nếu không có GPU → chạy CPU (chậm hơn ~5x, vẫn OK cho production).

---

### `keyframe_extractor.py` — Step 5b

Extract keyframes từ scene boundaries.

```python
class KeyframeExtractor:
    """Extract keyframes từ video dựa trên scene boundaries."""
    
    def sample_frames_from_shot(self, start_idx: int, end_idx: int) -> list[int]:
        """
        Adaptive sampling: 1 frame/30 frames, min 3, max 10.
        """
        pass
    
    def extract_keyframes(self, video_path: str, scenes: list, 
                          output_dir: str, fps: float) -> int:
        """
        Extract keyframes cho 1 video.
        Save: {output_dir}/{frame_idx:06d}.webp
        Return: số keyframes đã extract
        """
        pass
    
    def process_playlist(self, videos_dir: str, scene_dir: str,
                         output_dir: str, fps_data: dict) -> dict:
        """Process tất cả video trong playlist."""
        pass
```

**Dependencies**: `opencv-python`

---

### `ocr_processor.py` — Step 6

OCR trên keyframes + preprocess.

```python
class OCRProcessor:
    """OCR keyframes bằng EasyOCR + advanced cleaning."""
    
    def __init__(self):
        import easyocr
        self.reader = easyocr.Reader(['vi'], gpu=torch.cuda.is_available())
    
    def extract_ocr(self, img_path: str) -> str:
        """OCR 1 ảnh, return text (confidence > 0.5)."""
        pass
    
    def clean_ocr_text(self, text: str) -> str:
        """
        Advanced cleaning:
        - Strip UI noise (IDE, footer trường)
        - Remove file paths
        - Remove single-char/number-only lines
        - Fix common OCR mistakes
        """
        pass
    
    def add_metadata(self, ocr_data: list, metadata_path: str, 
                     fps_data: dict) -> list:
        """
        Enrich OCR data:
        - Thêm video_id, url từ metadata.json
        - Thêm timestamp từ keyframe_id / fps
        """
        pass
    
    def process_playlist(self, keyframes_dir: str, output_dir: str,
                         metadata_path: str, fps_data: dict) -> dict:
        """Process tất cả video trong playlist."""
        pass
```

**Dependencies**: `easyocr`, `torch` (GPU auto-detect)

---

### `combine_content.py` — Step 7

Merge OCR content vào chunk metadata. Chi tiết tại [docs/combine_content.md](combine_content.md).

```python
class ContentCombiner:
    """Ghép OCR text vào metadata của chunks."""
    
    SIMILARITY_THRESHOLD = 0.85
    MIN_OCR_LENGTH = 10
    NOISE_PATTERNS = [
        "Trường Đại học Công nghệ Thông tin",
        "ĐHQG-HCM",
    ]
    
    def dedup_ocr_frames(self, frames: list) -> list[str]:
        """Dedup OCR frames bằng SequenceMatcher."""
        pass
    
    def match_ocr_to_chunk(self, chunk: dict, ocr_frames: list) -> str:
        """Match OCR frames → chunk bằng video_id + timestamp range."""
        pass
    
    def combine_for_playlist(self, ocr_dir: str, chunks_file: str) -> int:
        """
        Combine OCR vào chunks cho 1 playlist.
        Return: số chunks đã enriched.
        """
        pass
```

**Dependencies**: `difflib` (built-in)

---

### `pipeline_state.py` — State tracking + Backup

```python
class PipelineState:
    """Track trạng thái pipeline + backup."""
    
    STATE_FILE = "data_loader/pipeline_state.json"
    BACKUP_DIR = "data_loader/backups/"
    
    def get_status(self, course: str, step: str) -> str:
        """Return: 'pending' | 'in_progress' | 'done' | 'failed'"""
        pass
    
    def set_status(self, course: str, step: str, status: str, **extra):
        """Update status + save state file."""
        pass
    
    def backup(self, step: str, target_paths: list[str]) -> str:
        """Backup target dirs trước khi chạy step. Return backup path."""
        pass
    
    def print_status(self):
        """In bảng trạng thái tất cả playlists."""
        pass
```

---

## 🔄 Mở rộng `DataPipeline` trong `pipeline.py`

```python
class DataPipeline:
    """Pipeline tự động: Transcript + Visual → Combine → Index"""
    
    def __init__(self):
        # ... existing init ...
        self.state = PipelineState()
    
    # ──── Luồng Transcript (existing, đổi tên) ────
    def step1_crawl_transcripts(self, playlist_url: str): ...
    def step2_preprocess_transcripts(self, folder_name: str): ...
    def step3_chunk_transcripts(self, folder_name: str): ...
    
    # ──── Luồng Visual (new) ────
    def step4_download_videos(self, playlist_url: str, folder_name: str): ...
    def step5_extract_visual(self, folder_name: str): ...  # Scene + Keyframes
    def step6_ocr_keyframes(self, folder_name: str): ...
    
    # ──── Merge + Index ────
    def step7_combine_content(self, folder_name: str): ...
    def step8_index_to_vectordb(self, folder_name: str): ...
    
    def run_full_pipeline(self, playlist_url: str, folder_name: str, skip_transcript=False, skip_visual=False):
        """
        Chạy toàn bộ pipeline cho một playlist.
        Hai luồng chạy tuần tự nhưng độc lập.
        """
        paths = get_playlist_paths(folder_name)
        
        # Luồng Transcript
        if not skip_transcript:
            self.step1_crawl_transcripts(playlist_url)
            self.step2_preprocess_transcripts(folder_name)
            self.step3_chunk_transcripts(folder_name)
        
        # Luồng Visual
        if not skip_visual:
            self.step4_download_videos(playlist_url, folder_name)
            self.step5_extract_visual(folder_name)
            self.step6_ocr_keyframes(folder_name)
        
        # Merge + Index
        self.step7_combine_content(folder_name)
        self.step8_index_to_vectordb(folder_name)
        
    def process_from_config(self):
        """
        Quét file config.yaml và chạy run_full_pipeline 
        cho tất cả các playlist có enabled: true.
        """
        config = load_config("config.yaml") # hoặc sử dụng ConfigBasedCoordinator
        for playlist in config["playlists"]:
            if playlist.get("enabled", True):
                # 1. Trích xuất playlist ID từ URL
                # 2. Gọi fetcher để lấy folder_name (VD: cs114-máy-học)
                # 3. run_full_pipeline(url, folder_name)
                pass
```

---

## 🖥️ CLI mở rộng

```bash
# Chạy full pipeline (cả 2 luồng)
python -m data_loader.pipeline

# Chỉ chạy luồng transcript (như hiện tại)
python -m data_loader.pipeline --skip-visual

# Chỉ chạy luồng visual
python -m data_loader.pipeline --skip-transcript --playlist CS315

# Chỉ combine + index (cả 2 luồng đã chạy trước đó)
python -m data_loader.pipeline --only-combine

# Chỉ chạy 1 step cụ thể
python -m data_loader.pipeline --only-step 6 --playlist CS315

# Xem trạng thái
python -m data_loader.pipeline --status

# Dry run
python -m data_loader.pipeline --dry-run

# Bỏ qua backup
python -m data_loader.pipeline --no-backup
```

### Arguments mới (thêm vào CLI hiện tại)

```python
# Visual pipeline controls
parser.add_argument("--skip-visual", action="store_true",
    help="Bỏ qua luồng visual (download/scene/keyframe/OCR)")
parser.add_argument("--skip-transcript", action="store_true",
    help="Bỏ qua luồng transcript (crawl/preprocess/chunk)")
parser.add_argument("--only-combine", action="store_true",
    help="Chỉ chạy combine + index")
parser.add_argument("--only-step", type=int, choices=range(1,9),
    help="Chỉ chạy 1 step cụ thể (1-8)")

# State & backup
parser.add_argument("--status", action="store_true",
    help="Xem trạng thái pipeline")
parser.add_argument("--no-backup", action="store_true",
    help="Bỏ qua backup trước khi chạy")
parser.add_argument("--dry-run", action="store_true",
    help="Chỉ in kế hoạch, không chạy")
```

---

## 💾 State & Backup

### State file: `data_loader/pipeline_state.json`

```json
{
  "last_updated": "2026-04-10T23:00:00",
  "playlists": {
    "CS315": {
      "step1_crawl":       {"status": "done", "timestamp": "..."},
      "step2_preprocess":  {"status": "done", "timestamp": "..."},
      "step3_chunk":       {"status": "done", "timestamp": "...", "total_chunks": 466},
      "step4_download":    {"status": "done", "timestamp": "...", "completed": 74},
      "step5_visual":      {"status": "done", "timestamp": "...", "total_keyframes": 5000},
      "step6_ocr":         {"status": "in_progress", "completed": 45, "remaining": 29},
      "step7_combine":     {"status": "pending"},
      "step8_index":       {"status": "pending"}
    }
  }
}
```

### Backup targets

| Step | Backup trước khi chạy |
|------|----------------------|
| Step 3 (chunk) | `chunks/{playlist}/semantic_chunks.json` |
| Step 5 (visual) | `data_extraction/SceneJSON/{course}/`, `Keyframes/{course}/` |
| Step 6 (OCR) | `data_extraction/OCR/ocr_output_final/{course}/` |
| Step 7 (combine) | `chunks/{playlist}/semantic_chunks.json` |

Format backup: `data_loader/backups/{step}_{timestamp}/`

---

## ⚙️ GPU Auto-Detection

```python
def detect_device():
    """Auto-detect GPU availability."""
    import torch
    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        print(f"🎮 GPU detected: {gpu_name}")
    else:
        device = "cpu"
        print("💻 No GPU detected, running on CPU (slower)")
    return device
```

Sử dụng trong `SceneDetector`, `OCRProcessor`:
- **GPU**: Tốc độ bình thường
- **CPU**: Chậm hơn ~5-10x nhưng vẫn chạy được, in warning ước tính thời gian

---

## 🔀 Flow thực tế

### Lần đầu chạy (chưa có gì)
```bash
python -m data_loader.pipeline --playlist CS315
# Chạy step 1→3 (transcript) rồi step 4→6 (visual) rồi step 7→8 (merge)
```

### Chỉ cần update OCR (thêm playlist mới)
```bash
python -m data_loader.pipeline --skip-transcript --playlist CS315
# Chỉ chạy step 4→6→7→8
```

### Đã có transcript + OCR, chỉ muốn combine lại
```bash
python -m data_loader.pipeline --only-combine --playlist CS315
# Chỉ chạy step 7→8
```

### Resume sau khi bị gián đoạn
```bash
python -m data_loader.pipeline --status
# Xem step nào đang in_progress, chạy lại từ đó
python -m data_loader.pipeline --only-step 6 --playlist CS315
```

---

## ✅ Checklist thực thi

### Phase 1: Infrastructure
- [x] Tạo `src/data_pipeline/data_loader/pipeline_state.py` — State + backup
- [x] Implement `get_playlist_paths()` sinh đường dẫn động dựa trên `folder_name`

### Phase 2: Visual modules
- [x] Tạo `data_loader/video_downloader.py` — yt-dlp wrapper
- [x] Tạo `data_loader/scene_detector.py` — TransNetV2 (từ notebook)
- [x] Tạo `data_loader/keyframe_extractor.py` — Frame extraction (từ notebook)
- [x] Tạo `data_loader/ocr_processor.py` — EasyOCR + preprocess (từ notebook)
- [x] Tạo `data_loader/combine_content.py` — OCR → chunk metadata

### Phase 3: Pipeline integration
- [x] Refactor `pipeline.py` — Thêm steps 4-8, mở rộng CLI
- [x] Tách step3 hiện tại thành step3 (chunk) + step8 (index)
- [x] Test end-to-end (Đã chạy verify cấu trúc thành công)
- [ ] Update `AGENTS.md` (Sẽ làm ở bước sau)

---

## ⚠️ Lưu ý

1. **Backward compatible**: `--skip-visual` giữ behavior y hệt pipeline cũ
2. **Notebooks giữ nguyên**: `data_extraction/*.ipynb` — chỉ để thí nghiệm
3. **Output giữ nguyên vị trí**: `data_extraction/Keyframes/`, `OCR/` vẫn ở chỗ cũ, modules mới đọc/ghi đúng path đó
4. **Dependencies nặng là optional**: `easyocr`, `tensorflow` chỉ import khi chạy steps cần nó → `--skip-visual` không cần cài
