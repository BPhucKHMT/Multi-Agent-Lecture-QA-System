import sys
import os
from pathlib import Path

# Thêm src vào path để import
sys.path.append(os.getcwd())

from src.storage.vectorstore import VectorDB
from src.retrieval.keyword_search import BM25KeywordSearch
from src.retrieval.reranking import CrossEncoderReranker

def smoke_test():
    query = "Hàm loss của diffusion là gì"
    print(f"🚀 Đang thực hiện Smoke Test với query: '{query}'\n")
    
    # 1. Khởi tạo DB và lấy toàn bộ docs
    vdb = VectorDB()
    all_docs = vdb.get_documents()
    print(f"📦 Tổng số documents trong DB: {len(all_docs)}")
    
    # 2. Khởi tạo BM25 (Với logic OCR mới)
    print("🔍 Đang chạy tìm kiếm BM25 (Keywords + OCR)...")
    bm25_retriever = BM25KeywordSearch(all_docs, k=10).get_retriever()
    bm25_results = bm25_retriever.get_relevant_documents(query)
    
    # 3. Kiểm tra kết quả BM25
    found_ocr_match = False
    print("\n--- Kết quả BM25 (Top 5) ---")
    for i, doc in enumerate(bm25_results[:5]):
        has_ocr = "Yes" if doc.metadata.get("ocr_content") else "No"
        print(f"[{i}] Title: {doc.metadata.get('title')}")
        print(f"    Has OCR: {has_ocr}")
        
        # Kiểm tra xem từ khóa có nằm trong OCR không
        ocr_text = doc.metadata.get("ocr_content", "").lower()
        if "loss" in ocr_text or "diffusion" in ocr_text:
            found_ocr_match = True
            print(f"    ✨ MATCH TRONG OCR: ...{ocr_text[:100]}...")
        
        print(f"    Snippet: {doc.page_content[:150]}...\n")

    if found_ocr_match:
        print("✅ THÀNH CÔNG: BM25 đã tìm thấy tài liệu dựa trên nội dung OCR!")
    else:
        print("⚠️ CẢNH BÁO: Không tìm thấy từ khóa trong phần OCR của top kết quả (có thể do dữ liệu chưa có hoặc query chưa khớp).")

if __name__ == "__main__":
    # Đảm bảo môi trường UTF-8
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    smoke_test()
