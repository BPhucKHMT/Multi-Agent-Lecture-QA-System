# Kế hoạch nâng cấp Docker cho RAG QABot

Tài liệu này mô tả kế hoạch thiết kế lại Docker để phục vụ 2 mục tiêu chính:

1. **Local/demo chạy nhanh bằng GPU** trên máy cá nhân có CUDA.
2. **Deploy tiết kiệm bằng CPU** trên VPS/Render/Railway hoặc server không có GPU.

---

## 1. Quyết định thiết kế đã chốt

| Hạng mục | Quyết định |
|---|---|
| Local/dev/demo | Ưu tiên GPU để phản hồi nhanh và demo mượt |
| Deploy mặc định | CPU-only để giảm chi phí server và image nhẹ hơn |
| Docker strategy | Multi-target Dockerfile: `dev-gpu`, `prod-cpu`, optional `prod-gpu` |
| PyTorch CPU | Dùng wheel CPU chính thức, không kéo CUDA vào image deploy |
| PyTorch GPU | Dùng base image PyTorch CUDA có sẵn thay vì tự build CUDA stack |
| Frontend | Build tách riêng hoặc service riêng tùy compose profile |
| Runtime artifacts | Mount/persist `artifacts/`, không bake dữ liệu lớn vào image |
| Model cache | Mount HuggingFace cache volume để tránh download lại model |

> [!IMPORTANT]
> Không dùng một image CUDA nặng cho mọi môi trường. Local GPU và deploy CPU cần tách target rõ ràng để tránh image deploy quá nặng, build lâu, và tốn tài nguyên RAM/disk.

---

## 2. Bối cảnh hiện tại

Docker hiện tại còn tối giản và chưa đúng entrypoint backend:

| File | Hiện trạng |
|---|---|
| `Dockerfile` | Base `python:3.12.7`, cài toàn bộ `requirements.txt`, copy toàn project |
| `docker-compose.yaml` | Chạy `uvicorn server:app` và `streamlit run app.py` |
| `requirements.txt` | Có extra index CUDA 11.6 cho `torch/torchvision/torchaudio` |

Vấn đề chính:

1. Image deploy có thể kéo CUDA wheel dù server chỉ chạy CPU.
2. Chưa có target GPU local riêng.
3. Chưa có `.dockerignore` để giảm build context.
4. Chưa tách dependency CPU/GPU nên khó tối ưu kích thước image.
5. Compose hiện chạy entrypoint cũ, trong khi backend FastAPI chính là `src.api.server:app`.
6. Dữ liệu runtime/model cache chưa được khai báo volume rõ ràng.

---

## 3. Kết quả benchmark liên quan

### 3.1. Embedding `BAAI/bge-m3`

| Mode | Device | Load model | Avg/query |
|---|---:|---:|---:|
| GPU | `cuda:0` | `30.285s` | `0.0162s` |
| CPU | `cpu` | `20.15s` | `0.0615s` |

Embedding CPU đủ nhanh cho deploy nhỏ vì chỉ khoảng `~60ms/query`.

### 3.2. Reranker `BAAI/bge-reranker-base`

Benchmark 80 docs:

| Mode | Device | Avg rerank |
|---|---:|---:|
| GPU | `cuda` | `~0.18–0.20s` |
| CPU | `cpu` | `~1.9–2.0s` |

Reranker CPU chậm hơn GPU khoảng 10x, nhưng vẫn chấp nhận được cho deploy tiết kiệm nếu traffic thấp.

### 3.3. Số docs thực tế reranker nhận

| Luồng | Input reranker | Output reranker |
|---|---:|---:|
| Tutor/RAG chính | `<= 60 docs` | `<= 10 docs` |
| Quiz | `~40 docs` | `<= 5 docs` |
| Coding retrieval | `~40 docs` | mặc định `3 docs` |

> [!NOTE]
> Benchmark 80 docs là worst-case/proxy hơi cao hơn thực tế. Khi tối ưu CPU deploy nên benchmark lại với 40 và 60 docs.

---

## 4. Kiến trúc Docker đề xuất

### 4.1. Dockerfile multi-target

Đề xuất có các target:

| Target | Mục đích | Base image |
|---|---|---|
| `base` | Layer chung: env, workdir, system deps tối thiểu | `python:3.12-slim` |
| `prod-cpu` | Deploy CPU mặc định | `python:3.12-slim` + PyTorch CPU wheel |
| `dev-gpu` | Local/demo GPU | `pytorch/pytorch:<cuda-runtime>` |
| `prod-gpu` | Optional nếu sau này thuê server GPU | `pytorch/pytorch:<cuda-runtime>` |

Nguyên tắc:

- `prod-cpu` không cài CUDA wheel.
- `dev-gpu` dùng image có CUDA/PyTorch sẵn để tránh tự build torch.
- Cài dependency theo file riêng:
  - `requirements.base.txt`
  - `requirements.cpu.txt`
  - `requirements.gpu.txt`
