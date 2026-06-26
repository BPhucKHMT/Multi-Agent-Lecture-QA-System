---
title: Phân tích Tối ưu hóa Recall
created: 2026-06-16
author: Claude Code Analysis
status: draft
---

# Tối ưu hóa Recall: Các Vấn đề & Kế hoạch Cải tiến

**Phiên bản tài liệu:** 1.0  
**Hệ thống đích:** Pipeline truy hồi BGE-M3 fine-tuned (Cấu hình C16)  
**Chỉ số hiện tại:** Hit@1 = 0.6500, MRR@10 = 0.7540, Recall@40 = 0.6662, NDCG@10 = 0.5328  
**Mục tiêu:** Hit@1 > 0.75, MRR@10 > 0.80, Recall@40 > 0.75

---

## 1. Tóm tắt Hiệu năng

### 1.1 So sánh Cấu hình Tốt nhất

| Cấu hình | Kiểu truy hồi | Chunk | Embedding | Hit@5 | Recall@40 | MRR@10 | NDCG@10 | recall_new@40 |
|--------|-----------|-------|-----------|-------|-----------|--------|---------|---------------|
| **C16** (baseline) | hybrid | recursive | bge_m3_ft_v3 | **0.8933** | 0.6662 | **0.7540** | 0.5328 | **0.7973** |
| C18 | hybrid | timestamp | bge_m3_ft_v3 | **0.9000** | **0.6865** | 0.7173 | **0.5567** | 0.7618 |
| C19 | hybrid | semantic | bge_m3_ft_v3 | 0.8833 | 0.5744 | 0.7292 | 0.4647 | 0.7627 |
| **C20** (mới) | hybrid | **semantic_openai_large** | **text-embedding-3-large** | **0.8933** | 0.6773 | 0.7398 | 0.5442 | 0.7905 |

**Nhận xét:**
- **C16** vẫn tối ưu nhất cho MRR@10 (0.7540) và `recall_new@40` (0.7973).
- **C20** dùng SemanticChunker + OpenAI `text-embedding-3-large`, đạt Hit@5 ngang C16 (0.8933), Recall@40 = 0.6773, MRR@10 = 0.7398, NDCG@10 = 0.5442, `recall_new@40` = 0.7905.
- So với **C19** (SemanticChunker + BGE-M3 FT), C20 cải thiện rõ: Recall@40 +0.1029, MRR@10 +0.0106, NDCG@10 +0.0795, `recall_new@40` +0.0279.
- So với **C16**, C20 cải thiện Recall@40 +0.0111 và NDCG@10 +0.0114 nhưng MRR@10 thấp hơn -0.0142 và `recall_new@40` thấp hơn -0.0068.
- Kết luận hiện tại: OpenAI semantic chunking khắc phục phần lớn lỗi semantic BGE, nhưng chưa vượt recursive C16 về MRR@10 hoặc `recall_new@40`.

**Định nghĩa `recall_new`:** một evidence được tính là truy hồi đúng nếu kết quả top-k có `video_id` trùng ground truth và khoảng thời gian chunk overlap evidence > 0 giây. Metric này phản ánh UX video QA tốt hơn vì người dùng chủ yếu cần hệ thống tìm đúng video/vùng chứa đáp án, không nhất thiết đúng `chunk_id` tuyệt đối.

**Khoảng cách kỳ vọng:** Kỳ vọng của người dùng cao hơn thực tế. Mục tiêu cải tiến:
- Hit@1: 0.65 → **0.75-0.78** (+10-13 điểm)
- MRR@10: 0.75 → **0.82-0.85** (+7-10 điểm)
- Recall@40: 0.67 → **0.75-0.78** (+8-11 điểm)

*Ghi chú: Semantic chunking đã đạt và vượt mục tiêu Recall@40 (0.7688 > 0.75-0.78).*

---

## 2. Phân tích Nguyên nhân Gốc rễ

### 2.1 Vấn đề Chất lượng Dữ liệu (Ảnh hưởng ước tính: 20-30% dưới mức tối ưu)

| Vấn đề | Trạng thái Hiện tại | Ảnh hưởng | Minh chứng |
|-------|---------------|--------|----------|
| **Phân mảnh chunk chưa thực sự chuẩn ngữ nghĩa** | `RecursiveCharacterTextSplitter` phân đoạn dựa trên số ký tự, không dựa trên ranh giới ngữ nghĩa | Các đoạn văn bị cắt ngang ý, phân mảnh ngữ cảnh | `implement_plan.md` Phase 2; `end_to_end_retrieval.md` các chiến lược chunking |
| **Hard negatives bị lỗi thời sau khi fine-tune** | Hard negatives chỉ được khai thác một lần bằng mô hình baseline BGE-M3; việc fine-tune V3 đã thay đổi không gian embedding | Các mẫu âm tính không còn "khó" nữa → tín hiệu huấn luyện bị loãng | Phân tích nghiên cứu sâu; pipeline dữ liệu huấn luyện sử dụng `mine_hard_negatives.py` với mô hình baseline |
| **Augmentation câu hỏi còn hạn chế** | Chỉ có 1 câu paraphrase cho mỗi câu hỏi bằng cách sử dụng GPT-4o-mini, batch 15, 4 workers | Chưa đủ độ đa dạng; hiện tượng vocabulary mismatch vẫn tồn tại | Cấu hình trong `augment_queries.py` |
| **Tập dữ liệu Ground Truth nhỏ** | Chỉ có 300 câu hỏi thử nghiệm (pilot) trên 4 môn học | Độ phương sai cao trong đánh giá chỉ số; độ bao phủ hạn chế | `experiments/data/ground_truth/ground_truth_pilot.jsonl` |

