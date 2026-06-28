import json
from pathlib import Path

from experiments.src.indexing.chroma_index import build_chroma_index, build_collection_name


class FakeEmbedder:
    name = "fake-model"

    def encode(self, texts):
        return [[1.0, 0.0] if "alpha" in text else [0.0, 1.0] for text in texts]


def test_build_chroma_index_writes_manifest(tmp_path: Path, monkeypatch):
    chunks_dir = tmp_path / "chunks" / "recursive" / "cs101"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "recursive_chunks.json").write_text(
        json.dumps(
            [
                {"page_content": "alpha lesson", "metadata": {"filename": "v1", "start_timestamp": "0:00:00", "end_timestamp": "0:00:30"}},
                {"page_content": "beta lesson", "metadata": {"filename": "v2", "start_timestamp": "0:00:00", "end_timestamp": "0:00:30"}},
            ]
        ),
        encoding="utf-8",
    )
    index_dir = tmp_path / "indexes" / "chroma" / "recursive" / "fake-model"
    added = []

    class FakeCollection:
        def add(self, ids, embeddings, documents, metadatas):
            added.append({"ids": ids, "embeddings": embeddings, "documents": documents, "metadatas": metadatas})

    class FakeClient:
        def __init__(self, path):
            assert path == str(index_dir)

        def delete_collection(self, name):
            pass

        def create_collection(self, name, metadata):
            assert name == "idx-recursive-fake-model"
            assert metadata == {"hnsw:space": "cosine"}
            return FakeCollection()

    monkeypatch.setitem(__import__("sys").modules, "chromadb", type("FakeChroma", (), {"PersistentClient": FakeClient}))

    manifest = build_chroma_index(
        {
            "dataset_version": "unit",
            "strategy_id": "recursive",
            "chunks_dir": str(tmp_path / "chunks" / "recursive"),
            "index_dir": str(index_dir),
            "collection_name": "idx-recursive-fake-model",
            "retrieval_backend": "chroma",
            "model": {"name": "fake-model"},
        },
        FakeEmbedder(),
    )

    assert manifest["chunk_count"] == 2
    assert manifest["index_dir"] == str(index_dir)
    assert added[0]["ids"] == ["v1_0_30__row_0", "v2_0_30__row_1"]
    assert added[0]["metadatas"][0]["doc_id"] == "v1_0_30"
    saved_manifest = json.loads((index_dir / "index_manifest.json").read_text(encoding="utf-8"))
    assert saved_manifest == manifest


def test_build_collection_name_is_stable():
    assert build_collection_name({"strategy_id": "timestamp_90_30", "model": {"name": "BAAI/bge-m3"}}) == "idx-timestamp-90-30-baai-bge-m3"
