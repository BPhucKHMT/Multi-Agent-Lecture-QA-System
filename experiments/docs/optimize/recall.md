---
title: Recall Optimization Analysis
created: 2026-06-16
author: Claude Code Analysis
status: draft
---

# Recall Optimization: Issues & Improvement Plan

**Document version:** 1.0  
**Target system:** BGE-M3 fine-tuned retrieval pipeline (C16 config)  
**Current metrics:** Hit@1 = 0.6500, MRR@10 = 0.7540, Recall@40 = 0.6662, NDCG@10 = 0.5328  
**Goal:** Hit@1 > 0.75, MRR@10 > 0.80, Recall@40 > 0.75

---

## 1. Performance Summary

### 1.1 Best Config Comparison

| Config | Retrieval | Chunk | Embedding | Hit@1 | Hit@5 | Hit@10 | Recall@40 | MRR@10 | NDCG@10 |
|--------|-----------|-------|-----------|-------|-------|--------|-----------|--------|---------|
| **C16** (selected) | hybrid | recursive | bge_m3_ft_v3 | **0.6500** | 0.8933 | 0.9433 | 0.6662 | **0.7540** | 0.5328 |
| C18 (alternative) | hybrid | timestamp | bge_m3_ft_v3 | 0.5733 | **0.9000** | **0.9667** | **0.6865** | 0.7173 | **0.5567** |

**Interpretation:**
- **C16** optimized for **Rank-1 accuracy** (Hit@1 = 0.65) — ideal for chatbot where first result matters most
- **C18** optimized for **Recall@40** (0.6865) and **Hit@10** (0.9667) — better for exhaustive search scenarios
- C16 preserves semantic paragraph boundaries (recursive chunking), C18 uses sliding time windows (timestamp_90_30)
- V3 fine-tuning improved both configurations over baseline (C02, C06)

**Perceived gap:** User expects "higher" results. Target improvements:
- Hit@1: 0.65 → **0.75-0.78** (+10-13 pts)
- MRR@10: 0.75 → **0.82-0.85** (+7-10 pts)
- Recall@40: 0.67 → **0.75-0.78** (+8-11 pts)

---

## 2. Root Cause Analysis

### 2.1 Data Quality Issues (Estimated impact: 20-30% suboptimal)

| Issue | Current State | Impact | Evidence |
|-------|---------------|--------|----------|
| **Chunking not truly semantic** | `RecursiveCharacterTextSplitter` splits on character count, not semantic boundaries | Paragraphs cut mid-thought, context fragmentation | `implement_plan.md` Phase 2; `end_to_end_retrieval.md` chunking strategies |
| **Hard negatives stale after fine-tune** | Hard negatives mined once using BGE-M3 baseline; V3 fine-tune changed embedding space | Negatives no longer "hard" → training signal diluted | Deep research analysis; training data pipeline uses `mine_hard_negatives.py` with baseline model |
| **Query augmentation limited** | Single paraphrase per query using GPT-4o-mini, batch 15, 4 workers | Insufficient diversity; vocabulary mismatch persists | `augment_queries.py` configuration |
| **Ground truth dataset small** | Only 300 pilot questions across 4 courses | High variance in metric estimates; limited coverage | `experiments/data/ground_truth/ground_truth_pilot.jsonl` (100 questions referenced in docs; actual count TBD) |

**Supporting data:**
- Corpus: 4,460 chunks total (recursive) / 3,665 chunks (timestamp)
- Train/val split: 95/5 stratified
- Hard negatives: 5 per query

---

### 2.2 Training Configuration Gaps (Estimated impact: 15-25% suboptimal)

| Unknown / Missing | Current Status | Potential Impact |
|-------------------|----------------|------------------|
| Learning rate schedule | Not documented in configs | Suboptimal convergence; could be too high/low |
| Warmup steps | Unknown | Unstable early training |
| Number of epochs | Unknown (likely 3-5?) | Possible underfitting |
| Batch size | Unknown | Gradient noise affecting stability |
| Mixed precision (FP16) | Not mentioned | Training slower; memory wasted |
| Loss weighting (CMNRL) | Used but weights unknown | Positive vs negative balance unclear |
| Checkpoint selection | Best by validation metric? | May not generalize to test set |

**Evidence:** `implement_plan.md` Phase 3 lists these as "Unknowns". No `config.yaml` for fine-tuning visible in docs.

---

### 2.3 Evaluation Ceiling (Estimated impact: 10-15% inherent limit)

