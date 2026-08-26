# Stage 1: Build Frontend Assets
FROM node:20-slim AS frontend-builder
WORKDIR /build

COPY package.json package-lock.json* tsconfig.json vite.config.ts tailwind.config.js* ./
RUN npm ci || npm install

COPY frontend/ ./frontend/
RUN npm run build

# Stage 2: Runtime Backend & App Container
FROM python:3.12-slim AS runner
WORKDIR /app

ENV PYTHONUNBUFFERED=1     PYTHONDONTWRITEBYTECODE=1     DEMO_MODE=mock     PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends     curl     ca-certificates     && rm -rf /var/lib/apt/lists/*

# Official Grafana MCP server, spawned over stdio by the agent. Pulled from the
# published release rather than compiled here: Cloud Build keeps no layer cache,
# so a Go builder stage recompiled it on every deploy and eventually ran the
# build past its timeout.
ARG MCP_GRAFANA_VERSION=1.2.0
RUN curl -fsSL "https://github.com/grafana/mcp-grafana/releases/download/v${MCP_GRAFANA_VERSION}/mcp-grafana_Linux_x86_64.tar.gz" -o /tmp/mcp.tar.gz \
    && tar -xzf /tmp/mcp.tar.gz -C /usr/local/bin mcp-grafana \
    && chmod +x /usr/local/bin/mcp-grafana \
    && unlink /tmp/mcp.tar.gz \
    && /usr/local/bin/mcp-grafana --version

COPY pyproject.toml README.md LICENSE ./
RUN pip install --no-cache-dir --upgrade pip &&     pip install --no-cache-dir .

COPY backend/ ./backend/
COPY synthetic/ ./synthetic/
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# Pre-generate synthetic MCAP recording inside container
RUN python -c "from backend.app.integrations.mcap.generator import generate_synthetic_mcap; generate_synthetic_mcap('synthetic/recordings/stage_a_take_003.mcap')"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3   CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
