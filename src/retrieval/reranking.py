"""Reranker cross-encoder đa backend: OpenVINO INT8 / ONNX Runtime INT8 (CPU) và TensorRT/ONNX CUDA (GPU).

Suy luận reranker là bước tốn CPU nhất trong RAG (benchmark 2026-09-28:
PyTorch CPU ~52s/query, OpenVINO INT8 ~1.9s/query, ONNX INT8 ~0.66s p50).
Module này thay thế loader PyTorch đơn thuần bằng factory `load_reranker`
chọn backend theo biến môi trường và tự fallback khi backend lỗi:

- CPU: OpenVINO INT8 -> ONNX Runtime CPU INT8 -> PyTorch CPU.
- GPU NVIDIA: TensorRT/ONNX CUDA -> PyTorch CUDA FP16/BF16.
- Bypass: `reranker_model: none` giữ nguyên hành vi lọc BAD_HINTS cũ.

Hợp đồng dùng chung: `score_pairs(query, texts) -> list[float]` và
`rerank(docs, query, top_k)`; metadata không đổi cho caller.
"""

from __future__ import annotations

import logging
import math
import os
import threading
from pathlib import Path
from typing import Callable, List

import numpy as np
import torch
import yaml

logger = logging.getLogger(__name__)

MODEL_REVISION = "9cfeff2df7d40d1b78e75e5e9cebec92a99813c9"
MODEL_REPO_ID = "jinaai/jina-reranker-v2-base-multilingual"
DEFAULT_MODEL_DIR = Path(
    "artifacts/models/jina-reranker-v2-base-multilingual-9cfeff2"
)
DEFAULT_BATCH_SIZE = 8
BAD_HINTS = ("Cảm ơn các bạn đã xem", "đăng ký kênh", "subscribe", "like và share")
LOWER_BAD_HINTS = tuple(hint.lower() for hint in BAD_HINTS)
ScoreBatch = Callable[[str, List[str]], List[float]]

CPU_BACKEND_ORDER = ("openvino", "onnx", "torch")
GPU_BACKEND_ORDER = ("tensorrt", "onnx", "torch")


def _read_reranker_model_name() -> str | None:
    try:
        with open("config.yaml", "r", encoding="utf-8") as file:
            config = yaml.safe_load(file) or {}
        pipeline_config = config.get("pipeline", {}) or {}
        model_name = pipeline_config.get("reranker_model")
        return str(model_name) if model_name else None
    except Exception as error:  # noqa: BLE001 - config tuỳ chọn
        logger.warning("Không đọc được config.yaml, dùng default reranker: %s", error)
        return None


def _model_dir() -> Path:
    return Path(os.getenv("RAG_RERANKER_MODEL_DIR", DEFAULT_MODEL_DIR))


def _resolve_model_name(model_name: str | None) -> str:
    resolved = model_name or _read_reranker_model_name() or MODEL_REPO_ID
    if resolved.lower() in {"none", "null"}:
        return "none"
    return resolved


def _artifact_paths(model_dir: Path | None = None) -> tuple[Path, Path] | None:
    base = model_dir or _model_dir()
    onnx_path = base / "onnx" / "model_int8.onnx"
    if onnx_path.is_file() and (base / "tokenizer.json").is_file():
        return base, onnx_path
    return None


def _onnx_artifact(model_dir: Path) -> Path:
    artifacts = _artifact_paths(model_dir)
    if artifacts is None:
        raise FileNotFoundError(f"Thiếu ONNX INT8/tokenizer tại {model_dir}")
    return artifacts[1]


def _resolve_device(device: str | None = None) -> str:
    requested = (device or os.getenv("RAG_DEVICE", "auto")).strip().lower()
    if requested in {"", "auto"}:
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested not in {"cpu", "cuda"}:
        raise ValueError(f"RAG_DEVICE không hợp lệ: {requested}")
    if requested == "cuda" and not torch.cuda.is_available():
        logger.warning("CUDA không khả dụng; dùng CPU cho reranker.")
        return "cpu"
    return requested