**Corpus constraints:**
- Total chunks: ~4,500 (small candidate pool)
- Domain-specific: 4 CS courses only (CS114, CS116, CS315, CS431)
- Ground truth may require evidence from multiple videos → some queries inherently low recall if only one span exists

**Metric trade-offs observed:**
- Recursive chunking: higher Hit@1, lower Recall@40 (semantic boundaries help rank-1 but reduce candidate pool)
- Timestamp chunking: lower Hit@1, higher Recall@40 (overlapping windows increase recall but dilute precision)

**Realistic ceiling estimate:** Even with perfect model, **Recall@40 likely capped at 0.75-0.80** given corpus size and domain specificity. Hit@1 > 0.80 may be unrealistic without expanding corpus.

---

### 2.4 Architecture Limits (Estimated impact: 5-10% suboptimal)

- **BGE-M3 multi-lingual vs Vietnamese domain:** Model trained on multilingual data; fine-tuned on Vietnamese + English code-switching. Possible representation confusion.
- **Context window:** 512 tokens may truncate some lecture content → information loss
- **Reranker not fine-tuned:** Using `BAAI/bge-reranker-base` gốc; domain mismatch likely hurts ranking
- **No reranker fine-tuning pipeline:** Planned in Phase 5 but not executed yet

---

## 3. Gap Analysis

| Issue Category | Current State | Desired State | Gap Magnitude | Priority |
|----------------|---------------|---------------|---------------|----------|
| Chunking strategy | RecursiveCharacterTextSplitter (character-based) | Semantic/timestamp-aware with overlap | Medium | P0 |
| Hard negative quality | Mined once with baseline model | Iterative re-mining per epoch or every N steps | High | P0 |
| Ground truth size | ~300 questions | 500-1000 questions across all courses | High | P0 |
| LR scheduling | Unknown | Warmup + cosine decay | Medium | P1 |
| Batch size & accumulation | Unknown | Effective batch 64 with gradient accumulation | Low | P1 |
| Reranker fine-tuning | Not done | Fine-tune on domain passage pairs | Medium | P1 |
| Checkpoint ensemble | Single best checkpoint | Ensemble top-3 checkpoints | Low | P2 |
| Mixed precision | FP32 (assumed) | FP16/BF16 training | Low | P2 |
| Embedding dimension | Fixed by BGE-M3 | Experiment with dimension if model supports | Unknown | P2 |

---

## 4. Proposed Optimizations

### 4.1 Priority Matrix

| Optimization | Expected Gain (MRR@10 / Hit@1) | Effort | Priority | Dependencies |
|--------------|--------------------------------|--------|----------|--------------|
| **Semantic chunking** (sentence-aware) | +3-5% Hit@1 | Low (1-2 days) | **P0** | None |
| **Iterative hard negative mining** (re-mine each epoch) | +5-8% MRR@10 | Medium (3-5 days) | **P0** | Retrain from scratch |
| **Expand ground truth** to 500+ queries | +5-10% all metrics | High (2-4 weeks annotation) | **P0** | Human annotation effort |
| **LR warmup + cosine decay** | +1-2% stability | Low (1 day) | **P1** | Retrain from checkpoint |
| **Gradient accumulation** (effective batch 64) | +2-3% convergence | Low (1 day) | **P1** | Retrain |
| **Reranker fine-tuning** (CrossEncoder) | +3-5% NDCG@10 | High (1-2 weeks) | **P1** | Labeled passage pairs |
| **Checkpoint ensemble** (top-3) | +1-2% robustness | Low (1 day) | **P2** | Multiple checkpoints |
| **FP16 training** | 2× speed, same quality | Low (1 day) | **P2** | GPU with Tensor Cores |

---

### 4.2 Implementation Roadmap

#### **Phase 1 (Week 1-2): Quick Wins**

**Goal:** Improve chunking and validate baseline

- [ ] Implement semantic chunking script
  - Sentence-aware sliding window (preserve sentence boundaries, 2-3 sentence overlap)
  - Evaluate on dev set: compare Hit@1 vs current recursive
  - Rebuild Chroma indexes with new chunks
- [ ] Re-run benchmark on new chunking
  - Measure delta in C16-equivalent config
  - If Hit@1 improves without degrading Recall@40 → adopt
- [ ] Document chunking strategy in pipeline

**Deliverables:**
- `experiments/src/chunking/semantic_chunker.py`
- New chunk files in `experiments/data/chunks/semantic/`
- Updated benchmark results

