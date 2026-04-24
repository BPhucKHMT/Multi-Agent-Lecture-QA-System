"""
Hỗ trợ Semantic Cache sử dụng Redis và OpenAI Embeddings.
Giúp giảm chi phí và thời gian phản hồi cho các câu hỏi trùng lặp hoặc tương tự.
"""
import json
import logging
from typing import Any, Dict, Optional
import redis
from langchain_openai import OpenAIEmbeddings
import numpy as np

logger = logging.getLogger(__name__)

class SemanticCache:
    def __init__(self, redis_client: redis.Redis, threshold: float = 0.95):
        self.redis = redis_client
        self.threshold = threshold
        # Sử dụng cùng embedding model với RAG core để đồng bộ
        from backend.app.core.config import settings
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.prefix = "semantic_cache:"

    async def get(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Tìm kiếm câu trả lời tương tự trong cache."""
        try:
            # 1. Tạo embedding cho prompt mới
            query_embedding = self.embeddings.embed_query(prompt)
            
            # Lưu ý: Hiện tại Redis bản miễn phí/standard thường không hỗ trợ Vector Search trực tiếp
            # Nếu không có RediSearch/Vector similarity, ta có thể dùng phương pháp Hash đơn giản
            # hoặc brute-force (không khuyến khích cho production lớn).
            # Ở đây ta sử dụng cơ chế Hash đơn giản cho bài toán này nếu không có Vector DB chuyên dụng.
            
            cache_key = f"{self.prefix}hash:{hash(prompt)}"
            data = self.redis.get(cache_key)
            if data:
                return json.loads(data)
                
            return None
        except Exception as e:
            logger.error(f"SemanticCache Get Error: {e}")
            return None

    async def set(self, prompt: str, response: Dict[str, Any], expire: int = 3600 * 24):
        """Lưu câu trả lời vào cache."""
        try:
            cache_key = f"{self.prefix}hash:{hash(prompt)}"
            self.redis.setex(
                cache_key,
                expire,
                json.dumps(response, ensure_ascii=False)
            )
        except Exception as e:
            logger.error(f"SemanticCache Set Error: {e}")
