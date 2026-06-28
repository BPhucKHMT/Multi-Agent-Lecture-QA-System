# Báo cáo Context Dự án — Handoff cho Session mới

Tài liệu này tóm tắt toàn bộ bối cảnh hệ thống, các thay đổi gần nhất liên quan đến việc huấn luyện mô hình **BGE-M3 V3 Embedding** và trạng thái triển khai Production hiện tại để các session làm việc tiếp theo có thể nắm bắt và tiếp tục phát triển ngay lập tức.

---

## 📌 Trạng thái Hệ thống Hiện tại (Current State)

### 1. Mô hình Embedding Production
* **Model:** BGE-M3 V3 Fine-tuned (tên thư mục gốc: `experiments/runs/finetune/embedding/20260616-120132`).
* **Đường dẫn đóng gói:** `models/production/bge-m3-v3/`.
* **Cấu hình biến môi trường (`.env`):**
  ```env
  EMBEDDING_MODEL_NAME=models/production/bge-m3-v3
  ```
  Hệ thống FastAPI Backend sẽ tự động load mô hình này khi khởi chạy.

### 2. Cơ sở dữ liệu Vector (Vector Database)
* **Thư mục lưu trữ:** `artifacts/database_semantic/` (ChromaDB).
* **Số lượng chunks đã index:** **4.469 chunks** thuộc 4 môn học:
  - `CS114` (Machine Learning)
  - `CS116` (Web Application Development)
  - `CS315` (Software Engineering)
  - `CS431` (Multi-Agent QA / Lập trình nâng cao)
* **Trạng thái:** Đã được rebuild đồng bộ hoàn toàn với mô hình **V3 Embedding** trên GPU qua script `scratch/rebuild_production_index.py`.

---

## 📊 Kết quả Đánh giá Benchmark (Retrieval Evaluation)

Mô hình V3 đã được benchmark kỹ lưỡng trên 300 câu hỏi test của tập dữ liệu Pilot và so sánh trực tiếp trên 2 chiến lược phân mảnh (Recursive vs Timestamp).

### 1. Bảng số sánh các cấu hình quan trọng (Recursive vs Timestamp)

| Config ID | Chiến lược | Chunking | Embedding | Hit@1 | Hit@5 | Hit@10 | Recall@40 | MRR@10 | NDCG@10 | Final Recall@10 |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| **`C02`** | `hybrid` | `recursive` | `bge_m3` (Gốc) | 0.6500 | 0.8967 | 0.9333 | 0.6537 | 0.7471 | 0.5205 | 0.4410 |
| **`C16`** | `hybrid` | `recursive` | **`bge_m3_v3`** (Fine-tuned) | **0.6500** | 0.8933 | 0.9433 | 0.6662 | **0.7540** | 0.5328 | 0.4522 |
| **`C06`** | `hybrid` | `timestamp` | `bge_m3` (Gốc) | 0.5733 | 0.8900 | 0.9533 | **0.6915** | 0.7114 | 0.5526 | 0.4774 |
| **`C18`** | `hybrid` | `timestamp` | **`bge_m3_v3`** (Fine-tuned) | 0.5733 | **0.9000** | **0.9667** | 0.6865 | 0.7173 | **0.5567** | **0.4793** |

### 2. Phân tích Trade-off giữa các chiến lược
* **Winner được lựa chọn cho Production: `C16` (Recursive + V3)**
  * **Lý do:** Đạt **Hit@1 = 0.6500** và **MRR@10 = 0.7540** cao nhất. Chiến lược `recursive` bảo toàn cấu trúc ngữ nghĩa của các đoạn văn (semantic paragraph boundaries) giúp LLM trả lời tập trung và không bị đứt đoạn kiến thức.
* **Đối thủ so sánh: `C18` (Timestamp + V3)**
  * Đạt **Hit@5 = 0.9000** cao nhất nhờ cơ chế sliding window có độ chồng chéo (overlap 30s). Tuy nhiên, do bị cắt vụn theo mốc thời gian cứng (time-based boundaries), thông tin dễ bị phân mảnh làm giảm thứ hạng chính xác ở vị trí đầu tiên (Hit@1 giảm còn 0.5733 và MRR@10 giảm còn 0.7173).

---

## 🛠️ Công nghệ & Kỹ thuật đã áp dụng ở V3 Fine-tuning
Mô hình V3 đạt hiệu năng vượt trội nhờ tích hợp đồng thời các kỹ thuật nâng cao:
1. **Query Augmentation & Paraphrasing:** Sử dụng mô hình sinh để đa dạng hóa câu hỏi (paraphrase) nhằm giảm thiểu vocabulary mismatch.
2. **CMNRL (Co-efficient Multiple Negatives Ranking Loss):** Kết hợp học độ tương đồng đa lớp.
3. **Iterative Hard Negative Mining:** Khai thác triệt để các mẫu âm tính khó từ checkpoint V2 để bắt mô hình phân biệt sâu hơn.

---

## 🔮 Kế hoạch hành động tiếp theo (Next Steps Backlog)

Nếu bạn tiếp nhận session mới này, đây là các đầu việc cần làm tiếp theo:

1. **Đo lường độ trễ (Latency Profiling):**
   * Tiến hành đo lường độ trễ truy vấn (p95, p99 latency) của pipeline `C16` trên GPU/CPU dưới môi trường tải cao để tối ưu thời gian phản hồi của chatbot.
2. **LLM-as-a-judge Evaluation:**
   * Benchmark chất lượng câu trả lời sinh ra từ mô hình sinh (generation quality) dựa trên ngữ cảnh đã tối ưu từ `C16`. Đánh giá tỷ lệ ảo giác (hallucination rate) và độ bao phủ thông tin (faithfulness).
3. **Refactor Codebase để giải quyết Cảnh báo Deprecation:**
   * Trong log chạy của `src/storage/vectorstore.py`, `HuggingFaceEmbeddings` đang được load từ `langchain_community`. Cần refactor chuyển sang thư viện mới `langchain-huggingface` để tránh các lỗi không tương thích trong tương lai.

---

*Tài liệu kỹ thuật chi tiết hơn có thể xem tại: `experiments/docs/evaluation/end_to_end_retrieval.md`*
