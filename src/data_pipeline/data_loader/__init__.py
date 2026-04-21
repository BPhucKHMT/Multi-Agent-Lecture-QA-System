"""Data ingestion loaders and pipeline."""

from importlib import import_module

__all__ = ["ConfigBasedCoordinator", "DataCoordinator", "Loader", "TranscriptPreprocessor"]


def __getattr__(name: str):
    module_map = {
        "ConfigBasedCoordinator": "src.data_pipeline.data_loader.coordinator",
        "DataCoordinator": "src.data_pipeline.data_loader.coordinator",
        "Loader": "src.data_pipeline.data_loader.file_loader",
        "TranscriptPreprocessor": "src.data_pipeline.data_loader.preprocess",
    }
    if name not in module_map:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_map[name])
    return getattr(module, name)
