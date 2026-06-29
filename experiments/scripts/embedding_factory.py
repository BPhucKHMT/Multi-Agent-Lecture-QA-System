from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv


DEFAULT_OPENAI_EMBEDDING_DIMENSIONS = 3072
DEFAULT_OPENAI_EMBEDDING_CHUNK_SIZE = 256


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str, batch_size: int = 16, normalize_embeddings: bool = True) -> None:
        from sentence_transformers import SentenceTransformer

        self.name = model_name
        self.batch_size = batch_size
        self.normalize_embeddings = normalize_embeddings
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=True,
        )
        return embeddings.tolist()


class OpenAIEmbedder:
    def __init__(
        self,
        model_name: str,
        dimensions: int = DEFAULT_OPENAI_EMBEDDING_DIMENSIONS,
        chunk_size: int = DEFAULT_OPENAI_EMBEDDING_CHUNK_SIZE,
    ) -> None:
        from langchain_openai import OpenAIEmbeddings

        load_dotenv()
        api_key = os.getenv("myAPIKey") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing OpenAI API key: set myAPIKey or OPENAI_API_KEY in .env")

        self.name = model_name
        self.model = OpenAIEmbeddings(
            model=model_name,
            api_key=api_key,
            dimensions=dimensions,
            chunk_size=chunk_size,
        )

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self.model.embed_documents(texts)


def create_embedder(model_config: dict[str, Any]) -> SentenceTransformerEmbedder | OpenAIEmbedder:
    embedder_type = model_config.get("type", "sentence_transformers")
    if embedder_type == "openai":
        return OpenAIEmbedder(
            model_name=model_config["name"],
            dimensions=int(model_config.get("dimensions", DEFAULT_OPENAI_EMBEDDING_DIMENSIONS)),
            chunk_size=int(model_config.get("chunk_size", DEFAULT_OPENAI_EMBEDDING_CHUNK_SIZE)),
        )

    return SentenceTransformerEmbedder(
        model_config["name"],
        batch_size=int(model_config.get("batch_size", 16)),
        normalize_embeddings=bool(model_config.get("normalize_embeddings", True)),
    )
