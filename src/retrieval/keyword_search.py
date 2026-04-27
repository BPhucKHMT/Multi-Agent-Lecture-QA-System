from langchain.schema import Document
from typing import List
from langchain_community.retrievers import BM25Retriever

'''
thực thi bm25:
 vector_db  = VectorDB()
 documents = vector_db.get_documents()
 BM25_search = BM25KeywordSearch(documents)
'''


import copy

class BM25KeywordSearch:
    def __init__(self, documents: List[Document], k: int = 40):
        # Tạo bản sao sâu để không làm bẩn dữ liệu cho các retriever khác (như Vector)
        # Chúng ta chỉ muốn BM25 có thêm thông tin từ OCR
        enriched_docs = []
        for doc in documents:
            new_doc = copy.copy(doc) # Shallow copy is enough to change page_content without touching meta
            ocr_text = doc.metadata.get("ocr_content")
            if ocr_text:
                # Gộp nội dung OCR vào text để BM25 có thể tìm kiếm từ khoa học trên slide
                new_doc.page_content = f"{doc.page_content}\n[OCR Context]: {ocr_text}"
            enriched_docs.append(new_doc)

        self.retriever = BM25Retriever.from_documents(enriched_docs, k=k)

    def get_retriever(self):
        return self.retriever