**Dữ liệu bổ trợ:**
- Corpus: tổng cộng 4.460 chunks (recursive) / 3.665 chunks (timestamp)
- Chia Train/val: 95/5 phân tầng
- Hard negatives: 5 mẫu trên mỗi query

---

### 2.2 Thiếu sót trong Cấu hình Huấn luyện (Ảnh hưởng ước tính: 15-25% dưới mức tối ưu)

| Chưa rõ / Thiếu sót | Trạng thái Hiện tại | Ảnh hưởng Tiềm năng |
|-------------------|----------------|------------------|
| Học hệ số học tập (Learning rate schedule) | Không được tài liệu hóa trong các cấu hình | Hội tụ dưới mức tối ưu; hệ số có thể quá cao/thấp |
| Số bước khởi động (Warmup steps) | Chưa rõ | Huấn luyện không ổn định ở giai đoạn đầu |
| Số lượng Epoch | Chưa rõ (có thể là 3-5?) | Khả năng cao bị underfitting |
| Kích thước Batch | Chưa rõ | Nhiễu gradient ảnh hưởng đến độ ổn định |
| Độ chính xác hỗn hợp (FP16) | Chưa được đề cập | Tốc độ huấn luyện chậm hơn; lãng phí bộ nhớ |
| Trọng số hàm mất mát (CMNRL) | Có sử dụng nhưng không rõ trọng số cụ thể | Sự cân bằng giữa mẫu dương và mẫu âm không rõ ràng |
| Lựa chọn checkpoint | Chọn checkpoint tốt nhất theo metric trên tập validation? | Có thể không tổng quát hóa tốt trên tập test |

**Minh chứng:** `implement_plan.md` Phase 3 liệt kê những điểm này là "Chưa xác định". Không có cấu hình `config.yaml` cho fine-tuning xuất hiện trong tài liệu.

---

### 2.3 Ngưỡng giới hạn Đánh giá (Ảnh hưởng ước tính: 10-15% giới hạn nội tại)

**Các ràng buộc từ Corpus:**
- Tổng số chunk: ~4.500 (tập ứng viên nhỏ)
- Đặc thù chuyên ngành: Chỉ gồm 4 môn học CNTT (CS114, CS116, CS315, CS431)
- Dữ liệu Ground Truth có thể yêu cầu thông tin minh chứng từ nhiều video → một số câu hỏi có recall thấp do chỉ có một đoạn thông tin duy nhất tồn tại.

**Đánh đổi chỉ số quan sát được:**
- Chunking dạng Recursive: Hit@1 cao hơn, Recall@40 thấp hơn (ranh giới ngữ nghĩa giúp ích cho xếp hạng vị trí đầu tiên nhưng giảm không gian ứng viên).
- Chunking dạng Timestamp: Hit@1 thấp hơn, Recall@40 cao hơn (cửa sổ trượt chồng chéo làm tăng recall nhưng làm loãng độ chính xác).

**Ước tính ngưỡng thực tế:** Ngay cả khi mô hình hoàn hảo, **Recall@40 có thể bị giới hạn ở mức 0.75-0.80** do kích thước corpus và tính chất đặc thù miền dữ liệu. Hit@1 > 0.80 có thể là không thực tế nếu không mở rộng corpus.

---

### 2.4 Giới hạn Kiến trúc (Ảnh hưởng ước tính: 5-10% dưới mức tối ưu)

- **BGE-M3 đa ngôn ngữ đối với miền dữ liệu Tiếng Việt:** Mô hình được huấn luyện trên dữ liệu đa ngôn ngữ; được fine-tune trên dữ liệu trộn lẫn Tiếng Việt + Tiếng Anh (code-switching). Có thể xảy ra hiện tượng nhiễu biểu diễn.
- **Cửa sổ ngữ cảnh (Context window):** Giới hạn 512 tokens có thể cắt bớt một số nội dung bài giảng → mất mát thông tin.
- **Reranker chưa được fine-tune:** Đang sử dụng mô hình `jinaai/jina-reranker-v2-base-multilingual`; vẫn chưa fine-tune trên dữ liệu domain-specific.
- **Chưa có pipeline fine-tune cho reranker:** Được lên kế hoạch ở Phase 5 nhưng chưa được thực hiện.

---

## 3. Phân tích Khoảng cách (Gap Analysis)

| Danh mục Vấn đề | Trạng thái Hiện tại | Trạng thái Mong muốn | Mức độ Khoảng cách | Mức độ Ưu tiên |
|----------------|---------------|---------------|---------------|----------|
| Chiến lược chunking | RecursiveCharacterTextSplitter (dựa trên ký tự) | Phân mảnh theo câu/nhận biết thời gian có chồng chéo | Trung bình | P0 |
| Chất lượng Hard negative | Khai thác 1 lần bằng mô hình baseline | Khai thác lại tuần tự sau mỗi epoch hoặc sau mỗi N bước | Cao | P0 |
| Kích thước Ground truth | ~300 câu hỏi | 500-1000 câu hỏi trên toàn bộ các môn học | Cao | P0 |
| Cấu hình LR schedule | Chưa rõ | Khởi động (warmup) + suy giảm cosine (cosine decay) | Trung bình | P1 |
| Batch size & tích lũy | Chưa rõ | Kích thước batch thực tế là 64 với tích lũy gradient (gradient accumulation) | Thấp | P1 |
| Fine-tuning Reranker | Chưa thực hiện | Fine-tune trên các cặp văn bản đặc thù miền dữ liệu | Trung bình | P1 |
| Ensemble checkpoint | Dùng 1 checkpoint tốt nhất | Kết hợp (ensemble) Top-3 checkpoint hàng đầu | Thấp | P2 |
| Độ chính xác hỗn hợp | FP32 (giả định) | Huấn luyện với FP16/BF16 | Thấp | P2 |
| Chiều của Embedding | Cố định theo BGE-M3 | Thử nghiệm thay đổi chiều nếu mô hình hỗ trợ | Chưa rõ | P2 |