def resolve_backend(device: str | None = None) -> str:
    """Chọn backend từ cấu hình, sau đó theo thiết bị runtime."""
    explicit = os.getenv("RAG_BACKEND", "auto").strip().lower()
    if explicit not in {"", "auto"}:
        return explicit
    return "tensorrt" if _resolve_device(device) == "cuda" else "openvino"


def _pretrained_kwargs(model_source: str | Path) -> dict[str, str | bool]:
    source = str(model_source).replace("\\", "/")
    if "jina-reranker-v2-base-multilingual" not in source:
        return {}
    kwargs: dict[str, str | bool] = {"fix_mistral_regex": True}
    if not isinstance(model_source, Path):
        kwargs["revision"] = MODEL_REVISION
    return kwargs


def _load_tokenizer(model_source: str | Path):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(
        model_source,
        **_pretrained_kwargs(model_source),
    )


def _sigmoid(logits: np.ndarray) -> np.ndarray:
    logits = np.clip(np.asarray(logits, dtype=np.float32), -80.0, 80.0)
    return 1.0 / (1.0 + np.exp(-logits))


def _tokenize_batch(tokenizer, query: str, batch: List[str], max_length: int):
    encoded = tokenizer(
        [query] * len(batch),
        batch,
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="np",
    )
    return {key: np.asarray(value, dtype=np.int64) for key, value in encoded.items()}


def _build_openvino(
    model_dir: Path,
    max_length: int,
    _device: str | None = None,
) -> "CrossEncoderReranker":
    import openvino as ov

    onnx_path = _onnx_artifact(model_dir)
    compiled = ov.Core().compile_model(
        str(onnx_path),
        "CPU",
        {"PERFORMANCE_HINT": "LATENCY"},
    )
    tokenizer = _load_tokenizer(model_dir)
    inference_lock = threading.Lock()

    def score_batch(query: str, batch: List[str]) -> List[float]:
        feed = _tokenize_batch(tokenizer, query, batch, max_length)
        with inference_lock:
            results = compiled(feed)
            logits = next(iter(results.values())).reshape(-1)
        return _sigmoid(logits).tolist()

    return CrossEncoderReranker(
        backend="openvino",
        model_dir=model_dir,
        score_batch=score_batch,
        batch_size=DEFAULT_BATCH_SIZE,
    )


def _build_onnx(
    model_dir: Path,
    max_length: int,
    device: str | None = None,
) -> "CrossEncoderReranker":
    import onnxruntime as ort

    onnx_path = _onnx_artifact(model_dir)
    runtime_device = _resolve_device(device)
    provider = (
        "CUDAExecutionProvider"
        if runtime_device == "cuda"
        else "CPUExecutionProvider"
    )
    if provider not in ort.get_available_providers():
        raise RuntimeError(f"ONNX Runtime thiếu provider {provider}")
    options = ort.SessionOptions()
    options.intra_op_num_threads = 0
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(
        str(onnx_path),
        sess_options=options,
        providers=[provider],
    )
    input_names = {item.name for item in session.get_inputs()}
    tokenizer = _load_tokenizer(model_dir)

    def score_batch(query: str, batch: List[str]) -> List[float]:
        encoded = _tokenize_batch(tokenizer, query, batch, max_length)
        feed = {
            key: value for key, value in encoded.items() if key in input_names
        }
        if "token_type_ids" in input_names and "token_type_ids" not in feed:
            feed["token_type_ids"] = np.zeros_like(feed["input_ids"])
        logits = np.asarray(session.run(None, feed)[0], dtype=np.float32).reshape(-1)
        return _sigmoid(logits).tolist()

    return CrossEncoderReranker(
        backend="onnx_cuda" if runtime_device == "cuda" else "onnx",
        model_dir=model_dir,
        score_batch=score_batch,
        batch_size=DEFAULT_BATCH_SIZE,
    )


