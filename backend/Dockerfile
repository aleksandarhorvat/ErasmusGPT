FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models

WORKDIR /srv

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# CPU-only torch first: the CUDA wheels are ~2.5 GB and we never use a GPU here.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.5.1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the models into the image so the demo runs with no network at all.
COPY app/core/config.py app/core/config.py
COPY app/__init__.py app/__init__.py
COPY app/core/__init__.py app/core/__init__.py
COPY scripts/download_models.py scripts/download_models.py
# CI builds with BAKE_MODELS=0 and MATCHER_IMPL=stub so the end-to-end smoke test does
# not have to download 220 MB of models. Any real run leaves this at 1.
ARG BAKE_MODELS=1
RUN if [ "$BAKE_MODELS" = "1" ]; then python scripts/download_models.py; \
    else echo "BAKE_MODELS=0: skipping model download, MATCHER_IMPL=stub only"; fi

COPY . .

# From here on, nothing may reach huggingface.co.
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    OMP_NUM_THREADS=4

EXPOSE 8000
# start-period has to cover a COLD start, not the warm one you get while data/.cache is
# on the host. On a fresh clone the cache is empty (it is git-ignored), so boot encodes
# about 596 course vectors and 3096 sentence vectors with bge-small on CPU before the
# first health probe can succeed. If this window is too short the container is marked
# unhealthy and the frontend, which waits on service_healthy, never starts at all.
# A generous window costs nothing when startup is fast.
HEALTHCHECK --interval=15s --timeout=5s --start-period=300s --retries=10 \
  CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