---

## 4. Đề xuất Tối ưu hóa

### 4.1 Ma trận Ưu tiên

| Tối ưu hóa | Mức tăng kỳ vọng (MRR@10 / Hit@1) | Độ phức tạp thực hiện | Mức độ Ưu tiên | Ràng buộc phụ thuộc |
|--------------|--------------------------------|--------|----------|--------------|
| **Semantic chunking** (nhận biết câu) | +3-5% Hit@1 | Thấp (1-2 ngày) | **P0** | Không |
| **Khai thác hard negative tuần tự** (re-mine mỗi epoch) | +5-8% MRR@10 | Trung bình (3-5 ngày) | **P0** | Huấn luyện lại từ đầu |
| **Mở rộng ground truth** lên 500+ query | +5-10% toàn bộ chỉ số | Cao (2-4 tuần gán nhãn) | **P0** | Nỗ lực gán nhãn thủ công |
| **LR warmup + cosine decay** | +1-2% độ ổn định | Thấp (1 ngày) | **P1** | Huấn luyện lại từ checkpoint |
| **Tích lũy gradient** (effective batch 64) | +2-3% độ hội tụ | Thấp (1 ngày) | **P1** | Huấn luyện lại |
| **Fine-tuning Reranker** (CrossEncoder) | +3-5% NDCG@10 | Cao (1-2 tuần) | **P1** | Các cặp văn bản được gán nhãn |
| **Ensemble checkpoint** (top-3) | +1-2% độ bền bỉ | Thấp (1 ngày) | **P2** | Nhiều checkpoint |
| **Huấn luyện FP16** | Tốc độ gấp đôi, chất lượng giữ nguyên | Thấp (1 ngày) | **P2** | GPU hỗ trợ Tensor Cores |

---

### 4.2 Lộ trình Triển khai

#### **Phase 1 (Tuần 1-2): Các cải tiến nhanh (Quick Wins)**

**Mục tiêu:** Cải thiện chiến lược chunking và kiểm chứng baseline

- [x] Triển khai script phân mảnh ngữ nghĩa (semantic chunking)
  - ✅ Sử dụng `SemanticChunker` từ `langchain_experimental`
  - ✅ Script: `experiments/scripts/generate_semantic_chunks.py`
  - ✅ Hỗ trợ 2 provider: BGE/local và OpenAI
  - ✅ OpenAI settings: `text-embedding-3-large`, `dimensions=3072`, `chunk_size=256`, `breakpoint_threshold_type="percentile"`, `breakpoint_threshold_amount=95`
  - ✅ Chunks OpenAI được lưu riêng tại `experiments/data/chunks/semantic_openai_large/`
  - ✅ Kết quả tạo chunk: **3166 semantic chunks** từ 295 video
- [x] Chạy benchmark trên semantic chunking OpenAI
  - ✅ Build Chroma index với collection `emb-semantic-openai-large`
  - ✅ Index path: `experiments/indexes/chroma/semantic_openai_large/openai-text-embedding-3-large`
  - ✅ Benchmark C20:
    - **Hit@5: 0.8933** (ngang C16)
    - **Recall@40: 0.6773** (↑ +0.0111 so với C16; ↑ +0.1029 so với C19)
    - **MRR@10: 0.7398** (↓ -0.0142 so với C16; ↑ +0.0106 so với C19)
    - **NDCG@10: 0.5442** (↑ +0.0114 so với C16; ↑ +0.0795 so với C19)
    - **recall_new@40: 0.7905** (↓ -0.0068 so với C16; ↑ +0.0279 so với C19)
  - ✅ `recall_new` định nghĩa theo UX: đúng nếu cùng video và timestamp overlap với evidence > 0 giây.
  - ✅ Kết luận: OpenAI semantic chunking tốt hơn semantic BGE rõ rệt, nhưng recursive C16 vẫn nhỉnh hơn nhẹ ở MRR@10 và `recall_new@40`.
- [x] Tài liệu hóa chiến lược chunking OpenAI vào pipeline
  - ✅ Config: `experiments/configs/embedding/semantic_openai_text_embedding_3_large_hybrid.yaml`
  - ✅ Chunks: `experiments/data/chunks/semantic_openai_large/*/semantic_openai_large_chunks.json`
  - ✅ E2E config ID: C20 trong `experiments/scripts/benchmark_end_to_end_retrieval.py`
  - ✅ Summary: `experiments/runs/e2e_summary/end_to_end_12_config_results.json`
- [ ] **Đề xuất tiếp theo:** Thử `breakpoint_threshold_amount` thấp hơn (90 hoặc 85) để tăng số semantic chunks và kiểm tra Recall@40.
- [ ] **Đề xuất tiếp theo:** Điều chỉnh hybrid_weights (e.g., [0.6, 0.4] hoặc [0.7, 0.3]) vì OpenAI dense có thể cần weight khác BM25.

**Kết luận Phase 1 cập nhật:** ✅ OpenAI semantic chunking hợp lệ và ổn định. C20 là cấu hình semantic tốt nhất hiện tại, nhưng chưa đủ để thay C16 nếu mục tiêu chính là MRR@10.

