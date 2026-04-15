FROM python:3.12-slim AS builder

RUN pip install uv -i https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple uv sync --frozen --no-dev --no-install-project

COPY src/ src/
COPY gen/ gen/
COPY config/ config/

RUN UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple uv sync --frozen --no-dev

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/gen /app/gen
COPY --from=builder /app/config /app/config
COPY scripts/ scripts/
COPY data/ data/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:/app/gen"
ENV PYTHONUNBUFFERED=1
ENV HF_ENDPOINT=https://hf-mirror.com
ENV HF_HOME=/app/data/hf_cache

# Install psql client for demo initialization
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

EXPOSE 50051

CMD ["python", "-m", "gameserver.main"]
