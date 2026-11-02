"""Kiểm thử lựa chọn backend và hợp đồng scoring cho reranker."""
import concurrent.futures
import importlib.util
import os
import sys
import threading
import time
from types import SimpleNamespace
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

_MODULE_PATH = Path(os.fspath(PROJECT_ROOT)) / "src" / "retrieval" / "reranking.py"
_SPEC = importlib.util.spec_from_file_location("reranking_under_test", _MODULE_PATH)


def _load_reranking():
    module = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(module)
    return module


class _FakeBackend:
    def __init__(self, backend: str, scores=None):
        self.backend = backend
        self._scores = scores or [0.9, 0.1]

    def score_pairs(self, _query, texts):
        return self._scores[: len(texts)]

def test_score_pairs_forwards_query_to_every_batch():
    reranking = _load_reranking()
    calls = []

    def score_batch(query, texts):
        calls.append((query, list(texts)))
        return [float(index) for index, _text in enumerate(texts)]

    reranker = reranking.CrossEncoderReranker(
        backend="fake",
        model_dir=Path("."),
        score_batch=score_batch,
        batch_size=2,
    )

    scores = reranker.score_pairs("query thật", ["a", "b", "c"])

    assert calls == [
        ("query thật", ["a", "b"]),
        ("query thật", ["c"]),
    ]
    assert scores == [0.0, 1.0, 0.0]


@pytest.mark.parametrize(
    "scores",
    ([0.1], [0.1, float("nan")]),
)
def test_score_pairs_rejects_invalid_backend_output(scores):
    reranking = _load_reranking()
    reranker = reranking.CrossEncoderReranker(
        backend="fake",
        model_dir=Path("."),
        score_batch=lambda _query, _texts: scores,
        batch_size=2,
    )

    with pytest.raises(ValueError, match="backend"):
        reranker.score_pairs("query", ["a", "b"])


def test_reranker_rejects_non_positive_batch_size():
    reranking = _load_reranking()

    with pytest.raises(ValueError, match="batch_size"):
        reranking.CrossEncoderReranker(
            backend="fake",
            model_dir=Path("."),
            score_batch=lambda _query, _texts: [],
            batch_size=0,
        )


def test_rerank_returns_no_documents_for_non_positive_top_k():
    reranking = _load_reranking()
    reranker = reranking.CrossEncoderReranker(
        backend="fake",
        model_dir=Path("."),
        score_batch=lambda _query, texts: [1.0 for _ in texts],
    )
    docs = [type("Doc", (), {"page_content": "content"})()]

    assert reranker.rerank(docs, "query", top_k=0) == []
    assert reranking.BypassReranker().rerank(docs, "query", top_k=-1) == []


def test_openvino_backend_serializes_compiled_model_calls(monkeypatch):
    reranking = _load_reranking()
    state_lock = threading.Lock()
    start = threading.Event()
    state = {"active": 0, "overlap": False}

    class CompiledModel:
        def __call__(self, _feed):
            with state_lock:
                state["active"] += 1
                state["overlap"] = state["overlap"] or state["active"] > 1
            time.sleep(0.05)
            with state_lock:
                state["active"] -= 1
            return {"output": reranking.np.asarray([[0.5]], dtype="float32")}

    compiled = CompiledModel()

    class Core:
        def compile_model(self, *_args, **_kwargs):
            return compiled

    def tokenizer(*_args, **_kwargs):
        return {
            "input_ids": [[1]],
            "attention_mask": [[1]],
        }

    monkeypatch.setitem(
        sys.modules,
        "openvino",
        SimpleNamespace(Core=Core),
    )
    monkeypatch.setattr(
        reranking,
        "_onnx_artifact",
        lambda _model_dir: Path("model_int8.onnx"),
    )
    monkeypatch.setattr(reranking, "_load_tokenizer", lambda _model_dir: tokenizer)
    model = reranking._build_openvino(Path("."), max_length=256)

    def score():
        start.wait(timeout=1)
        return model.score_pairs("query", ["document"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(score) for _ in range(2)]
        start.set()
        assert [future.result(timeout=1) for future in futures]

    assert state["overlap"] is False


def test_remote_tokenizer_uses_pinned_model_revision(monkeypatch):
    reranking = _load_reranking()
    calls = []

    class AutoTokenizer:
        @staticmethod
        def from_pretrained(model_source, **kwargs):
            calls.append((model_source, kwargs))
            return object()

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(AutoTokenizer=AutoTokenizer),
    )

    reranking._load_tokenizer(reranking.MODEL_REPO_ID)

    assert calls == [
        (
            reranking.MODEL_REPO_ID,
            {
                "revision": reranking.MODEL_REVISION,
                "fix_mistral_regex": True,
            },
        )
    ]