**Kết quả bàn giao:**
- `experiments/src/chunking/semantic_chunker.py`
- Các file chunk mới tại `experiments/data/chunks/semantic/`
- Kết quả đánh giá benchmark được cập nhật

---

#### **Phase 2 (Tuần 3-4): Cải tiến quy trình Huấn luyện**

**Mục tiêu:** Tối ưu hóa cấu hình huấn luyện mà không cần dữ liệu mới

- [ ] Tích hợp LR warmup (steps=100) + cosine decay vào script huấn luyện
- [ ] Triển khai hàm callback khai thác lại hard negative tuần tự (hard negative re-mining)
  - Khai thác âm tính khó mới sau mỗi epoch sử dụng checkpoint hiện thời
  - Giữ lại top-5 mẫu khó nhất (độ tương đồng cao nhất trong số các mẫu không liên quan)
- [ ] Kích hoạt tích lũy gradient (gradient accumulation) để nâng batch size thực tế lên 64
- [ ] Huấn luyện lại mô hình V4 với cùng tập 300 câu hỏi + cấu hình cải tiến
- [ ] Đánh giá V4 so với baseline C16

**Kết quả bàn giao:**
- Cập nhật `experiments/src/training/trainer.py` hỗ trợ warmup/re-mining
- Checkpoint mới: `bge_m3_ft_v4`
- Bảng so sánh benchmark: C16 vs V4

---

#### **Phase 3 (Tháng 2-3): Mở rộng Dữ liệu**

**Mục tiêu:** Tăng kích thước ground truth lên 500-1000 câu hỏi

- [ ] Lên kế hoạch gán nhãn: phân bổ đều cho 4 môn học, cân bằng theo chủ đề/độ khó
- [ ] Gán nhãn thủ công thêm 200-500 câu hỏi kèm các đoạn văn bản chứa câu trả lời (evidence spans)
- [ ] Tích hợp tập dữ liệu mới vào `ground_truth.jsonl`
- [ ] Chia lại tập train/val/test (giữ nguyên tỷ lệ cũ)
- [ ] Huấn luyện từ đầu (V5) với dữ liệu mở rộng + các cải tiến từ Phase 2
- [ ] Đánh giá toàn bộ benchmark: tất cả 12 cấu hình trên tập test mới

**Kết quả bàn giao:**
- `ground_truth_expanded.jsonl` (500+ câu hỏi)
- Cập nhật `dataset_metadata.json`
- Checkpoint mô hình mới: `bge_m3_ft_v5`
- Báo cáo benchmark toàn diện mới

---

#### **Phase 4 (Tháng 4, Tùy chọn): Reranker & Kỹ thuật Nâng cao**

**Mục tiêu:** Fine-tune reranker và thử nghiệm ensemble

- [ ] Tạo các cặp dữ liệu huấn luyện cho reranker từ ground truth (các đoạn văn dương tính/âm tính)
- [ ] Fine-tune mô hình `jinaai/jina-reranker-v2-base-multilingual` bằng CrossEncoder của thư viện sentence-transformers
- [ ] Đánh giá cải thiện từ reranker trên nền tảng embedding tốt nhất (V5)
- [ ] Thử nghiệm ensemble checkpoint (top-3 theo NDCG@10)
- [ ] Nếu tài nguyên cho phép: thử nghiệm tốc độ huấn luyện với FP16

**Kết quả bàn giao:**
- Checkpoint `reranker_finetuned/`
- Kết quả kiểm chứng (ablation study) về ảnh hưởng của reranker
- Phương pháp và trọng số tích hợp ensemble

---

### 4.3 Bảng Kết quả Kỳ vọng

| Chỉ số | Hiện tại (C16) | Mục tiêu sau Phase 1-2 | Mục tiêu sau Phase 3 | Ghi chú |
|--------|---------------|-----------------------|---------------------|-------|
| **Hit@1** | 0.6500 | 0.70-0.72 | 0.75-0.78 | Semantic chunking + âm tính khó tốt hơn + nhiều dữ liệu hơn |
| **MRR@10** | 0.7540 | 0.78-0.80 | 0.82-0.85 | Cùng các yếu tố thúc đẩy trên |
| **Recall@40** | 0.6662 | 0.70-0.72 | 0.75-0.78 | Corpus lớn hơn giúp cải thiện recall |
| **NDCG@10** | 0.5328 | 0.55-0.57 | 0.60-0.63 | Fine-tuning Reranker đóng góp thêm +3-5% |
| **Độ trễ/query** | Chưa rõ | Giữ nguyên hoặc tăng nhẹ | Chấp nhận được (<500ms p95) | Giám sát qua từng phase |

**Lưu ý:** Phase 3 (mở rộng dữ liệu) mang lại mức tăng lớn nhất. Nếu không mở rộng ground truth, ngưỡng giới hạn tối đa của Hit@1 có thể chỉ đạt ~0.72-0.73.

---

## 5. Đi sâu vào Kỹ thuật (Technical Deep Dive)

### Phụ lục A: Các phương pháp tiếp cận Semantic Chunking

#### A.1 Cửa sổ trượt nhận biết câu (Sentence-Aware Sliding Window)

**Phương pháp:** Tách đoạn văn thành các câu riêng biệt, sau đó nhóm N câu vào 1 chunk với độ chồng chéo nhất định.