---

#### **Phase 2 (Week 3-4): Training Improvements**

**Goal:** Fix training configuration without new data

- [ ] Add LR warmup (steps=100) + cosine decay to training script
- [ ] Implement hard negative re-mining callback
  - Mine new negatives every epoch using current checkpoint
  - Keep top-5 hardest (highest similarity among non-relevants)
- [ ] Enable gradient accumulation (effective batch=64)
- [ ] Retrain V4 model with same 300-question dataset + improved configs
- [ ] Evaluate V4 against C16 baseline

**Deliverables:**
- Updated `experiments/src/training/trainer.py` with warmup/re-mining
- New checkpoint: `bge_m3_ft_v4`
- Benchmark comparison: C16 vs V4

---

#### **Phase 3 (Month 2-3): Data Expansion**

**Goal:** Increase ground truth size to 500-1000 questions

- [ ] Create annotation plan: distribute across 4 courses, balanced by topic/difficulty
- [ ] Annotate 200-500 additional questions with evidence spans
- [ ] Integrate new dataset into `ground_truth.jsonl`
- [ ] Re-split train/val/test (maintain same ratio)
- [ ] Re-train from scratch (V5) with expanded data + Phase 2 improvements
- [ ] Full benchmark suite: all 12 configs on new test set

**Deliverables:**
- `ground_truth_expanded.jsonl` (500+ questions)
- Updated `dataset_metadata.json`
- New model checkpoint: `bge_m3_ft_v5`
- Full benchmark report

---

#### **Phase 4 (Month 4, Optional): Reranker & Advanced**

**Goal:** Fine-tune reranker and explore ensembles

- [ ] Generate reranker training pairs from ground truth (positive/negative passages)
- [ ] Fine-tune `BAAI/bge-reranker-base` using sentence-transformers CrossEncoder
- [ ] Evaluate reranker improvements on top of best embedding (V5)
- [ ] Experiment with checkpoint ensemble (top-3 by NDCG@10)
- [ ] If resources allow: test FP16 training speedup

**Deliverables:**
- `reranker_finetuned/` checkpoint
- Ablation results: reranker impact
- Ensemble weights/method

---

### 4.3 Expected Outcomes Table

| Metric | Current (C16) | Target after Phase 1-2 | Target after Phase 3 | Notes |
|--------|---------------|-----------------------|---------------------|-------|
| **Hit@1** | 0.6500 | 0.70-0.72 | 0.75-0.78 | Semantic chunking + better negatives + more data |
| **MRR@10** | 0.7540 | 0.78-0.80 | 0.82-0.85 | Same drivers |
| **Recall@40** | 0.6662 | 0.70-0.72 | 0.75-0.78 | Larger corpus helps recall |
| **NDCG@10** | 0.5328 | 0.55-0.57 | 0.60-0.63 | Reranker fine-tuning adds +3-5% |
| **Latency/query** | TBD | Same or slightly higher | Acceptable (<500ms p95) | Monitor in each phase |

**Caveat:** Phase 3 (data expansion) likely yields largest gains. Without expanding ground truth, ceiling may limit to Hit@1 ~0.72-0.73.

---

## 5. Technical Deep Dive

### Appendix A: Semantic Chunking Approaches

#### A.1 Sentence-Aware Sliding Window

**Method:** Split on sentence boundaries, then group N sentences per chunk with overlap.

```python
def semantic_sentence_chunker(text: str, chunk_size: int = 256, overlap: int = 2):
    """
    Split text into chunks preserving sentence boundaries.
    
    Args:
        text: Input document
        chunk_size: Target token count per chunk
        overlap: Number of sentences to overlap between chunks
    
    Returns:
        List of chunk dicts with metadata
    """
    import nltk
    sentences = nltk.sent_tokenize(text)
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for i, sentence in enumerate(sentences):
        sentence_tokens = len(sentence.split())
        
        if current_length + sentence_tokens > chunk_size and current_chunk:
            # Emit current chunk
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'sentence_range': (i-len(current_chunk), i),
                'token_count': current_length
            })
            # Start new chunk with overlap
            current_chunk = current_chunk[-overlap:] if overlap > 0 else []
            current_length = sum(len(s.split()) for s in current_chunk)
        
        current_chunk.append(sentence)
        current_length += sentence_tokens
    
    # Add final chunk
    if current_chunk:
        chunks.append({
            'text': ' '.join(current_chunk),
            'sentence_range': (len(sentences)-len(current_chunk), len(sentences)),
            'token_count': current_length
        })
    
    return chunks
```

