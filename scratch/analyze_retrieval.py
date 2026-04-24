import os
import sys

# Add src to path
sys.path.append(os.getcwd())

from src.rag_core import resource_manager
from src.rag_core.offline_rag import Offline_RAG
from src.generation.llm_model import get_llm

def analyze_query(query):
    print(f"\n{'='*50}")
    print(f"ANALYZING QUERY: {query}")
    print(f"{'='*50}")
    
    # 1. Get resources
    hybrid_retriever = resource_manager.get_hybrid_retriever()
    reranker = resource_manager.get_tutor_chain() # Wait, get_tutor_chain returns the chain, not reranker
    
    # Let's use the resources directly
    vector_retriever = resource_manager.get_vector_retriever()
    bm25_retriever = resource_manager.get_bm25_retriever()
    reranker = resource_manager.get_tutor_reranker()
    
    # 2. Vector Search
    print("\n--- VECTOR SEARCH TOP 5 ---")
    vector_docs = vector_retriever.invoke(query)
    for i, doc in enumerate(vector_docs[:5]):
        print(f"[{i}] {doc.metadata.get('title')} ({doc.metadata.get('start_timestamp')})")
        print(f"Content: {doc.page_content[:200]}...")
        
    # 3. BM25 Search
    print("\n--- BM25 SEARCH TOP 5 ---")
    bm25_docs = bm25_retriever.invoke(query)
    for i, doc in enumerate(bm25_docs[:5]):
        print(f"[{i}] {doc.metadata.get('title')} ({doc.metadata.get('start_timestamp')})")
        print(f"Content: {doc.page_content[:200]}...")
        
    # 4. Hybrid Search
    print("\n--- HYBRID SEARCH TOP 10 ---")
    hybrid_docs = hybrid_retriever.invoke(query)
    for i, doc in enumerate(hybrid_docs[:10]):
        print(f"[{i}] {doc.metadata.get('title')} ({doc.metadata.get('start_timestamp')})")
        
    # 5. Reranked
    print("\n--- RERANKED TOP 5 ---")
    reranked = reranker.rerank(hybrid_docs, query, top_k=5)
    for i, doc in enumerate(reranked):
        print(f"[{i}] {doc.metadata.get('title')} ({doc.metadata.get('start_timestamp')})")
        print(f"Content: {doc.page_content[:200]}...")

if __name__ == "__main__":
    queries = [
        "diffusion có 3 thành phần gì trong loss nó",
        "3 thành phần trong diffusion",
        "reconstruction, divergence, conditioning là gì",
        "thành phần hàm loss diffusion"
    ]
    
    for q in queries:
        analyze_query(q)