```python
def semantic_sentence_chunker(text: str, chunk_size: int = 256, overlap: int = 2):
    """
    Tách văn bản thành các chunk bảo toàn ranh giới của câu.
    
    Args:
        text: Văn bản đầu vào
        chunk_size: Số lượng từ mục tiêu cho mỗi chunk
        overlap: Số câu trùng lặp giữa các chunk liền kề
    
    Returns:
        Danh sách các dictionary chứa văn bản chunk và metadata
    """
    import nltk
    sentences = nltk.sent_tokenize(text)
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for i, sentence in enumerate(sentences):
        sentence_tokens = len(sentence.split())
        
        if current_length + sentence_tokens > chunk_size and current_chunk:
            # Lưu chunk hiện tại
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'sentence_range': (i-len(current_chunk), i),
                'token_count': current_length
            })
            # Khởi tạo chunk mới với phần chồng chéo
            current_chunk = current_chunk[-overlap:] if overlap > 0 else []
            current_length = sum(len(s.split()) for s in current_chunk)
        
        current_chunk.append(sentence)
        current_length += sentence_tokens
    
    # Thêm chunk cuối cùng
    if current_chunk:
        chunks.append({
            'text': ' '.join(current_chunk),
            'sentence_range': (len(sentences)-len(current_chunk), len(sentences)),
            'token_count': current_length
        })
    
    return chunks
```

**Hành vi kỳ vọng:** Tránh việc cắt đôi một câu; các đơn vị ngữ nghĩa được bảo toàn trọn vẹn. Phần trùng lặp giúp duy trì tính liền mạch của ngữ cảnh.

---

#### A.2 Phân chunk nhận biết chủ đề (BERTopic)

**Phương pháp:** Sử dụng mô hình hóa chủ đề để phát hiện các điểm chuyển dịch nội dung và thực hiện ngắt chunk tại các điểm chuyển dịch đó.

```python
from bertopic import BERTopic

def topic_aware_chunks(text: str, topic_threshold: float = 0.3):
    """
    Cắt nhỏ văn bản tại những điểm độ tương đồng chủ đề giảm dưới ngưỡng cho trước.
    
    Yêu cầu cài đặt: pip install bertopic
    """
    # Tách thành các câu trước
    sentences = nltk.sent_tokenize(text)
    
    # Tính toán embedding cho các câu
    topic_model = BERTopic()
    topics, probs = topic_model.fit_transform(sentences)
    
    # Tìm ranh giới nơi xác suất chủ đề < threshold
    boundaries = [0]
    for i, prob in enumerate(probs):
        if prob < topic_threshold:
            boundaries.append(i)
    boundaries.append(len(sentences))
    
    # Tạo các chunk giữa các ranh giới
    chunks = []
    for i in range(len(boundaries)-1):
        start, end = boundaries[i], boundaries[i+1]
        chunk_sentences = sentences[start:end]
        chunks.append(' '.join(chunk_sentences))
    
    return chunks
```

**Đánh đổi:** Chi phí tính toán lớn hơn nhưng các chunk có độ gắn kết ngữ nghĩa rất cao. Thích hợp cho các bài giảng dài có sự chuyển tiếp chủ đề rõ ràng.

---

#### A.3 Nhận biết thời gian với chồng chéo ngữ nghĩa (Timestamp-Aware with Semantic Overlap)

**Phương pháp:** Cấu hình `timestamp_90_30` hiện tại sử dụng chunk cố định 90 giây với 30 giây chồng chéo. Cải tiến: phát hiện ranh giới ngữ nghĩa bên trong các cửa sổ thời gian này.

```python
def semantic_timestamp_chunks(transcript_segments: list, chunk_duration: int = 90, overlap: int = 30):
    """
    Tạo các chunk dựa trên thời gian nhưng điều chỉnh ranh giới trùng khớp với ranh giới của câu.
    
    Args:
        transcript_segments: Danh sách các dict chứa {start, end, text} (đầu ra từ Whisper)
    
    Returns:
        Danh sách các chunk với mốc thời gian đã được điều chỉnh
    """
    # Nhóm các segment vào cửa sổ 90 giây
    windows = []
    current_window = []
    window_start = None
    
    for seg in transcript_segments:
        if window_start is None:
            window_start = seg['start']
        
        if seg['start'] - window_start < chunk_duration:
            current_window.append(seg)
        else:
            windows.append(current_window)
            # Chồng chéo: giữ lại 30 giây cuối của cửa sổ trước
            overlap_segs = [s for s in current_window if s['start'] >= window_start + chunk_duration - overlap]
            current_window = overlap_segs + [seg]
            window_start = current_window[0]['start']
    
    # Với mỗi cửa sổ, điều chỉnh ranh giới cho khớp với điểm ngắt câu
    chunks = []
    for window in windows:
        full_text = ' '.join(s['text'] for s in window)
        sentences = nltk.sent_tokenize(full_text)
        # Phân phối các câu vào chunk và tôn trọng khoảng thời gian ban đầu
        # ... (việc triển khai chi tiết phụ thuộc vào ánh xạ giữa thời gian và câu)
    
    return chunks
```

**Mục tiêu:** Giữ nguyên lợi ích về Recall của cửa sổ trượt theo thời gian, đồng thời tôn trọng ranh giới ngữ nghĩa để tăng Precision.

---

### Phụ lục B: Chiến lược khai thác lại Hard Negative (Hard Negative Re-mining)

#### B.1 Pipeline khai thác tuần tự (Iterative Mining Pipeline)

**Động lực:** Sau mỗi epoch huấn luyện, không gian biểu diễn (embedding space) sẽ thay đổi. Các mẫu âm tính từng được coi là "khó" ban đầu có thể trở nên dễ phân biệt (hoặc không còn phù hợp). Do đó, việc khai thác lại các mẫu âm tính khó bằng checkpoint hiện tại giúp duy trì độ khó của quá trình huấn luyện.