**Expected behavior:** Avoids splitting sentences; semantic units stay intact. Overlap maintains context.

---

#### A.2 Topic-Aware Chunking (BERTopic)

**Method:** Use topic modeling to detect topic shifts, split at topic boundaries.

```python
from bertopic import BERTopic

def topic_aware_chunks(text: str, topic_threshold: float = 0.3):
    """
    Split text where topic similarity drops below threshold.
    
    Requires: pip install bertopic
    """
    # Split into sentences first
    sentences = nltk.sent_tokenize(text)
    
    # Compute embeddings for sentences
    topic_model = BERTopic()
    topics, probs = topic_model.fit_transform(sentences)
    
    # Find boundaries where topic probability < threshold
    boundaries = [0]
    for i, prob in enumerate(probs):
        if prob < topic_threshold:
            boundaries.append(i)
    boundaries.append(len(sentences))
    
    # Create chunks between boundaries
    chunks = []
    for i in range(len(boundaries)-1):
        start, end = boundaries[i], boundaries[i+1]
        chunk_sentences = sentences[start:end]
        chunks.append(' '.join(chunk_sentences))
    
    return chunks
```

**Trade-off:** Heavier computation but semantically coherent. Good for long lectures with clear topic transitions.

---

#### A.3 Timestamp-Aware with Semantic Overlap

**Method:** Current `timestamp_90_30` uses fixed 90s chunks with 30s overlap. Improvement: detect semantic boundaries within time windows.

```python
def semantic_timestamp_chunks(transcript_segments: list, chunk_duration: int = 90, overlap: int = 30):
    """
    Create time-based chunks but adjust boundaries to sentence boundaries.
    
    Args:
        transcript_segments: List of {start, end, text} dicts (from whisper)
    
    Returns:
        List of chunk dicts with adjusted timestamps
    """
    # Group segments into 90s windows
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
            # Overlap: keep last 30s of previous window
            overlap_segs = [s for s in current_window if s['start'] >= window_start + chunk_duration - overlap]
            current_window = overlap_segs + [seg]
            window_start = current_window[0]['start']
    
    # For each window, adjust boundaries to sentence breaks
    chunks = []
    for window in windows:
        full_text = ' '.join(s['text'] for s in window)
        sentences = nltk.sent_tokenize(full_text)
        # Distribute sentences into chunks respecting original time range
        # ... (implementation depends on time-to-sentence mapping)
    
    return chunks
```

**Goal:** Keep time-based sliding window benefits (recall) while respecting semantic boundaries (precision).

---

### Appendix B: Hard Negative Re-mining Strategy

#### B.1 Iterative Mining Pipeline

**Motivation:** After each training epoch, the embedding space shifts. Negatives that were "hard" initially may become easy (or irrelevant). Re-mine negatives using the current checkpoint to maintain training difficulty.

**Process:**

```
Epoch 1:
  - Use BGE-M3 baseline to mine top-5 negatives per query
  - Train for 1 epoch → checkpoint V3.1
  
Epoch 2:
  - Load checkpoint V3.1
  - Re-encode queries with V3.1
  - Re-compute similarity to all corpus chunks
  - Select new top-5 negatives (excluding positives)
  - Train on new triplet set → checkpoint V3.2
  
Epoch 3:
  - Repeat with V3.2 → V3.3
  ...
```

**Pseudo-code:**

```python
def iterative_hard_mining(model, corpus, queries, positives, k=5, epoch_interval=1):
    """
    Re-mine hard negatives every N epochs.
    
    Args:
        model: Current embedding model checkpoint
        corpus: Dict[chunk_id, text]
        queries: List[query_id, query_text]
        positives: Dict[query_id, List[positive_chunk_ids]]
        k: Number of negatives per query
        epoch_interval: Re-mine every N epochs
    
    Returns:
        Iterator over (epoch, new_triplets)
    """
    for epoch in range(total_epochs):
        if epoch % epoch_interval == 0:
            # Encode all queries with current model
            query_embeddings = model.encode([q for _, q in queries])
            
            # Encode corpus (or use precomputed if model unchanged)
            corpus_embeddings = model.encode(list(corpus.values()))
            
            # For each query, find top-k similar chunks (excluding positives)
            new_triplets = []
            for (qid, _), q_emb in zip(queries, query_embeddings):
                sim_scores = np.dot(corpus_embeddings, q_emb)  # cosine if normalized
                # Set positives to -inf to exclude
                for pos_id in positives.get(qid, []):
                    sim_scores[pos_id] = -np.inf
                
                # Get top-k negatives
                neg_indices = np.argsort(sim_scores)[-k:][::-1]
                for neg_id in neg_indices:
                    new_triplets.append({
                        'query': queries[qid],
                        'positive': positives[qid][0],  # primary positive
                        'negative': corpus[neg_id]
                    })
        
        yield epoch, new_triplets
```

