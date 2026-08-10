FROM python:3.12-slim

# ---------------------------------------------------------------------------
# System packages that pip cannot provide.
#   tesseract-ocr  -> pytesseract (analyse_material_service.py)
#   poppler-utils  -> pdf2image.convert_from_path
# Both fail at runtime with obscure errors if missing, not at build time.
# libgomp1 is required by scikit-learn / torch at import.
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr \
      poppler-utils \
      libgomp1 \
      wget \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # Default listening port; override at runtime with `-e PORT=…`. Not a build
    # arg on purpose — that would make the port part of the image cache key.
    PORT=8000 \
    # Model cache lives inside the image, not a volume — see the pre-download
    # step below. HF_HOME must be set before any transformers import.
    HF_HOME=/opt/hf-cache

# ---------------------------------------------------------------------------
# torch FIRST, from the CPU-only index.
#
# Installing it via requirements.txt would pull the CUDA build and ~2.5GB of
# nvidia-* wheels onto a server with no GPU. Installing the CPU wheel here means
# the pinned torch==2.7.1 in requirements.txt is already satisfied and pip skips
# it. Keep the version in sync with requirements.txt.
# ---------------------------------------------------------------------------
RUN pip install --no-cache-dir torch==2.7.1 \
      --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Created before the model download so the cache can be chowned in the same
# layer — huggingface_hub writes marker files into it at load time, so a
# read-only cache produces permission errors on every start.
RUN useradd --create-home --uid 10001 appuser

# ---------------------------------------------------------------------------
# Bake the embedding model into the image.
#
# vector_search_service.py evaluates HuggingFaceEmbeddings(...) as a DEFAULT
# ARGUMENT, so it runs at import time — and main.py imports that router at the
# top level. Without the model present the container would download ~420MB on
# every cold start, and would fail to boot at all if HuggingFace were
# unreachable. Pre-fetching makes start-up offline and deterministic.
# ---------------------------------------------------------------------------
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-mpnet-base-v2')" \
 && chown -R appuser:appuser /opt/hf-cache

COPY . .

# Non-root. The user is created earlier, above the model download.
RUN chown -R appuser:appuser /app
USER appuser

# Documentation only — the compose file's `expose:` is what Coolify routes to,
# and that one follows ${PORT}.
EXPOSE 8000

# GET / returns 200 with a JSON body and touches no database, so it reports
# process health without depending on Mongo or any upstream API.
# Shell form, so ${PORT} is expanded at check time rather than baked in.
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD wget -qO- "http://127.0.0.1:${PORT}/" || exit 1

# `sh -c` so ${PORT} expands, and `exec` so uvicorn replaces the shell as PID 1
# — otherwise SIGTERM stops at the shell and the container waits for the
# 10s kill timeout on every redeploy instead of shutting down cleanly.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