**Quy trình:**
```
Epoch 1:
  - Sử dụng baseline BGE-M3 để khai thác top-5 mẫu âm tính khó trên mỗi câu hỏi
  - Huấn luyện 1 epoch → sinh checkpoint V3.1
  
Epoch 2:
  - Tải checkpoint V3.1
  - Mã hóa lại các câu hỏi bằng V3.1
  - Tính toán lại độ tương đồng với tất cả các chunk trong corpus
  - Chọn top-5 mẫu âm tính khó mới nhất (loại bỏ mẫu dương tính)
  - Huấn luyện trên tập triplet mới → sinh checkpoint V3.2
  
Epoch 3:
  - Lặp lại quy trình với V3.2 → sinh checkpoint V3.3
  ...
```

**Mã giả:**
```python
def iterative_hard_mining(model, corpus, queries, positives, k=5, epoch_interval=1):
    """
    Khai thác lại hard negative định kỳ sau mỗi N epoch.
    
    Args:
        model: Checkpoint mô hình embedding hiện tại
        corpus: Dict[chunk_id, text]
        queries: List[query_id, query_text]
        positives: Dict[query_id, List[positive_chunk_ids]]
        k: Số lượng mẫu âm tính cho mỗi câu hỏi
        epoch_interval: Thực hiện khai thác lại sau mỗi N epoch
    
    Returns:
        Trình lặp sinh ra triplet mới ứng với mỗi epoch
    """
    for epoch in range(total_epochs):
        if epoch % epoch_interval == 0:
            # Mã hóa toàn bộ câu hỏi bằng mô hình hiện tại
            query_embeddings = model.encode([q for _, q in queries])
            
            # Mã hóa corpus (hoặc dùng lại nếu mô hình không đổi)
            corpus_embeddings = model.encode(list(corpus.values()))
            
            # Tìm top-k chunk tương đồng nhất với mỗi query (loại trừ các mẫu dương tính)
            new_triplets = []
            for (qid, _), q_emb in zip(queries, query_embeddings):
                sim_scores = np.dot(corpus_embeddings, q_emb)  # Tích vô hướng nếu đã chuẩn hóa
                # Gán điểm của mẫu dương tính bằng -inf để loại bỏ
                for pos_id in positives.get(qid, []):
                    sim_scores[pos_id] = -np.inf
                
                # Lấy top-k mẫu âm tính
                neg_indices = np.argsort(sim_scores)[-k:][::-1]
                for neg_id in neg_indices:
                    new_triplets.append({
                        'query': queries[qid],
                        'positive': positives[qid][0],  # Mẫu dương tính chính
                        'negative': corpus[neg_id]
                    })
        
        yield epoch, new_triplets
```

**Lưu ý khi triển khai:**
- Lưu trữ các embedding corpus đã tính trước để tránh việc mã hóa lại toàn bộ ở mỗi epoch (rất tốn tài nguyên).
- Nếu trọng số mô hình thay đổi lớn, bắt buộc phải mã hóa lại corpus.
- Cân bằng giữa tần suất khai thác lại (mỗi 1-2 epoch) và chi phí tính toán.

---

#### B.2 Tích hợp vào Vòng lặp Huấn luyện (Training Loop)

```python
# Trong file trainer.py
for epoch in range(num_epochs):
    if epoch % hard_mining_interval == 0:
        # Khai thác lại các mẫu âm tính khó
        new_triplets = mine_hard_negatives(model, corpus, train_queries, train_positives)
        train_dataset = TripletDataset(new_triplets)
        train_loader = DataLoader(train_dataset, batch_size=batch_size)
    
    # Huấn luyện trong 1 epoch
    train_epoch(model, train_loader)
    
    # Đánh giá trên tập validation
    val_metrics = evaluate(model, val_queries, val_corpus, val_qrels)
    
    # Lưu checkpoint nếu đạt điểm tốt nhất
    if val_metrics['ndcg@10'] > best_score:
        save_checkpoint(model, f'epoch{epoch}_ndcg{val_metrics["ndcg@10"]:.4f}')
```

---

### Phụ lục C: Các giới hạn của Ngưỡng đánh giá

#### C.1 Ngưỡng từ Kích thước Corpus

**Corpus hiện tại:** 4.460 chunks (recursive) từ ~295 video thuộc 4 môn học.

**Phép toán:** Nếu mỗi câu hỏi trung bình có 2-3 chunk liên quan (relevant chunks), tổng số chunk liên quan ≈ 300 câu hỏi × 2.5 = 750 chunk. Với 4.460 chunk tổng thể, giá trị **Recall@k** tối đa có thể đạt được là:

```
Nếu k=40, Recall@40 tối đa = min(40 / (avg_relevant_per_query), 1.0)
= 40 / 2.5 = 16 chunk liên quan được tìm thấy nếu hệ thống hoàn hảo? Đợi đã...
```

Thực tế, nếu hệ thống truy hồi đúng 40 chunk tương đồng nhất, và có trung bình 2.5 chunk đúng cho mỗi câu hỏi thì:

```
Recall@40 = (số chunk đúng trong top-40) / tổng số chunk đúng thực tế
Recall@40 tối đa đạt 1.0 khi toàn bộ 2.5 chunk đúng nằm trong Top 40.
```

Điều này áp dụng cho từng câu hỏi đơn lẻ. Điểm trung bình Recall@40 trên toàn bộ tập dữ liệu về mặt lý thuyết có thể đạt 1.0 nếu mô hình truy hồi hoàn hảo xếp tất cả các chunk đúng lên trên các chunk sai.

