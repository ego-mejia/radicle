# syntax=docker/dockerfile:1.7

# --- frontend build --------------------------------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /app/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# --- python dependencies ---------------------------------------------------------------
FROM python:3.12-slim AS backend
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --frozen --no-dev

# --- runtime ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime
# Chromium prints Folio's PDF exports (5.2). It adds about 300 MB to the image; build with
# --build-arg PDF=false to leave it out, and PDF exports then fail with a clear message.
ARG PDF=true
RUN if [ "$PDF" = "true" ]; then \
      apt-get update \
      && apt-get install -y --no-install-recommends chromium fonts-liberation fonts-noto-color-emoji \
      && rm -rf /var/lib/apt/lists/*; \
    fi
ENV RADICLE_CHROMIUM_PATH=/usr/bin/chromium
RUN groupadd --system radicle && useradd --system --gid radicle --home /app radicle \
    && mkdir -p /data/attachments && chown -R radicle:radicle /data
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    RADICLE_STATIC_DIR=/app/static
WORKDIR /app/backend
COPY --from=backend /opt/venv /opt/venv
COPY --from=backend /app/backend /app/backend
COPY --from=frontend /app/frontend/dist /app/static
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
USER radicle
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/health').status != 200)"
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "radicle.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