def test_unrelated_remote_model_does_not_receive_jina_only_kwargs(monkeypatch):
    reranking = _load_reranking()
    calls = []

    class AutoTokenizer:
        @staticmethod
        def from_pretrained(model_source, **kwargs):
            calls.append((model_source, kwargs))
            return object()

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(AutoTokenizer=AutoTokenizer),
    )

    reranking._load_tokenizer("example/other-model")

    assert calls == [("example/other-model", {})]


def test_explicit_remote_model_does_not_use_default_local_artifacts(monkeypatch):
    reranking = _load_reranking()
    calls = []
    monkeypatch.setattr(
        reranking,
        "_artifact_paths",
        lambda *_args: (Path("default-model"), Path("model_int8.onnx")),
    )
    monkeypatch.setattr(
        reranking,
        "_build_openvino",
        lambda *_args, **_kwargs: calls.append("openvino")
        or _FakeBackend("openvino"),
    )
    monkeypatch.setattr(
        reranking,
        "_build_torch",
        lambda source, _max_length, _device: calls.append(source)
        or _FakeBackend("torch_cpu"),
    )

    reranker = reranking.load_reranker(
        model_name="example/model",
        backend="openvino",
        device="cpu",
    )

    assert calls == ["example/model"]
    assert reranker.backend == "torch_cpu"

def test_resolve_backend_prefers_openvino_on_cpu(monkeypatch):
    reranking = _load_reranking()
    monkeypatch.delenv("RAG_BACKEND", raising=False)
    monkeypatch.delenv("RAG_DEVICE", raising=False)
    monkeypatch.setattr(
        reranking,
        "torch",
        type("T", (), {"cuda": type("C", (), {"is_available": staticmethod(lambda: False)})})(),
    )
    assert reranking.resolve_backend() == "openvino"


def test_resolve_backend_selects_tensorrt_on_cuda(monkeypatch):
    reranking = _load_reranking()
    monkeypatch.delenv("RAG_BACKEND", raising=False)
    monkeypatch.delenv("RAG_DEVICE", raising=False)
    monkeypatch.setattr(
        reranking,
        "torch",
        type("T", (), {"cuda": type("C", (), {"is_available": staticmethod(lambda: True)})})(),
    )
    assert reranking.resolve_backend() == "tensorrt"


def test_resolve_backend_respects_explicit_choice(monkeypatch):
    reranking = _load_reranking()
    monkeypatch.setenv("RAG_BACKEND", "onnx")
    assert reranking.resolve_backend() == "onnx"


def test_load_reranker_honors_explicit_backend_before_fallback(monkeypatch):
    reranking = _load_reranking()
    calls = []
    monkeypatch.setattr(
        reranking,
        "_artifact_paths",
        lambda *_args: (Path("."), Path("model_int8.onnx")),
    )
    monkeypatch.setattr(
        reranking,
        "_build_openvino",
        lambda *_args, **_kwargs: calls.append("openvino"),
    )
    monkeypatch.setattr(
        reranking,
        "_build_onnx",
        lambda *_args, **_kwargs: calls.append("onnx") or _FakeBackend("onnx"),
    )

    reranker = reranking.load_reranker(backend="onnx", device="cpu")

    assert calls == ["onnx"]
    assert reranker.backend == "onnx"


def test_load_reranker_backend_none_bypasses_all_builders(monkeypatch):
    reranking = _load_reranking()

    def unexpected_builder(*_args, **_kwargs):
        raise AssertionError("backend builder must not run")

    monkeypatch.setattr(reranking, "_build_openvino", unexpected_builder)
    monkeypatch.setattr(reranking, "_build_onnx", unexpected_builder)
    monkeypatch.setattr(reranking, "_build_tensorrt", unexpected_builder)
    monkeypatch.setattr(reranking, "_build_torch", unexpected_builder)

    reranker = reranking.load_reranker(backend="none")

    assert reranker.backend == "none"


def test_load_reranker_cpu_device_overrides_available_cuda(monkeypatch):
    reranking = _load_reranking()
    calls = []
    monkeypatch.delenv("RAG_BACKEND", raising=False)
    monkeypatch.setattr(
        reranking,
        "torch",
        type(
            "T",
            (),
            {"cuda": type("C", (), {"is_available": staticmethod(lambda: True)})},
        )(),
    )
    monkeypatch.setattr(
        reranking,
        "_artifact_paths",
        lambda *_args: (Path("."), Path("model_int8.onnx")),
    )
    monkeypatch.setattr(
        reranking,
        "_build_openvino",
        lambda *_args, **_kwargs: calls.append("openvino")
        or _FakeBackend("openvino"),
    )
    monkeypatch.setattr(
        reranking,
        "_build_tensorrt",
        lambda *_args, **_kwargs: calls.append("tensorrt")
        or _FakeBackend("tensorrt"),
    )

    reranker = reranking.load_reranker(device="cpu")

    assert calls == ["openvino"]
    assert reranker.backend == "openvino"