- Copy dependency trước, source sau để tận dụng Docker layer cache.
- Không copy `.env`, `.git`, `.conda`, cache, database runtime vào image.

### 4.2. Docker Compose profiles

Đề xuất compose có profile:

| Profile | Service | Mục đích |
|---|---|---|
| `cpu` | backend CPU | Deploy/local CPU test |
| `gpu` | backend GPU | Local demo có NVIDIA runtime |
| `frontend` | React/Vite | Chạy UI dev nếu cần |
| `redis` | Redis Stack | Dùng cho semantic cache nếu bật |

Ví dụ usage dự kiến:

```powershell
# Local GPU demo
$env:COMPOSE_PROFILES="gpu,frontend,redis"
docker compose up --build

# Local test CPU gần giống deploy
$env:COMPOSE_PROFILES="cpu,redis"
docker compose up --build

# Deploy CPU
Docker build target: prod-cpu
Command: uvicorn src.api.server:app --host 0.0.0.0 --port 8000
```

---

## 5. Cấu hình runtime đề xuất

Thêm các biến môi trường để cùng một code chạy được CPU/GPU:

```env
RAG_DEVICE=auto
RAG_RETRIEVER_K=40
RAG_RETRIEVER_FETCH_K=80
RAG_RERANK_TOP_K=10
HF_HOME=/app/.cache/huggingface
TRANSFORMERS_CACHE=/app/.cache/huggingface
TOKENIZERS_PARALLELISM=false
```

Local GPU:

```env
RAG_DEVICE=cuda
RAG_RETRIEVER_K=40
RAG_RETRIEVER_FETCH_K=80
```

Deploy CPU tiết kiệm:

```env
RAG_DEVICE=cpu
RAG_RETRIEVER_K=20
RAG_RETRIEVER_FETCH_K=50
```

> [!WARNING]
> Nếu code vẫn hard-code `torch.cuda.is_available()` mà không đọc `RAG_DEVICE`, container CPU/GPU sẽ khó kiểm soát hành vi. Cần thêm config device trước hoặc cùng lúc với Docker refactor.

---

## 6. Thay đổi file dự kiến

### 6.1. `Dockerfile`

Mục tiêu:

- Chuyển sang multi-target.
- Có target `prod-cpu` và `dev-gpu`.
- Entry command mặc định chạy `src.api.server:app`.
- Không bake artifacts/database/model cache vào image.

### 6.2. `.dockerignore`

Thêm loại trừ:

```txt
.git
.conda
.venv
__pycache__
.pytest_cache
.mypy_cache
.env
artifacts/database_semantic
artifacts/chunks
artifacts/videos
scratch
frontend/node_modules
frontend/dist
```

Không loại trừ toàn bộ `artifacts/data` nếu deploy cần transcript có sẵn. Cần quyết định dữ liệu nào mount ngoài, dữ liệu nào đóng gói.

### 6.3. Dependency files

Tách dependency để tránh kéo CUDA vào CPU image:

```txt
requirements.base.txt
requirements.cpu.txt
requirements.gpu.txt
```

Hướng dự kiến:

- `requirements.base.txt`: FastAPI, LangChain, Chroma, sentence-transformers, app deps không phụ thuộc CUDA.
- `requirements.cpu.txt`: include base + torch CPU index/wheels.
- `requirements.gpu.txt`: include base, không cài torch nếu base PyTorch image đã có đủ torch CUDA.

### 6.4. `docker-compose.yaml`

Mục tiêu:

- Thay command cũ bằng `uvicorn src.api.server:app`.
- Thêm service CPU/GPU profile.
- Mount volumes:
  - `./artifacts:/app/artifacts`
  - `hf_cache:/app/.cache/huggingface`
- GPU service khai báo NVIDIA device/runtime theo Docker Compose hiện đại.

### 6.5. `.env.example`

Bổ sung biến Docker/runtime:

```env
RAG_DEVICE=auto
RAG_RETRIEVER_K=40
RAG_RETRIEVER_FETCH_K=80
HF_HOME=/app/.cache/huggingface
TOKENIZERS_PARALLELISM=false
```

### 6.6. Code config device/retriever

Các file có thể cần chỉnh:

| File | Lý do |
|---|---|
| `src/rag_core/resource_manager.py` | `_get_device()` nên đọc `RAG_DEVICE` |
| `src/storage/vectorstore.py` | `get_retriever()` nên đọc `RAG_RETRIEVER_K/FETCH_K` |
| `src/retrieval/reranking.py` | Cho phép ép CPU/GPU rõ ràng, giữ fallback an toàn |

---

## 7. Checklist triển khai

