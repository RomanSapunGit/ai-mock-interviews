FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev && rm -rf /root/.cache/uv

# Bake the embedding model into the image so containers never download it
# from HuggingFace at runtime — on small instances that download/load was
# slow enough to look like a hang and risked OOM during cold start.
ENV FASTEMBED_CACHE_PATH=/opt/fastembed_cache
RUN /opt/venv/bin/python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2')"

COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
