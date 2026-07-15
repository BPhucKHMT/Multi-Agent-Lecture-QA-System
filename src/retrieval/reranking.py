import os
import torch
import yaml
from typing import List
from transformers import AutoTokenizer, AutoModelForSequenceClassification

'''
hybrid_retrievr = HybridSearch(vector_retriever, keyword_retriever).get_retriever()
docs = hybrid_retrievr.get_relevant_documents(query)
reranker = CrossEncoderReranker()

--> TARGET: reranked_docs = reranker.rerank(docs, query, top_k=10)
'''


class CrossEncoderReranker:
    def __init__(self, model_name: str = None, device: str = None):
        # Load config từ config.yaml
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                pipeline_config = config.get('pipeline', {})
                default_model = pipeline_config.get('reranker_model', 'BAAI/bge-reranker-base')
        except Exception as e:
            print(f"[WARN] Không đọc được config.yaml, dùng default reranker: {e}")
            default_model = 'BAAI/bge-reranker-base'

        # Use param nếu có, nếu không dùng config
        if model_name is None:
            model_name = default_model
        self.model_name = model_name

        requested_device = device or os.getenv("RAG_DEVICE", "auto")
        if requested_device == "auto":
            requested_device = "cuda" if torch.cuda.is_available() else "cpu"
        if requested_device == "cuda" and not torch.cuda.is_available():
            requested_device = "cpu"
        self.device = requested_device
        print(f"Initializing CrossEncoderReranker on {self.device}...")
        print(f"Loading reranker model: {self.model_name}")

        # Jina v2 models cần trust_remote_code=True
        trust_remote = "jina-reranker-v2" in model_name

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            trust_remote_code=trust_remote
        )
        self.model.to(self.device)
        self.model.eval()
        self.BAD_HINTS = ("Cảm ơn các bạn đã xem", "đăng ký kênh", "subscribe", "like và share")

    @torch.no_grad()
    def batch_scores(self, query: str, texts: List[str], batch_size: int = 128, max_len: int = 512) -> List[float]:
        scores = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i: i + batch_size]
            inputs = self.tokenizer([query] * len(batch), batch, padding=True, truncation=True,
                                    max_length=max_len, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            logits = self.model(**inputs).logits.squeeze(-1)
            scores.extend(logits.tolist())
        return scores

    def rerank(self, docs, query: str, top_k: int = 10) -> List:
        texts = [d.page_content for d in docs]
        scores = self.batch_scores(query, texts)
        ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)

        final_docs = []
        for d, s in ranked:
            if all(h.lower() not in d.page_content.lower() for h in self.BAD_HINTS):
                final_docs.append(d)
            if len(final_docs) >= top_k:
                break
        return final_docs
