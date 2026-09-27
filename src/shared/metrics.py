"""Các metric Prometheus dùng chung cho tiến trình API."""

import logging
from contextlib import contextmanager
from time import perf_counter

from prometheus_client import Counter, Gauge, Histogram


# Histogram latency dùng chung có các mốc dài để không cắt cụt request chậm.
_DURATION_BUCKETS = (
    0.05,
    0.1,
    0.25,
    0.5,
    1,
    2,
    5,
    10,
    15,
    30,
    60,
    120,
    300,
    600,
)
_TTFT_BUCKETS = (
    0.05,
    0.1,
    0.25,
    0.5,
    1,
    2,
    5,
    10,
    30,
    60,
    120,
    300,
    600,
)

CHAT_REQUESTS = Counter(
    "puq_chat_requests_total",
    "Lượt chat kết thúc",
    labelnames=("route", "outcome", "cache"),
)
CHAT_DURATION = Histogram(
    "puq_chat_duration_seconds",
    "Thời gian xử lý lượt chat",
    labelnames=("route", "outcome", "cache"),
    buckets=_DURATION_BUCKETS,
)
CHAT_TTFT = Histogram(
    "puq_chat_ttft_seconds",
    "Thời gian tới token trả lời đầu",
    labelnames=("route", "cache"),
    buckets=_TTFT_BUCKETS,
)
CHAT_ACTIVE = Gauge("puq_chat_active", "Luồng chat đang hoạt động")

JEV_REQUESTS = Counter(
    "puq_jev_requests_total",
    "Lượt gọi Jev",
    labelnames=("outcome",),
)
JEV_DURATION = Histogram(
    "puq_jev_duration_seconds",
    "Thời gian gọi Jev",
    labelnames=("outcome",),
    buckets=_DURATION_BUCKETS,
)
SUPERVISOR_FALLBACKS = Counter(
    "puq_supervisor_fallbacks_total",
    "Lượt supervisor fallback sang Luna",
    labelnames=("reason",),
)
AGENT_NODE_DURATION = Histogram(
    "puq_agent_node_duration_seconds",
    "Thời gian xử lý node agent",
    labelnames=("node", "outcome"),
    buckets=_DURATION_BUCKETS,
)
RAG_STAGE_DURATION = Histogram(
    "puq_rag_stage_duration_seconds",
    "Thời gian xử lý từng bước RAG",
    labelnames=("stage", "outcome"),
    buckets=_DURATION_BUCKETS,
)


@contextmanager
def measure_rag_stage(stage: str):
    """Đo thời gian RAG cho Prometheus, không tạo span Langfuse."""
    started = perf_counter()
    outcome = "error"
    try:
        yield
        outcome = "success"
    finally:
        try:
            RAG_STAGE_DURATION.labels(stage=stage, outcome=outcome).observe(
                perf_counter() - started
            )
        except Exception as error:
            logging.getLogger(__name__).warning(
                "Không thể ghi RAG metric (%s)", type(error).__name__
            )


__all__ = [
    "CHAT_REQUESTS",
    "CHAT_DURATION",
    "CHAT_TTFT",
    "CHAT_ACTIVE",
    "JEV_REQUESTS",
    "JEV_DURATION",
    "SUPERVISOR_FALLBACKS",
    "AGENT_NODE_DURATION",
    "RAG_STAGE_DURATION",
    "measure_rag_stage",
]