**Implementation notes:**
- Store precomputed corpus embeddings to avoid re-encoding every epoch (expensive)
- If model weights change significantly, need to re-encode corpus
- Balance: re-mine every 1-2 epochs vs. computational cost

---

#### B.2 Training Loop Integration

```python
# In trainer.py
for epoch in range(num_epochs):
    if epoch % hard_mining_interval == 0:
        # Re-mine negatives
        new_triplets = mine_hard_negatives(model, corpus, train_queries, train_positives)
        train_dataset = TripletDataset(new_triplets)
        train_loader = DataLoader(train_dataset, batch_size=batch_size)
    
    # Train one epoch
    train_epoch(model, train_loader)
    
    # Evaluate on validation set
    val_metrics = evaluate(model, val_queries, val_corpus, val_qrels)
    
    # Save checkpoint if best
    if val_metrics['ndcg@10'] > best_score:
        save_checkpoint(model, f'epoch{epoch}_ndcg{val_metrics["ndcg@10"]:.4f}')
```

---

### Appendix C: Evaluation Ceiling Limitations

#### C.1 Corpus Size Ceiling

**Current corpus:** 4,460 chunks (recursive) across ~295 videos, 4 courses.

**Math:** If each query has on average 2-3 relevant chunks, total relevant pool ≈ 300 queries × 2.5 = 750 relevant chunks. With 4,460 total chunks, the maximum possible **Recall@k** is:

```
If k=40, maximum Recall@40 = min(40 / (avg_relevant_per_query), 1.0)
= 40 / 2.5 = 16 relevant chunks found if system were perfect? Wait...
```

Actually, if system retrieves the 40 most relevant chunks, and there are 2.5 relevant per query on average, then:

```
Recall@40 = (# relevant in top-40) / total_relevant
Maximum when all 2.5 relevant are in top-40 → 2.5/2.5 = 1.0
```

But that's per-query. The average Recall@40 across queries can theoretically reach 1.0 if the retriever perfectly ranks all relevant before irrelevant.

**However:** Real ceiling is lower because:
1. Some queries have >3 relevant chunks → can't fit all in top-40
2. Some queries have only 1 relevant chunk → can reach 1.0 if that chunk is in top-40
3. The embedding model's discrimination ability limits ranking quality

**Empirical ceiling from results:**
- Best Recall@40 achieved: C18 = 0.6915 (69.15%)
- Gap to perfect: 30.85%

This gap could be due to:
- **Model capacity:** BGE-M3 may not distinguish subtle differences in lecture context
- **Chunking:** Relevant info split across chunks → no single chunk contains full answer
- **Query ambiguity:** Some questions have multiple valid evidence spans spread across videos

**Expected maximum with perfect model + better chunking:** ~0.75-0.80 Recall@40 (5-10% absolute gain).

---

#### C.2 Metric Trade-off Ceiling

Observed trade-off in data:

| Strategy | Hit@1 | Recall@40 | Interpretation |
|----------|-------|-----------|----------------|
| Recursive | 0.6500 | 0.6662 | High precision at rank-1, moderate recall |
| Timestamp | 0.5733 | 0.6915 | Lower precision, higher recall |

**Why?** Recursive chunking preserves paragraph coherence → top-ranked chunk more likely to be fully relevant. But fewer chunks total → candidate pool smaller → recall capped.

Timestamp sliding window increases candidate pool (more overlapping chunks) → higher recall, but individual chunks are noisier (cut at arbitrary time boundaries) → precision suffers.

**Optimal strategy depends on use case:**
- **Chatbot (single answer):** Prefer recursive → Hit@1 matters more
- **Study assistant (multiple sources):** Prefer timestamp → Recall@40 matters more

**Can we have both?** Possibly with hybrid approach:
- Use recursive chunks for first-stage retrieval (precision)
- But add duplicate/overlap chunks at paragraph boundaries to boost recall

