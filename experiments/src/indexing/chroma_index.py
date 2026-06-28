import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from experiments.src.data.chunk_loader import load_chunks


class EmbedderProtocol:
    name: str

    def encode(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


def build_chroma_index(config: dict[str, Any], embedder: EmbedderProtocol) -> dict[str, Any]:
    chunks = load_chunks(config["chunks_dir"], strategy_id=config["strategy_id"])
    index_dir = Path(config["index_dir"])
    collection_name = config.get("collection_name", build_collection_name(config))
    index_dir.mkdir(parents=True, exist_ok=True)

    import chromadb

    client = chromadb.PersistentClient(path=str(index_dir))

    # Delete existing collection if present (clean rebuild)
    try:
        client.delete_collection(name=collection_name)
        print(f"[INFO] Deleted existing collection: {collection_name}")
    except Exception:
        pass  # Collection didn't exist, that's fine

    collection = client.create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
    vectors = embedder.encode([chunk["text"] for chunk in chunks])
    add_chunks(collection, chunks, vectors)

    manifest = {
        "strategy_id": config["strategy_id"],
        "dataset_version": config["dataset_version"],
        "retrieval_backend": config.get("retrieval_backend", "chroma"),
        "model": config["model"]["name"],
        "chunks_dir": config["chunks_dir"],
        "index_dir": str(index_dir),
        "collection_name": collection_name,
        "chunk_count": len(chunks),
    }
    (index_dir / "index_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def query_chroma_index(
    queries: List[Dict[str, Any]],
    index_dir: Union[str, Path],
    collection_name: str,
    embedder: EmbedderProtocol,
    top_k: int,
) -> Tuple[Dict[str, List[str]], List[Dict[str, Any]], Dict[str, Any]]:
    import chromadb

    client = chromadb.PersistentClient(path=str(index_dir))
    collection = client.get_collection(name=collection_name)
    query_vectors = embedder.encode([query["text"] for query in queries])
    
    # Query in batches to avoid SQLite variable limits ("too many SQL variables")
    batch_size = 50
    ids_list = []
    distances_list = []
    metadatas_list = []
    for start in range(0, len(query_vectors), batch_size):
        batch_vectors = query_vectors[start : start + batch_size]
        batch_result = collection.query(query_embeddings=batch_vectors, n_results=top_k)
        ids_list.extend(batch_result["ids"])
        distances_list.extend(batch_result["distances"])
        metadatas_list.extend(batch_result["metadatas"])
        
    result = {"ids": ids_list, "distances": distances_list, "metadatas": metadatas_list}

    rankings: dict[str, list[str]] = {}
    eval_results: list[dict[str, Any]] = []
    for index, query in enumerate(queries):
        rows = build_chroma_results(result["ids"][index], result["distances"][index], result["metadatas"][index])
        rankings[query["query_id"]] = [row["doc_id"] for row in rows]
        eval_results.append({"query_id": query["query_id"], "question": query["text"], "results": rows})

    return rankings, eval_results, {
        "retrieval_backend": "chroma",
        "index_path": str(index_dir),
        "collection_name": collection_name,
    }


def add_chunks(collection: Any, chunks: list[dict[str, Any]], vectors: list[list[float]]) -> None:
    batch_size = 500
    for start in range(0, len(chunks), batch_size):
        batch_chunks = chunks[start : start + batch_size]
        collection.add(
            ids=[f"{chunk['doc_id']}__row_{start + offset}" for offset, chunk in enumerate(batch_chunks)],
            embeddings=vectors[start : start + batch_size],
            documents=[chunk["text"] for chunk in batch_chunks],
            metadatas=[to_chroma_metadata(chunk) for chunk in batch_chunks],
        )


def build_chroma_results(ids: list[str], distances: list[float], metadatas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for rank, (_, distance, metadata) in enumerate(zip(ids, distances, metadatas, strict=True), start=1):
        results.append(
            {
                "rank": rank,
                "doc_id": metadata["doc_id"],
                "score": 1.0 - distance,
                "video_id": metadata.get("filename"),
                "video_url": metadata.get("video_url"),
                "start_timestamp": metadata.get("start_timestamp"),
                "end_timestamp": metadata.get("end_timestamp"),
            }
        )
    return results


def to_chroma_metadata(chunk: Dict[str, Any]) -> Dict[str, Union[str, int, float, bool]]:
    metadata = {"doc_id": chunk["doc_id"]}
    for key, value in chunk["metadata"].items():
        if isinstance(value, (str, int, float, bool)):
            metadata[key] = value
    return metadata


def build_collection_name(config: Dict[str, Any]) -> str:
    model = config["model"]["name"].lower().replace("/", "-").replace("_", "-")
    strategy = config["strategy_id"].lower().replace("_", "-")
    return f"idx-{strategy}-{model}"[:63].strip("-")