def _build_torch(
    model_source: str | Path,
    max_length: int,
    device: str | None = None,
) -> "CrossEncoderReranker":
    import torch
    from transformers import AutoModelForSequenceClassification

    runtime_device = _resolve_device(device)
    if runtime_device == "cuda":
        supports_bf16 = getattr(torch.cuda, "is_bf16_supported", lambda: False)()
        dtype = torch.bfloat16 if supports_bf16 else torch.float16
        backend = "torch_bf16" if supports_bf16 else "torch_fp16"
    else:
        dtype = torch.float32
        backend = "torch_cpu"
    model = AutoModelForSequenceClassification.from_pretrained(
        model_source,
        dtype=dtype,
        trust_remote_code=(
            "jina-reranker-v2-base-multilingual" in str(model_source)
        ),
        **_pretrained_kwargs(model_source),
    )
    model.to(runtime_device)
    model.eval()
    tokenizer = _load_tokenizer(model_source)

    def score_batch(query: str, batch: List[str]) -> List[float]:
        encoded = tokenizer(
            [query] * len(batch),
            batch,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(runtime_device) for key, value in encoded.items()}
        with torch.no_grad():
            logits = model(**encoded).logits
        logits = logits.float().squeeze(-1).cpu().numpy()
        return _sigmoid(logits).tolist()

    return CrossEncoderReranker(
        backend=backend,
        model_dir=model_source,
        score_batch=score_batch,
        batch_size=DEFAULT_BATCH_SIZE,
    )


def _build_tensorrt(
    model_dir: Path,
    max_length: int,
    _device: str | None = None,
) -> "CrossEncoderReranker":
    """ONNX Runtime với TensorRT EP; CUDA EP xử lý subgraph chưa hỗ trợ."""
    import onnxruntime as ort

    available_providers = set(ort.get_available_providers())
    required_providers = {"TensorrtExecutionProvider", "CUDAExecutionProvider"}
    missing = required_providers - available_providers
    if missing:
        raise RuntimeError(
            f"ONNX Runtime thiếu provider GPU: {', '.join(sorted(missing))}"
        )
    onnx_path = _onnx_artifact(model_dir)
    cache_path = Path(os.getenv("RAG_TRT_CACHE_DIR", "artifacts/trt-cache"))
    cache_path.mkdir(parents=True, exist_ok=True)
    options = ort.SessionOptions()
    providers = [
        (
            "TensorrtExecutionProvider",
            {
                "trt_fp16_enable": True,
                "trt_engine_cache_enable": True,
                "trt_engine_cache_path": str(cache_path),
            },
        ),
        ("CUDAExecutionProvider", {}),
    ]
    session = ort.InferenceSession(
        str(onnx_path),
        sess_options=options,
        providers=providers,
    )
    input_names = {item.name for item in session.get_inputs()}
    tokenizer = _load_tokenizer(model_dir)

    def score_batch(query: str, batch: List[str]) -> List[float]:
        encoded = _tokenize_batch(tokenizer, query, batch, max_length)
        feed = {
            key: value for key, value in encoded.items() if key in input_names
        }
        if "token_type_ids" in input_names and "token_type_ids" not in feed:
            feed["token_type_ids"] = np.zeros_like(feed["input_ids"])
        logits = np.asarray(session.run(None, feed)[0], dtype=np.float32).reshape(-1)
        return _sigmoid(logits).tolist()

    return CrossEncoderReranker(
        backend="tensorrt",
        model_dir=model_dir,
        score_batch=score_batch,
        batch_size=DEFAULT_BATCH_SIZE,
    )