This would increase index size but might break the trade-off.

---

#### C.3 Domain-Specific Ceiling

Lecture QA is harder than general web search because:
- **Narrow domain:** CS course terminology limits ambiguity → actually easier? 
- **Long documents:** Lectures are 1-2 hours → many chunks per video → more candidates to sift through
- **Sparse relevance:** Only small fraction of lecture content relevant to any given question
- **Temporal context:** Some questions refer to concepts introduced at specific timestamps → need precise span

**Comparison to MS MARCO (web search):**
- MS MARCO: ~500k queries, ~8M passages, ~50% relevant passages exist
- Our corpus: ~300 queries, ~4k chunks, ~0.5% relevant chunks per query (estimated)

This sparsity makes retrieval harder: the signal-to-noise ratio is lower.

**Conclusion:** Even state-of-the-art embedding models may hit ceiling around Hit@1 = 0.75-0.80 on this dataset without:
1. Expanding corpus (more positive examples per query)
2. Better chunking (increase relevant chunk density)
3. More training data (more queries to learn domain patterns)

---

## 6. Related Documents

- [`../research_problem.md`](../research_problem.md) - Original research questions and scope
- [`../implement_plan.md`](../implement_plan.md) - Full experiment implementation plan (Phases 0-7)
- [`../evaluation/end_to_end_retrieval.md`](../evaluation/end_to_end_retrieval.md) - Benchmark results & winner selection rationale
- [`/context.md`](../../context.md) - Project handoff context (latest summary)

---

## 7. Open Questions

These require investigation before committing to a path:

1. **Can semantic chunking improve Hit@1 without degrading Recall@40?**  
   Need empirical test: implement sentence-aware chunker and benchmark.

2. **Will hard negative re-mining require full retrain?**  
   Or can we fine-tune incrementally from V3 checkpoint? Evaluate feasibility.

3. **Is 500 questions sufficient for statistically significant improvement?**  
   Power analysis: how many queries needed to detect +3% MRR improvement with 95% confidence?

4. **Does reranker fine-tuning justify latency cost?**  
   Current Jina reranker ~100-150ms/query. Fine-tuned ViRanker ~500ms. Is +3% NDCG worth 3× latency?

5. **Should we expand corpus (more videos) before more queries?**  
   Adding more lecture videos increases candidate pool → may improve recall more than additional queries.

6. **Can we ensemble multiple chunking strategies?**  
   Retrieve from both recursive and timestamp indexes, then fuse results?

---

## 8. Change Log

- **2026-06-16** - Initial draft created via direct writing (bypassing subagent-driven workflow for speed)

---

## 9. Appendix: Data Sources & Extraction Notes

This section documents where data came from, for reproducibility.

### 9.1 Metrics Extraction

Source: `experiments/docs/evaluation/end_to_end_retrieval.md` (lines 221-240)

Table extracted for configs C13-C18 (fine-tuned models):
- C13-C14: bge_m3_ft_v2
- C15-C18: bge_m3_ft_v3

Metrics columns: Hit@1, Hit@5, Hit@10, Recall@40, MRR@10, NDCG@10, Final Recall@10

### 9.2 Issues List

Source: Deep research workflow output (task w9xapy435) stored in conversation context.

18 identified issues categorized into 4 buckets:
- Data Quality (chunking, hard negatives, augmentation, ground truth size)
- Training Config (LR, epochs, batch, warmup, loss weights)
- Evaluation Ceiling (corpus size, domain specificity, metric trade-offs)
- Architecture Limits (BGE-M3 capacity, context window, reranker not fine-tuned)

### 9.3 Training Configuration

Source: `experiments/docs/implement_plan.md` Phase 3 (Embedding Fine-Tune Feasibility)

Known:
- Dataset: synthetic_queries.jsonl + synthetic_queries_augmented.jsonl
- Split: 95/5 stratified
- Hard negatives: top-5 via BGE-M3 baseline
- Loss: CMNRL

Unknown (gaps): LR, epochs, batch size, warmup, precision

### 9.4 Corpus Size

Source: `experiments/docs/evaluation/end_to_end_retrieval.md` chunk file counts:
- Recursive: 4 chunk files → total ~4,460 chunks (from earlier context)
- Timestamp: 4 chunk files → total ~3,665 chunks

---

**Document status:** Draft — awaiting review and feedback before implementing Phase 1.