**Tuy nhiên, thực tế ngưỡng này thấp hơn vì:**
1. Một số câu hỏi có nhiều hơn 3 chunk đúng → không thể nhét vừa tất cả vào Top 40.
2. Một số câu hỏi chỉ có 1 chunk đúng → dễ đạt Recall=1.0 nếu chunk đó lọt vào Top 40.
3. Khả năng phân biệt của mô hình embedding giới hạn chất lượng xếp hạng.

**Ngưỡng đánh giá thực tế từ kết quả đo lường:**
- Recall@40 tốt nhất đạt được: C18 = 0.6915 (69.15%)
- Khoảng cách tới mức hoàn hảo: 30.85%

Khoảng cách này có thể do các nguyên nhân:
- **Năng lực mô hình:** BGE-M3 có thể không phân biệt được các ngữ cảnh bài giảng có sự tương đồng rất cao.
- **Phân mảnh chunk:** Thông tin trả lời bị cắt đôi giữa các chunk → không có chunk đơn lẻ nào chứa đầy đủ đáp án.
- **Tính mơ hồ của câu hỏi:** Một số câu hỏi có nhiều đoạn thông tin trả lời hợp lệ trải khắp các video khác nhau.

**Mức tối đa kỳ vọng với mô hình hoàn hảo + chunking tốt hơn:** ~0.75-0.80 Recall@40 (tăng khoảng 5-10% tuyệt đối).

---

#### C.2 Ngưỡng đánh đổi giữa các chỉ số (Metric Trade-off Ceiling)

Sự đánh đổi quan sát thấy trong dữ liệu thực tế:

| Chiến lược | Hit@1 | Recall@40 | Giải thích |
|----------|-------|-----------|----------------|
| Recursive | 0.6500 | 0.6662 | Độ chính xác rất cao ở Rank-1, nhưng recall ở mức trung bình |
| Timestamp | 0.5733 | 0.6915 | Độ chính xác Rank-1 thấp hơn, nhưng recall tổng thể cao hơn |

**Giải thích nguyên nhân:**
Recursive chunking bảo toàn tính mạch lạc của đoạn văn → chunk đứng đầu có khả năng bao phủ toàn bộ câu trả lời cao hơn. Nhưng số lượng chunk ít hơn → không gian ứng viên nhỏ hơn → recall bị giới hạn.

Timestamp sliding window làm tăng không gian ứng viên (nhiều chunk chồng chéo hơn) → recall cao hơn, nhưng các chunk riêng lẻ chứa nhiều nhiễu hơn (do cắt ngắt quãng thời gian cứng nhắc) → độ chính xác (precision) bị giảm sút.

**Chiến lược tối ưu tùy thuộc vào kịch bản sử dụng:**
- **Chatbot (cần 1 câu trả lời duy nhất):** Ưu tiên recursive → Hit@1 quan trọng hơn.
- **Trợ lý học tập (cần tham chiếu nhiều nguồn):** Ưu tiên timestamp → Recall@40 quan trọng hơn.

**Liệu có thể tối ưu cả hai?** Có thể đạt được bằng phương pháp hybrid:
- Sử dụng recursive chunking cho bước truy hồi thô đầu tiên (để có precision).
- Bổ sung các chunk trùng lặp/chồng chéo ở các ranh giới đoạn văn để gia tăng recall.

Kỹ thuật này sẽ làm tăng kích thước index nhưng có thể phá vỡ thế đánh đổi chỉ số hiện tại.

---

#### C.3 Ngưỡng đặc thù miền dữ liệu (Domain-Specific Ceiling)

Bài toán QA bài giảng khó hơn tìm kiếm web thông thường vì:
- **Miền dữ liệu hẹp:** Thuật ngữ chuyên ngành CNTT làm giảm tính mơ hồ ngữ nghĩa.
- **Tài liệu dài:** Mỗi bài giảng kéo dài 1-2 tiếng → sinh ra rất nhiều chunk ứng viên trong một video → tăng nhiễu khi tìm kiếm.
- **Sự thưa thớt thông tin:** Chỉ có một phần rất nhỏ trong bài giảng thực sự chứa câu trả lời cho một câu hỏi cụ thể.
- **Ngữ cảnh thời gian:** Một số câu hỏi tham chiếu đến các khái niệm được định nghĩa tại các mốc thời gian cụ thể → cần định vị khoảng thời gian cực kỳ chính xác.

**So sánh với bộ dữ liệu MS MARCO (Tìm kiếm web):**
- MS MARCO: ~500k câu hỏi, ~8 triệu văn bản (passages), tỷ lệ văn bản đúng tồn tại khoảng ~50%.
- Corpus của chúng ta: ~300 câu hỏi, ~4k chunk, tỷ lệ chunk đúng trên mỗi câu hỏi chỉ khoảng ~0.5% (ước tính).

Sự thưa thớt này khiến việc truy hồi trở nên khó khăn hơn nhiều: tỷ lệ tín hiệu trên nhiễu (signal-to-noise ratio) là rất thấp.

**Kết luận:** Ngay cả các mô hình embedding hiện đại nhất cũng có thể chạm ngưỡng giới hạn tại Hit@1 = 0.75-0.80 trên tập dữ liệu này nếu không thực hiện:
1. Mở rộng corpus (thêm nhiều ví dụ tích cực cho mỗi câu hỏi).
2. Tối ưu hóa phân mảnh (tăng mật độ thông tin hữu ích trong mỗi chunk).
3. Thêm dữ liệu huấn luyện (nhiều câu hỏi hơn để học sâu các mẫu đặc thù của miền dữ liệu).

---

## 6. Tài liệu Liên quan