- [ ] Benchmark lại reranker với 40 docs và 60 docs để có số đo sát thực tế.
- [x] Tạo `.dockerignore` để giảm build context.
- [x] Tách requirements CPU/GPU hoặc thêm constraints rõ ràng cho torch CPU/GPU.
- [x] Tách requirements runtime/pipeline để image deploy không cài OCR/Whisper/video dependencies.
- [x] Sửa `Dockerfile` thành multi-target `prod-cpu`, `pipeline-cpu`, `dev-gpu`, `pipeline-gpu`.
- [x] Sửa `docker-compose.yaml` dùng profiles `cpu`, `gpu`, `pipeline`, `pipeline-gpu`, `redis`, `frontend` nếu cần.
- [x] Thêm env config `RAG_DEVICE`, `RAG_RETRIEVER_K`, `RAG_RETRIEVER_FETCH_K`.
- [x] Cập nhật code đọc `RAG_DEVICE` thay vì chỉ phụ thuộc `torch.cuda.is_available()`.
- [x] Cập nhật code đọc retriever `k/fetch_k` từ env với default giữ hành vi cũ.
- [x] Kiểm thử build `prod-cpu` không kéo CUDA wheel và đo size runtime CPU: `rag-qabot:cpu-runtime = 3.97GB`.
- [ ] Kiểm thử chạy container CPU trả lời được query RAG.
- [ ] Kiểm thử chạy local GPU container nhận `cuda`.
- [x] Cập nhật checklist trong chính file này sau từng bước triển khai.

---

## 8. Tiêu chí hoàn thành

Docker upgrade được xem là đạt khi:

1. `prod-cpu` build thành công và không phụ thuộc CUDA runtime.
2. `dev-gpu` chạy được trên máy local có NVIDIA Docker và model nhận `cuda`.
3. Backend trong container chạy đúng app `src.api.server:app`.
4. RAG query hoạt động với `artifacts/` mount ngoài container.
5. HuggingFace model cache được persist qua volume, restart không download lại nếu cache còn.
6. `.env` không bị copy vào image.
7. CPU deploy có thể giảm `RAG_RETRIEVER_K/FETCH_K` mà không sửa code.
8. README hoặc docs có lệnh chạy local GPU và deploy CPU rõ ràng.

---

## 9. Kế hoạch kiểm thử thủ công

### Case 1: Build CPU image

```powershell
docker build --target prod-cpu -t rag-qabot:cpu .
```

Kỳ vọng:

- Build thành công.
- Không tải CUDA toolkit/wheel nặng.
- Image size nhỏ hơn GPU image đáng kể.

### Case 2: Run CPU compose

```powershell
$env:COMPOSE_PROFILES="cpu,redis"
docker compose up --build
```

Kỳ vọng:

- Backend start tại port `8000`.
- Log device là `cpu` nếu `RAG_DEVICE=cpu`.
- Gọi `/chat` hoặc endpoint health hoạt động.

### Case 3: Run GPU compose local

```powershell
$env:COMPOSE_PROFILES="gpu,redis"
docker compose up --build
```

Kỳ vọng:

- Container thấy GPU qua `nvidia-smi` hoặc `torch.cuda.is_available()`.
- Log device là `cuda`.
- Reranker chạy nhanh hơn CPU rõ rệt.

### Case 4: Model cache persist

1. Chạy container lần đầu để tải model.
2. Stop container.
3. Chạy lại container.

Kỳ vọng:

- Lần 2 không download lại toàn bộ model từ HuggingFace.
- Startup nhanh hơn hoặc log cache hit rõ ràng.

### Case 5: CPU tuning

Chạy deploy CPU với:

```env
RAG_RETRIEVER_K=20
RAG_RETRIEVER_FETCH_K=50
```

Kỳ vọng:

- Reranker nhận ít docs hơn.
- Latency CPU giảm.
- Câu trả lời vẫn có citation hợp lý.

---

## 10. Rủi ro và lưu ý

### 10.1. GPU Docker cần NVIDIA Container Toolkit

Local GPU compose chỉ chạy nếu máy đã cài Docker Desktop + NVIDIA Container Toolkit phù hợp.
Nếu thiếu, dùng CPU profile vẫn chạy được.

### 10.2. CPU image vẫn có thể nặng vì NLP stack

`sentence-transformers`, `transformers`, `torch`, `chromadb` vẫn là dependency lớn.
Mục tiêu là tránh CUDA runtime/wheel, không thể biến image ML thành siêu nhỏ.

### 10.3. Dữ liệu artifacts lớn

Không nên copy database/vector/chunks vào image nếu mục tiêu deploy linh hoạt.
Nên mount volume hoặc chuẩn bị bước sync dữ liệu riêng.

### 10.4. Khác biệt Windows local và Linux container

Benchmark hiện chạy trên Windows Anaconda. Docker Linux có thể khác tốc độ.
Cần benchmark lại trong container sau khi Dockerfile mới hoàn thành.

---

## 11. Ghi chú triển khai

- Giữ default code tương thích hành vi cũ: nếu không set env thì `RAG_DEVICE=auto`, `k=40`, `fetch_k=80`.
- Không refactor logic RAG ngoài phần đọc config cần thiết.
- Không đổi API contract frontend/backend.
- Sau mỗi checklist item hoàn thành, cập nhật trạng thái trong mục **Checklist triển khai** của file này.
