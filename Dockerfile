FROM node:22-bookworm-slim AS web
WORKDIR /build
COPY package*.json ./
RUN npm ci
COPY tsconfig.json vite.config.ts ./
COPY web ./web
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
COPY backend ./backend
COPY integration ./integration
COPY --from=web /build/dist ./dist
RUN useradd --uid 10001 --create-home observatorio && mkdir -p data && chown -R observatorio:observatorio /app
USER observatorio
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD /app/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)" || exit 1
CMD ["/app/.venv/bin/uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
