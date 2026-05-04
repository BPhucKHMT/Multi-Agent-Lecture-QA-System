import os
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from src.storage.vectorstore import VectorDB

queries = [
    "naive bayes là gì?",
    "giải thích hồi quy logistic trong machine learning",
    "overfitting và underfitting khác nhau như thế nào?",
    "thuật toán k means hoạt động ra sao?",
    "precision recall f1 score là gì?",
]

start = time.perf_counter()
vdb = VectorDB(documents=None)
load_time = time.perf_counter() - start

vdb.embedding.embed_query(queries[0])

times = []
for query in queries:
    start_query = time.perf_counter()
    vdb.embedding.embed_query(query)
    times.append(time.perf_counter() - start_query)

client = getattr(vdb.embedding, "client", None)
device = getattr(client, "_target_device", "unknown")

print("device=", device)
print("model=", os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3"))
print("load_sec=", round(load_time, 3))
print("avg_query_sec=", round(statistics.mean(times), 4))
print("max_query_sec=", round(max(times), 4))
print("samples=", [round(value, 4) for value in times])
