import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from langchain.schema import Document
from src.retrieval.reranking import CrossEncoderReranker

query = "naive bayes là gì và dùng trong phân loại như thế nào?"
base_texts = [
    "Naive Bayes là thuật toán phân loại xác suất dựa trên định lý Bayes và giả định độc lập có điều kiện giữa các đặc trưng.",
    "Hồi quy tuyến tính dự đoán giá trị liên tục bằng cách tối ưu sai số bình phương giữa nhãn thật và nhãn dự đoán.",
    "Trong học máy, overfitting xảy ra khi mô hình học quá sát dữ liệu huấn luyện và tổng quát kém trên dữ liệu mới.",
    "Precision, recall và F1-score là các thước đo đánh giá mô hình phân loại, đặc biệt khi dữ liệu mất cân bằng.",
    "K-means là thuật toán phân cụm chia dữ liệu thành k cụm bằng cách cập nhật tâm cụm lặp đi lặp lại.",
]

docs = [Document(page_content=base_texts[index % len(base_texts)]) for index in range(80)]

start = time.perf_counter()
reranker = CrossEncoderReranker()
load_time = time.perf_counter() - start

reranker.rerank(docs[:8], query, top_k=5)

times = []
for _ in range(3):
    start_run = time.perf_counter()
    reranker.rerank(docs, query, top_k=10)
    times.append(time.perf_counter() - start_run)

print("device=", reranker.device)
print("model= BAAI/bge-reranker-base")
print("docs=", len(docs))
print("load_sec=", round(load_time, 3))
print("avg_rerank_sec=", round(statistics.mean(times), 4))
print("max_rerank_sec=", round(max(times), 4))
print("samples=", [round(value, 4) for value in times])
