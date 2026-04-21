"""Text splitters for ingestion."""

from importlib import import_module

__all__ = ["TranscriptChunker"]


def __getattr__(name: str):
    if name != "TranscriptChunker":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module("src.retrieval.text_splitters.semantic")
    return getattr(module, name)
