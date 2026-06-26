ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS prod-cpu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    TOKENIZERS_PARALLELISM=false \
    RAG_DEVICE=cpu

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.runtime.txt requirements.cpu.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.cpu.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM prod-cpu AS pipeline-cpu

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.pipeline.txt ./
RUN pip install -r requirements.pipeline.txt

CMD ["python", "-m", "src.data_pipeline.pipeline"]

FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime AS dev-gpu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    TOKENIZERS_PARALLELISM=false \
    RAG_DEVICE=cuda

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ffmpeg \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.runtime.txt requirements.gpu.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.gpu.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM dev-gpu AS pipeline-gpu

COPY requirements.pipeline.txt ./
RUN pip install -r requirements.pipeline.txt

CMD ["python", "-m", "src.data_pipeline.data_loader.pipeline"]

FROM dev-gpu AS prod-gpu
ENV RAG_DEVICE=cuda
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