def test_load_reranker_uses_model_name_for_torch_without_local_artifacts(
    monkeypatch,
):
    reranking = _load_reranking()
    calls = []
    monkeypatch.setattr(reranking, "_artifact_paths", lambda *_args: None)
    monkeypatch.setattr(
        reranking,
        "_build_torch",
        lambda model_source, _max_length, *_args: calls.append(model_source)
        or _FakeBackend("torch_cpu"),
    )

    reranker = reranking.load_reranker(
        model_name="example/model",
        backend="torch",
        device="cpu",
        allow_fallback=False,
    )

    assert calls == ["example/model"]
    assert reranker.backend == "torch_cpu"


def test_load_reranker_openvino_falls_back_to_onnx(monkeypatch):
    reranking = _load_reranking()
    calls = []

    def _raise_openvino(*_args, **_kwargs):
        calls.append("openvino")
        raise RuntimeError("openvino unavailable")

    def _fake_onnx(*_args, **_kwargs):
        calls.append("onnx")
        return _FakeBackend("onnx")

    monkeypatch.setattr(reranking, "_build_openvino", _raise_openvino)
    monkeypatch.setattr(reranking, "_build_onnx", _fake_onnx)

    reranker = reranking.load_reranker(max_length=256)
    assert calls == ["openvino", "onnx"]
    assert reranker.backend == "onnx"
    assert reranker.score_pairs("q", ["a", "b"]) == [0.9, 0.1]


def test_load_reranker_cuda_falls_back_to_torch_fp16(monkeypatch):
    reranking = _load_reranking()

    def _raise(name):
        def _inner(*_args, **_kwargs):
            raise RuntimeError(f"{name} unavailable")

        return _inner

    monkeypatch.setattr(reranking, "_build_tensorrt", _raise("tensorrt"))
    monkeypatch.setattr(reranking, "_build_onnx", _raise("onnx cuda"))
    monkeypatch.setattr(
        reranking, "_build_torch", lambda *_a, **_kw: _FakeBackend("torch_fp16")
    )

    reranker = reranking.load_reranker(backend="tensorrt", max_length=256)
    assert reranker.backend == "torch_fp16"


def test_load_reranker_bypass_mode():
    reranking = _load_reranking()
    reranker = reranking.load_reranker(model_name="none")
    assert reranker.backend == "none"
    assert reranker.score_pairs("query", ["a", "b"]) == [0.0, 0.0]


def _model_dir_available() -> bool:
    model_dir = Path(
        os.getenv(
            "RAG_RERANKER_MODEL_DIR",
            "artifacts/models/jina-reranker-v2-base-multilingual-9cfeff2",
        )
    )
    return (model_dir / "onnx" / "model_int8.onnx").exists() and (
        model_dir / "tokenizer.json"
    ).exists()


def test_load_reranker_openvino_scores_real_pairs():
    pytest.importorskip("openvino")
    if not _model_dir_available():
        pytest.skip("Cần model artifacts local (model_int8.onnx + tokenizer)")
    reranking = _load_reranking()
    reranker = reranking.load_reranker(backend="openvino", max_length=256)
    try:
        scores = reranker.score_pairs(
            "Mô hình dịch máy hoạt động ra sao?",
            ["Dịch máy huấn luyện bằng mạng nơ-ron.", "Hôm nay trời nắng đẹp."],
        )
        assert len(scores) == 2
        assert scores[0] > scores[1]
        assert all(0.0 <= float(score) <= 1.0 for score in scores)
    finally:
        del reranker


def test_openvino_scores_change_when_query_changes():
    pytest.importorskip("openvino")
    if not _model_dir_available():
        pytest.skip("Cần model artifacts local (model_int8.onnx + tokenizer)")

    reranking = _load_reranking()
    reranker = reranking.load_reranker(backend="openvino", max_length=256)
    documents = [
        "GAN gồm Generator và Discriminator đối nghịch nhau.",
        "Decision tree chia dữ liệu theo thuộc tính.",
    ]
    try:
        gan_scores = reranker.score_pairs("Discriminator trong GAN làm gì?", documents)
        tree_scores = reranker.score_pairs(
            "Decision tree hoạt động thế nào?", documents
        )
    finally:
        del reranker

    assert gan_scores != pytest.approx(tree_scores)


def test_load_reranker_onnx_scores_real_pairs():
    pytest.importorskip("onnxruntime")
    if not _model_dir_available():
        pytest.skip("Cần model artifacts local (model_int8.onnx + tokenizer)")
    reranking = _load_reranking()
    reranker = reranking.load_reranker(backend="onnx", max_length=256)
    try:
        scores = reranker.score_pairs(
            "Mô hình dịch máy hoạt động ra sao?",
            ["Dịch máy huấn luyện bằng mạng nơ-ron.", "Hôm nay trời nắng đẹp."],
        )
        assert len(scores) == 2
        assert scores[0] > scores[1]
    finally:
        del reranker
