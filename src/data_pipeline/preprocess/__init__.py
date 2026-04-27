"""Preprocess utilities."""

from importlib import import_module

__all__ = ["correct_spelling"]


def __getattr__(name: str):
    if name != "correct_spelling":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module("src.data_pipeline.preprocess.preprocess")
    return getattr(module, name)
