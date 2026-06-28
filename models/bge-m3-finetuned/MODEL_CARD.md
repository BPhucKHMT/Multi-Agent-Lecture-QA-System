# Model Card: BAAI/bge-m3 Fine-tuned cho Hệ thống RAG QABot UIT

> **Alias trong Production:** `models/production/bge-m3-v3/`  
> **Thư mục này:** Chứa checkpoint **phiên bản cuối cùng** (V3) của quá trình fine-tune — tương đương với `models/production/bge-m3-v3/`.

---

## 1. Thông tin Mô hình

| Thuộc tính | Giá trị |
|---|---|
| **Tên mô hình** | `BAAI/bge-m3` fine-tuned cho bài giảng UIT (V3 — Final) |
| **Loại mô hình** | Sentence Transformer — Dense Embedding |
| **Mô hình cơ sở (Base)** | [`BAAI/bge-m3`](https://huggingface.co/BAAI/bge-m3) |
| **Chiều vector đầu ra** | 1024 chiều |
| **Độ dài chuỗi tối đa** | 384 tokens |
| **Hàm tương đồng** | Cosine Similarity |
| **Ngôn ngữ** | Tiếng Việt + Tiếng Anh (đa ngữ) |
| **Kiến trúc backbone** | XLMRobertaModel |
| **Ngày huấn luyện** | 2026-06-16 |
| **Framework** | sentence-transformers==5.1.2, PyTorch 2.10.0+cu128 |

---

## 2. Mục đích & Bối cảnh Dự án

Mô hình này được fine-tune như một phần trong dự án **RAG QABot UIT** — hệ thống hỏi đáp tự động cho các môn học tại Trường Đại học Công nghệ Thông tin (UIT), TP. HCM.

**Vấn đề cần giải quyết:**  
Các mô hình embedding đa ngữ tổng quát (như `BAAI/bge-m3` gốc) không được tối ưu cho ngữ cảnh **bài giảng đại học tiếng Việt**, nơi thuật ngữ kỹ thuật bằng tiếng Anh xuất hiện xen lẫn với diễn giải tiếng Việt theo phong cách giảng nói (spoken language). Việc fine-tune giúp mô hình học được sự tương đồng ngữ nghĩa chuyên biệt giữa câu hỏi của sinh viên và các đoạn nội dung bài giảng.

**Vai trò trong pipeline RAG:**

```
[Câu hỏi người dùng]
        ↓
[Fine-tuned Embedding Model (bge-m3-v3)] ← Đây là mô hình này
        ↓
[ChromaDB Vector Search + BM25 Hybrid Retrieval]
        ↓
[Jina Reranker]
        ↓
[LLM Generation (GPT-4o-mini)]
        ↓
[Câu trả lời có trích dẫn]
```

---

## 3. Dữ liệu Huấn luyện

### 3.1. Nguồn dữ liệu

Dữ liệu được sinh tổng hợp (synthetic) từ transcript bài giảng của **4 môn học tại UIT**:

| Môn học | Mã môn |
|---|---|
| Máy học nâng cao | CS315 | 
| Máy học | CS114 |
| Lập trình Python cho Máy học | CS116 | 
| Các kỹ thuật học sâu và ứng dụng | CS431 | 


### 3.2. Cấu trúc Dataset (Dạng Hard Negatives)

| Thành phần | Mô tả |
|---|---|
| `sentence_0` | Câu hỏi tổng hợp (query) |
| `sentence_1` | Đoạn transcript liên quan (positive) |
| `sentence_2–6` | Các đoạn transcript không liên quan (hard negatives) |
| **Tổng số mẫu** | **25,194 training samples** |
| **Hard negatives mỗi query** | 5 negatives |
| **File dữ liệu** | `experiments/data/finetune/train_queries.jsonl` |
| **File negatives** | `experiments/data/finetune/train_hard_negatives.jsonl` |

> **Phương pháp sinh câu hỏi:** Sử dụng GPT-4o-mini để sinh câu hỏi từ mỗi đoạn transcript (~700 ký tự), sau đó augment thêm bằng `synthetic_queries_augmented.jsonl`.

---

## 4. Chi tiết Huấn luyện

### 4.1. Chiến lược Fine-tune

| Tham số | Giá trị |
|---|---|
| **Loss Function** | `CachedMultipleNegativesRankingLoss` |
| **Loss scale** | 20.0 |
| **Epochs** | 3 |
| **Batch size** | 64 |
| **Learning rate** | 5e-5 |
| **Optimizer** | AdamW (fused) |
| **Frozen layers** | Freeze 8 layers đầu |
| **Hard negatives/query** | 5 |
| **FP16** | ✅ Có |
| **mini_batch_size (cached)** | 8 |

### 4.2. Training Logs

| Epoch | Step | Training Loss |
|:---:|:---:|:---:|
| 1.27 | 500 | 1.7203 |
| 2.54 | 1000 | 1.1170 |

> **Nhận xét:** Loss giảm rõ rệt từ 1.72 → 1.12 sau 1000 steps (3 epochs, 394 samples/step), cho thấy mô hình hội tụ tốt trên tập bài giảng tiếng Việt.

---

## 5. Kết quả Đánh giá

### 5.1. So sánh Embedding Models trên Corpus Bài giảng UIT

Đánh giá trên tập ground truth 300 câu hỏi (`ground_truth_pilot.jsonl`), sử dụng cấu hình ChromaDB MMR (k=40, fetch_k=80, lambda=0.7):

| Mô hình | Loại | Recall@10 | Recall@40 | MRR@10 | NDCG@10 | Hit@10 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **`bge-m3-finetuned` (Ours — thư mục này)** | Đa ngữ/Fine-tuned | 0.5120 | 0.6427 | **0.672** | **0.453** | **0.903** |
| `BAAI/bge-m3` (baseline) | Đa ngữ | **0.5155** | **0.6498** | 0.633 | 0.437 | 0.887 |
| `intfloat/multilingual-e5-large` | Đa ngữ | 0.4896 | 0.6510 | 0.657 | 0.442 | 0.883 |
| `contextboxai/halong_embedding` | Tiếng Việt/RAG | 0.4819 | 0.6382 | 0.595 | 0.399 | 0.840 |

### 5.2. Kết quả E2E Retrieval (Sau Reranker)

Trong benchmark 22 cấu hình E2E (`end_to_end_retrieval.md`), phiên bản V3 đạt kết quả sau khi kết hợp với Hybrid Retrieval và Jina Reranker:

| Config | Retrieval | Chunk | Embedding | Hit@5 | Recall@40 | MRR@10 | NDCG@10 |
|---|---|---|---|:---:|:---:|:---:|:---:|
| **`C16` — Alternative** | Hybrid | recursive | **bge-m3-ft-v3** | 0.8933 | **0.7973** | **0.7540** | 0.5328 |
| **`C21` — ✅ Production** | Hybrid | timestamp_150 | **bge-m3-ft-v3** | **0.9467** | 0.7758 | **0.8085** | **0.6092** |

> **`C21` là cấu hình production hiện tại** — đây là cấu hình tốt nhất tổng thể theo các chỉ số ranking (MRR, NDCG, Hit@5).

---

## 6. Phân tích Cải tiến qua các Phiên bản

| Phiên bản | Thay đổi chính | MRR@10 (MMR) | Ghi chú |
|---|---|:---:|---|
| **Baseline (`BAAI/bge-m3`)** | Không fine-tune | 0.633 | Reference |
| **Fine-tuned (thư mục này)** | Fine-tune 3 epochs, 5 hard negatives, freeze 8 layers | **0.672** | Tốt nhất, +6.2% vs baseline |

> **Insight:** Freeze 8 lớp đầu (encoder layers) giúp giữ lại khả năng đa ngữ tổng quát của mô hình gốc, trong khi chỉ fine-tune các lớp trên để học đặc trưng bài giảng tiếng Việt. Kết quả MRR@10 tăng 6.2% so với baseline chưa fine-tune.

---

## 7. Cách Sử dụng

### 7.1. Cài đặt

```bash
pip install -U sentence-transformers
```

### 7.2. Load và Inference

```python
from sentence_transformers import SentenceTransformer

# Load model (từ thư mục local)
model = SentenceTransformer("models/bge-m3-finetuned")

# Encoding câu hỏi và đoạn bài giảng
query = "Gradient Descent hoạt động như thế nào?"
passages = [
    "Gradient Descent là thuật toán tối ưu cập nhật tham số...",
    "Overfitting xảy ra khi mô hình học quá khớp tập train...",
]

query_embedding = model.encode(query, normalize_embeddings=True)
passage_embeddings = model.encode(passages, normalize_embeddings=True)

# Tính cosine similarity
similarities = model.similarity(query_embedding, passage_embeddings)
print(similarities)
```

### 7.3. Tích hợp trong Hệ thống RAG

Model được nạp tự động từ biến môi trường trong `src/storage/vectorstore.py`:

```python
# .env
EMBEDDING_MODEL_NAME = "models/production/bge-m3-v3"  # V3 — phiên bản production

# src/storage/vectorstore.py
embedding_model = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
self.embedding = HuggingFaceEmbeddings(
    model_name=embedding_model,
    model_kwargs={"device": device}
)
```

---

## 8. Cấu trúc Thư mục Model

```
models/bge-m3-finetuned/          ← Fine-tuned final model (thư mục này)
├── config.json                   # Cấu hình kiến trúc XLM-RoBERTa
├── config_sentence_transformers.json
├── model.safetensors             # Trọng số mô hình (~2.27 GB) — không push Git
├── modules.json
├── sentence_bert_config.json
├── sentencepiece.bpe.model       # SentencePiece tokenizer
├── special_tokens_map.json
├── tokenizer.json
├── tokenizer_config.json
├── 1_Pooling/config.json         # CLS pooling
└── 2_Normalize/config.json       # L2 normalization

models/production/bge-m3-v3/      ← Alias của cùng model trên (dùng trong production)
└── (cấu trúc tương tự)
```

> ⚠️ **Lưu ý:** File `model.safetensors` (~2.27 GB) không được lưu trên GitHub do giới hạn kích thước. Trọng số mô hình được lưu trên Google Drive hoặc Hugging Face Hub. Xem hướng dẫn cài đặt trong `README.md` gốc để biết cách tải về.

---

## 9. Thông tin Kỹ thuật

| Thông số | Giá trị |
|---|---|
| Số tham số | ~570M |
| Kích thước file weights | ~2.27 GB (safetensors) |
| Thời gian inference (GPU) | ~20ms/query |
| Thời gian inference (CPU) | ~200ms/query |
| VRAM yêu cầu (GPU) | ~3 GB |
| RAM yêu cầu (CPU) | ~5 GB |

---

## 10. Trích dẫn

```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title     = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author    = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of EMNLP 2019",
    year      = "2019",
    url       = "https://arxiv.org/abs/1908.10084",
}

@misc{chen2024bge,
    title  = {BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation},
    author = {Jianlv Chen et al.},
    year   = {2024},
    url    = {https://arxiv.org/abs/2309.07597},
}
```
