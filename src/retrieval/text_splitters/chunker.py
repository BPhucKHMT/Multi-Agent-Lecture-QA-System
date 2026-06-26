import os
import json
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain.schema import Document

# Import timestamp utility (copy từ experiments/src/time_utils.py)
def timestamp_to_seconds(timestamp: Any) -> int:
    """Convert timestamp string (HH:MM:SS or MM:SS) to seconds."""
    if timestamp in (None, ""):
        return 0
    if isinstance(timestamp, (int, float)):
        return int(timestamp)

    parts = [int(part) for part in str(timestamp).strip().split(":")]
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    return parts[0]


def seconds_to_timestamp(value: int) -> str:
    """Convert seconds to timestamp string (MM:SS or HH:MM:SS)."""
    hours, remainder = divmod(value, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


# ==========================================================
# Base Chunker
# ==========================================================
class BaseChunker:
    """Base class for all chunking strategies."""

    def chunk(self, documents: List[dict], output_dir: str) -> List[dict]:
        """Chunk documents and return list of chunk dicts."""
        raise NotImplementedError

    def _save_chunks(self, all_chunks: List[dict], output_dir: str, strategy_name: str):
        """Save chunks to JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "semantic_chunks.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([
                {"page_content": chunk.page_content, "metadata": chunk.metadata}
                for chunk in all_chunks
            ], f, ensure_ascii=False, indent=4)

        print(f"Saved {len(all_chunks)} chunks to {output_path} (strategy: {strategy_name})")


# ==========================================================
# Recursive Chunker (Baseline)
# ==========================================================
class RecursiveChunker(BaseChunker):
    """RecursiveCharacterTextSplitter - baseline chunking."""

    def __init__(self, chunk_size: int = 700, chunk_overlap: int = 100):
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def chunk(self, documents: List[dict], output_dir: str) -> List[dict]:
        all_chunks = []

        for item in documents:
            full_text = item["full_text"]
            position_map = item["position_map"]
            playlist = item["playlist"]
            filename = item["filename"]
            title = item["title"]
            url = item["url"]

            text_chunks = self.splitter.split_text(full_text)
            current_pos = 0

            for i, chunk_text in enumerate(text_chunks):
                start_index = full_text.find(chunk_text, current_pos)
                if start_index == -1:
                    start_index = current_pos

                end_index = start_index + len(chunk_text)
                current_pos = start_index + 1

                matched_ts = [
                    pos for pos in position_map
                    if not (pos["pos_end"] < start_index or pos["pos_start"] > end_index)
                ]

                metadata = {
                    "playlist": playlist,
                    "video_url": url,
                    "filename": filename,
                    "title": title,
                    "chunk_id": i,
                    "chunk_strategy": "recursive",
                    "start_timestamp": matched_ts[0]["start"] if matched_ts else None,
                    "end_timestamp": matched_ts[-1]["end"] if matched_ts else None
                }

                doc = Document(page_content=chunk_text, metadata=metadata)
                all_chunks.append(doc)

        self._save_chunks(all_chunks, output_dir, "recursive")
        return all_chunks


# ==========================================================
# Timestamp Chunker
# ==========================================================
class TimestampChunker(BaseChunker):
    """Timestamp-based sliding window chunking."""

    def __init__(self, window_seconds: int = 150, overlap_seconds: int = 50):
        self.window = window_seconds
        self.overlap = overlap_seconds

    def chunk(self, documents: List[dict], output_dir: str) -> List[dict]:
        all_chunks = []

        for item in documents:
            position_map = item["position_map"]
            playlist = item["playlist"]
            filename = item["filename"]
            title = item["title"]
            url = item["url"]

            if not position_map:
                continue

            # Convert timestamps to seconds and sort
            segments = []
            for seg in position_map:
                start_sec = timestamp_to_seconds(seg["start"])
                end_sec = timestamp_to_seconds(seg["end"])
                if end_sec > start_sec:  # Valid segment
                    segments.append({
                        "start_sec": start_sec,
                        "end_sec": end_sec,
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"]
                    })

            if not segments:
                continue

            # Sort by start time
            segments.sort(key=lambda s: s["start_sec"])

            # Get video time bounds
            video_start = min(seg["start_sec"] for seg in segments)
            video_end = max(seg["end_sec"] for seg in segments)

            # Sliding window
            stride = self.window - self.overlap
            window_chunks = []
            chunk_id = 0
            start = video_start

            while start < video_end:
                end = min(start + self.window, video_end)

                # Find segments that overlap with this window
                window_segments = [
                    seg for seg in segments
                    if seg["start_sec"] < end and seg["end_sec"] > start
                ]

                if window_segments:
                    # Concatenate text
                    chunk_text = " ".join(seg["text"] for seg in window_segments)

                    metadata = {
                        "playlist": playlist,
                        "video_url": url,
                        "filename": filename,
                        "title": title,
                        "chunk_id": chunk_id,
                        "chunk_strategy": f"timestamp_{self.window}_{self.overlap}",
                        "start_timestamp": window_segments[0]["start"],
                        "end_timestamp": window_segments[-1]["end"],
                        "start_seconds": window_segments[0]["start_sec"],
                        "end_seconds": window_segments[-1]["end_sec"],
                        "window_seconds": self.window,
                        "overlap_seconds": self.overlap
                    }

                    doc = Document(page_content=chunk_text, metadata=metadata)
                    window_chunks.append(doc)
                    chunk_id += 1

                start += stride

            all_chunks.extend(window_chunks)

        strategy_name = f"timestamp_{self.window}_{self.overlap}"
        self._save_chunks(all_chunks, output_dir, strategy_name)
        return all_chunks


# ==========================================================
# Semantic Chunker (LangChain SemanticChunker)
# ==========================================================
class SemanticChunker(BaseChunker):
    """
    Semantic chunking using LangChain's SemanticChunker with embeddings.
    Splits text based on semantic similarity (embedding cosine distance).
    """

    def __init__(self, embedding_provider: str = "openai"):
        """
        Args:
            embedding_provider: "openai" hoặc "bge"
        """
        from langchain_experimental.text_splitter import SemanticChunker

        self.embedding_provider = embedding_provider
        self.text_splitter = self._create_splitter()

    def _create_splitter(self):
        """Tạo SemanticChunker với embedding model phù hợp."""
        load_dotenv()

        if self.embedding_provider == "openai":
            try:
                from langchain_openai import OpenAIEmbeddings

                api_key = os.getenv("myAPIKey") or os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("Missing OpenAI API key (myAPIKey or OPENAI_API_KEY)")

                print(f"[SEMANTIC] Using OpenAI embeddings (text-embedding-3-large)")
                embeddings = OpenAIEmbeddings(
                    model="text-embedding-3-large",
                    api_key=api_key,
                    dimensions=3072,
                    chunk_size=256
                )
            except ImportError as e:
                raise ImportError(f"Missing langchain-openai: {e}. Install: pip install langchain-openai")
        else:
            # Default: dùng BGE-M3 fine-tuned từ experiments
            # Fallback nếu không có model
            model_path = Path("experiments/runs/finetune/embedding/20260616-120132")
            if not model_path.exists():
                print(f"[WARN] Fine-tuned BGE model not found at {model_path}, falling back to OpenAI")
                return self._create_splitter("openai")

            try:
                from langchain_huggingface import HuggingFaceEmbeddings

                print(f"[SEMANTIC] Using BGE-M3 fine-tuned embeddings")
                embeddings = HuggingFaceEmbeddings(
                    model_name=str(model_path),
                    model_kwargs={"device": "cpu"}
                )
            except ImportError as e:
                raise ImportError(f"Missing langchain-huggingface: {e}. Install: pip install langchain-huggingface")

        return SemanticChunker(
            embeddings=embeddings,
            buffer_size=1,
            add_start_index=True,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=95
        )

    def chunk(self, documents: List[dict], output_dir: str) -> List[dict]:
        all_chunks = []

        for item in documents:
            full_text = item["full_text"]
            position_map = item["position_map"]
            playlist = item["playlist"]
            filename = item["filename"]
            title = item["title"]
            url = item["url"]

            # Create Document for SemanticChunker
            doc = Document(
                page_content=full_text,
                metadata={
                    "playlist": playlist,
                    "video_url": url,
                    "filename": filename,
                    "title": title
                }
            )

            # Split with SemanticChunker
            try:
                split_docs = self.text_splitter.split_documents([doc])
            except Exception as e:
                print(f"[ERR] Semantic chunking failed for {filename}: {e}")
                print(f"       Falling back to recursive chunker for this video.")
                # Fallback: dùng recursive cho video này
                from langchain.text_splitter import RecursiveCharacterTextSplitter
                fallback_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=700,
                    chunk_overlap=100,
                    separators=["\n\n", "\n", ". ", " ", ""]
                )
                fallback_chunks = fallback_splitter.split_text(full_text)
                split_docs = [
                    Document(page_content=txt, metadata={"playlist": playlist, "video_url": url, "filename": filename, "title": title})
                    for txt in fallback_chunks
                ]

            # Process each chunk: map timestamps
            for i, chunk_doc in enumerate(split_docs):
                chunk_text = chunk_doc.page_content
                chunk_metadata = dict(chunk_doc.metadata)

                # SemanticChunker có start_index
                start_idx = chunk_metadata.pop("start_index", 0)
                end_idx = start_idx + len(chunk_text)

                # Find timestamps from position_map
                matched_ts = [
                    pos for pos in position_map
                    if not (pos["pos_end"] < start_idx or pos["pos_start"] > end_idx)
                ]

                # Update metadata
                chunk_metadata.update({
                    "chunk_id": i,
                    "chunk_strategy": "semantic",
                    "start_timestamp": matched_ts[0]["start"] if matched_ts else None,
                    "end_timestamp": matched_ts[-1]["end"] if matched_ts else None
                })

                all_chunks.append(chunk_doc)

        self._save_chunks(all_chunks, output_dir, "semantic")
        return all_chunks


# ==========================================================
# TranscriptChunker - Factory
# ==========================================================
class TranscriptChunker:
    """
    Factory class để chọn chunking strategy dựa trên config.

    CHUNK_STRATEGY env var options:
    - recursive (default)
    - timestamp_150_50
    - timestamp_90_30
    - semantic
    """

    def __init__(self, open_api_key: str = None):
        self.strategy = os.getenv("CHUNK_STRATEGY", "recursive")
        self.open_api_key = open_api_key

        if self.strategy == "recursive":
            self.chunker = RecursiveChunker()
        elif self.strategy.startswith("timestamp"):
            # Parse "timestamp_150_50" -> window=150, overlap=50
            parts = self.strategy.split("_")
            if len(parts) >= 3:
                window = int(parts[1])
                overlap = int(parts[2])
            else:
                # Default to 150/50 if just "timestamp"
                window, overlap = 150, 50
            self.chunker = TimestampChunker(window_seconds=window, overlap_seconds=overlap)
        elif self.strategy == "semantic":
            # Semantic chunker with embeddings
            provider = os.getenv("SEMANTIC_EMBEDDING_PROVIDER", "openai")
            print(f"[INFO] Using semantic chunking with {provider} embeddings")
            try:
                self.chunker = SemanticChunker(embedding_provider=provider)
            except Exception as e:
                print(f"[WARN] Failed to initialize SemanticChunker: {e}")
                print(f"       Falling back to recursive chunker")
                self.chunker = RecursiveChunker()
        else:
            print(f"[WARN] Unknown chunk strategy '{self.strategy}', falling back to recursive")
            self.chunker = RecursiveChunker()

    def __call__(self, documents: List[dict], output_dir: str) -> List[dict]:
        return self.chunker.chunk(documents, output_dir)