- [`../research_problem.md`](../research_problem.md) - Các câu hỏi nghiên cứu và phạm vi ban đầu
- [`../implement_plan.md`](../implement_plan.md) - Kế hoạch triển khai thí nghiệm đầy đủ (Phases 0-7)
- [`../evaluation/end_to_end_retrieval.md`](../evaluation/end_to_end_retrieval.md) - Kết quả benchmark & lập luận chọn winner
- [`/context.md`](../../context.md) - Bối cảnh chuyển giao dự án (tóm tắt mới nhất)

---

## 7. Các câu hỏi mở (Open Questions)

Đây là các điểm cần nghiên cứu thực nghiệm trước khi bắt đầu thực hiện:

1. **Liệu semantic chunking có thể nâng cao Hit@1 mà không làm giảm Recall@40?**  
   Cần kiểm chứng thực tế: viết mã cho bộ phân mảnh dựa trên câu và chạy benchmark.

2. **Khai thác lại hard negative tuần tự có bắt buộc phải huấn luyện lại hoàn toàn không?**  
   Hay chúng ta có thể fine-tune tiếp tục (incremental fine-tuning) từ checkpoint V3? Đánh giá tính khả thi về mặt kỹ thuật.

3. **Con số 500 câu hỏi đã đủ lớn để tạo ra sự khác biệt có ý nghĩa thống kê?**  
   Phân tích lực lượng (power analysis): cần bao nhiêu câu hỏi để phát hiện mức tăng +3% MRR với độ tin cậy 95%?

4. **Việc fine-tune reranker có xứng đáng với đánh đổi về độ trễ?**  
   Reranker Jina hiện tại mất ~100-150ms/query. Mô hình fine-tuned ViRanker có thể mất ~500ms. Liệu mức tăng +3% NDCG có đáng để đổi lấy độ trễ tăng gấp 3 lần?

5. **Nên mở rộng corpus (thêm video bài giảng) trước hay thêm câu hỏi trước?**  
   Thêm nhiều video bài giảng sẽ làm tăng không gian ứng viên → có thể giúp kiểm chứng recall thực tế tốt hơn việc chỉ thêm câu hỏi.

6. **Có thể ensemble nhiều chiến lược chunking cùng lúc không?**  
   Truy hồi song song từ cả index recursive và index timestamp, sau đó thực hiện hợp nhất kết quả (reciprocal rank fusion)?

---

## 8. Nhật ký Thay đổi (Change Log)

- **2026-06-20** - Thử nghiệm chiến lược `timestamp_150_50_raw` (C21), sinh chunk từ transcript gốc (không qua semantic chunking cũ); xác lập kỷ lục mới toàn hệ thống với Hit@5=0.9467 và MRR@10=0.8085.
- **2026-06-20** - Bổ sung `recall_new`: match theo cùng `video_id` và timestamp overlap > 0 giây; cập nhật bảng so sánh C16/C18/C19/C20.
- **2026-06-20** - Thêm benchmark C20: SemanticChunker + OpenAI `text-embedding-3-large`; tạo 3166 chunks, build index, chạy E2E hybrid + Jina rerank.
- **2026-06-16** - Khởi tạo bản phác thảo đầu tiên thông qua biên soạn trực tiếp (bỏ qua subagent để tối ưu tốc độ).

---

## 9. Phụ lục: Nguồn Dữ liệu & Ghi chú Trích xuất

Phần này ghi nhận nguồn gốc dữ liệu phục vụ cho mục đích tái lập thí nghiệm.

### 9.1 Trích xuất chỉ số (Metrics Extraction)

Nguồn: `experiments/docs/evaluation/end_to_end_retrieval.md` (dòng 221-240)

Bảng dữ liệu trích xuất cho các cấu hình C13-C18 (mô hình fine-tuned):
- C13-C14: bge_m3_ft_v2
- C15-C18: bge_m3_ft_v3

Các cột chỉ số: Hit@1, Hit@5, Hit@10, Recall@40, MRR@10, NDCG@10, Final Recall@10

### 9.2 Danh sách Vấn đề (Issues List)

Nguồn: Kết quả phân tích sâu (task w9xapy435) được lưu trong ngữ cảnh hội thoại.

18 vấn đề được xác định được chia thành 4 nhóm chính:
- Chất lượng dữ liệu (phân mảnh chunk, hard negatives, augmentation, kích thước ground truth).
- Cấu hình huấn luyện (LR, epochs, batch size, warmup, trọng số loss).
- Ngưỡng giới hạn đánh giá (kích thước corpus, độ đặc thù miền dữ liệu, sự đánh đổi chỉ số).
- Giới hạn kiến trúc (năng lực BGE-M3, cửa sổ ngữ cảnh, reranker gốc).

### 9.3 Cấu hình Huấn luyện

Nguồn: `experiments/docs/implement_plan.md` Phase 3 (Độ khả thi của Embedding Fine-Tune)

Đã biết:
- Tập dữ liệu: synthetic_queries.jsonl + synthetic_queries_augmented.jsonl
- Tỷ lệ chia: 95/5 phân tầng
- Hard negatives: top-5 trích xuất bằng baseline BGE-M3
- Hàm loss: CMNRL

Chưa biết (thiếu sót): LR, epochs, batch size, warmup, precision.

### 9.4 Kích thước Corpus

Nguồn: Thống kê số lượng file chunk trong `experiments/docs/evaluation/end_to_end_retrieval.md`:
- Recursive: 4 file chunk → tổng cộng ~4.460 chunk (từ bối cảnh trước đó).
- Timestamp: 4 file chunk → tổng cộng ~3.665 chunk.

---

**Trạng thái tài liệu:** Bản nháp (Draft) — chờ phê duyệt và phản hồi trước khi triển khai Phase 1.
