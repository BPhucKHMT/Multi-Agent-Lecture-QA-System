from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class RerankerModel(Protocol):
    name: str

    def score_pairs(self, query: str, passages: list[str]) -> list[float]:
        ...


@dataclass
class ModelLoadResult:
    name: str
    status: str
    model: RerankerModel | None = None
    reason: str | None = None


class NoRerankModel:
    name = "no_rerank"

    def score_pairs(self, query: str, passages: list[str]) -> list[float]:
        return [0.0 for _ in passages]


class SentenceTransformersCrossEncoderReranker:
    def __init__(self, model_name: str, batch_size: int, max_length: int, device: str | None, trust_remote_code: bool = False) -> None:
        from sentence_transformers import CrossEncoder

        kwargs: dict[str, Any] = {"max_length": max_length, "trust_remote_code": trust_remote_code}
        if device:
            kwargs["device"] = device
        self.name = model_name
        self.batch_size = batch_size
        self.model = CrossEncoder(model_name, **kwargs)

    def score_pairs(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        scores = self.model.predict([(query, passage) for passage in passages], batch_size=self.batch_size, show_progress_bar=False)
        return [float(score) for score in scores]


class FlashRankReranker:
    def __init__(self, model_name: str) -> None:
        from flashrank import Ranker

        self.name = model_name
        self.ranker = Ranker(model_name=model_name.replace("flashrank/", ""))

    def score_pairs(self, query: str, passages: list[str]) -> list[float]:
        from flashrank import RerankRequest

        request = RerankRequest(query=query, passages=[{"id": str(index), "text": text} for index, text in enumerate(passages)])
        results = self.ranker.rerank(request)
        scores = [0.0 for _ in passages]
        for result in results:
            scores[int(result["id"])] = float(result["score"])
        return scores


def load_reranker(config: dict[str, Any], lane_config: dict[str, Any], device: str | None) -> ModelLoadResult:
    name = config["name"]
    model_type = config.get("type", "sentence_transformers_cross_encoder")
    if model_type == "baseline":
        return ModelLoadResult(name=name, status="completed", model=NoRerankModel())
    if model_type == "flashrank":
        try:
            return ModelLoadResult(name=name, status="completed", model=FlashRankReranker(name))
        except ModuleNotFoundError as error:
            return ModelLoadResult(name=name, status="skipped_dependency_missing", reason=str(error))
        except Exception as error:  # pragma: no cover - depends on local model/runtime
            return ModelLoadResult(name=name, status="skipped_model_load_failed", reason=f"{type(error).__name__}: {error}")
    if model_type == "flagembedding_layerwise":
        try:
            import FlagEmbedding  # noqa: F401
        except ModuleNotFoundError as error:
            return ModelLoadResult(name=name, status="skipped_dependency_missing", reason=str(error))
        return ModelLoadResult(name=name, status="skipped_unsupported_adapter", reason="Layerwise FlagEmbedding adapter chưa được bật để tránh sai API.")
    try:
        return ModelLoadResult(
            name=name,
            status="completed",
            model=SentenceTransformersCrossEncoderReranker(
                name,
                batch_size=int(config.get("batch_size", 4)),
                max_length=int(lane_config.get("max_length", 512)),
                device=device,
                trust_remote_code=bool(config.get("trust_remote_code", False)),
            ),
        )
    except ModuleNotFoundError as error:
        return ModelLoadResult(name=name, status="skipped_dependency_missing", reason=str(error))
    except Exception as error:  # pragma: no cover - depends on model/runtime
        return ModelLoadResult(name=name, status="skipped_model_load_failed", reason=f"{type(error).__name__}: {error}")