class CrossEncoderReranker:
    """Adapter reranker dùng chung hợp đồng `score_pairs` cho mọi backend."""

    def __init__(
        self,
        backend: str,
        model_dir: str | Path,
        score_batch: ScoreBatch,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        if batch_size < 1:
            raise ValueError("batch_size phải lớn hơn 0")
        self.backend = backend
        self.model_dir = model_dir
        self.model_name = str(model_dir)
        self._score_batch = score_batch
        self.batch_size = batch_size

    def score_pairs(self, query: str, texts: List[str]) -> List[float]:
        if not texts:
            return []
        scores: list[float] = []
        for offset in range(0, len(texts), self.batch_size):
            batch = texts[offset : offset + self.batch_size]
            batch_scores = self._score_batch(query, batch)
            if len(batch_scores) != len(batch):
                raise ValueError(
                    f"Reranker backend {self.backend} trả {len(batch_scores)} "
                    f"scores cho {len(batch)} documents"
                )
            for score in batch_scores:
                value = float(score)
                if not math.isfinite(value):
                    raise ValueError(
                        f"Reranker backend {self.backend} trả score không hữu hạn"
                    )
                scores.append(value)
        return scores

    def rerank(self, docs, query: str, top_k: int = 10) -> List:
        if top_k <= 0:
            return []
        texts = [doc.page_content for doc in docs]
        scores = self.score_pairs(query, texts)
        ranked = sorted(zip(docs, scores), key=lambda item: item[1], reverse=True)
        final_docs = []
        for doc, _score in ranked:
            lowered = doc.page_content.lower()
            if all(hint not in lowered for hint in LOWER_BAD_HINTS):
                final_docs.append(doc)
            if len(final_docs) >= top_k:
                break
        return final_docs


class BypassReranker:
    """Chế độ tắt reranker: chỉ lọc BAD_HINTS theo thứ tự retrieval ban đầu."""

    backend = "none"

    def score_pairs(self, _query: str, texts: List[str]) -> List[float]:
        return [0.0 for _ in texts]

    def rerank(self, docs, _query: str, top_k: int = 10) -> List:
        if top_k <= 0:
            return []
        final_docs = []
        for doc in docs:
            lowered = doc.page_content.lower()
            if all(hint not in lowered for hint in LOWER_BAD_HINTS):
                final_docs.append(doc)
            if len(final_docs) >= top_k:
                break
        return final_docs


def load_reranker(
    model_name: str | None = None,
    device: str | None = None,
    backend: str | None = None,
    max_length: int = 256,
    allow_fallback: bool = True,
):
    """Tạo reranker theo backend đã chọn và fallback trong cùng nhóm thiết bị."""
    resolved_model = _resolve_model_name(model_name)
    selected = (backend or resolve_backend(device)).strip().lower()
    if resolved_model == "none" or selected == "none":
        return BypassReranker()
    if selected not in {*CPU_BACKEND_ORDER, *GPU_BACKEND_ORDER}:
        raise ValueError(f"RAG_BACKEND không hợp lệ: {selected}")
    if max_length < 1:
        raise ValueError("max_length phải lớn hơn 0")

    runtime_device = _resolve_device(device)
    configured_dir: Path | None = None
    if model_name:
        explicit_path = Path(model_name)
        if explicit_path.is_dir():
            configured_dir = explicit_path
    else:
        configured_dir = _model_dir()
    artifacts = (
        _artifact_paths(configured_dir)
        if configured_dir is not None
        else None
    )
    local_model_dir = artifacts[0] if artifacts is not None else None
    torch_source: str | Path = local_model_dir or resolved_model

    if allow_fallback:
        family = (
            GPU_BACKEND_ORDER
            if selected == "tensorrt"
            or (selected == "onnx" and runtime_device == "cuda")
            else CPU_BACKEND_ORDER
        )
        order = family[family.index(selected) :]
    else:
        order = (selected,)

    builders = {
        "openvino": _build_openvino,
        "onnx": _build_onnx,
        "tensorrt": _build_tensorrt,
        "torch": _build_torch,
    }
    errors: list[str] = []
    for candidate in order:
        model_source: str | Path
        if candidate == "torch":
            model_source = torch_source
        elif local_model_dir is None:
            artifact_source = configured_dir or resolved_model
            errors.append(f"{candidate}: thiếu artifacts tại {artifact_source}")
            continue
        else:
            model_source = local_model_dir
        try:
            built = builders[candidate](
                model_source,
                max_length,
                runtime_device,
            )
            logger.info("Reranker backend=%s đã sẵn sàng.", built.backend)
            return built
        except Exception as error:  # noqa: BLE001 - fallback có chủ đích
            errors.append(f"{candidate}: {error}")
            logger.warning(
                "Backend %s lỗi, thử backend kế tiếp: %s",
                candidate,
                error,
            )

    raise RuntimeError(f"Không build được backend nào cho reranker: {errors}")
