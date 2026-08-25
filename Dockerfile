# Stage 1: Build Frontend Assets
FROM node:20-slim AS frontend-builder
WORKDIR /build

COPY package.json package-lock.json* tsconfig.json vite.config.ts tailwind.config.js* ./
RUN npm ci || npm install

COPY frontend/ ./frontend/
RUN npm run build

# Stage 2: Official Grafana MCP server binary (spawned over stdio by the agent)
FROM golang:1.26-bookworm AS mcp-builder
ENV CGO_ENABLED=0
RUN GOBIN=/out go install github.com/grafana/mcp-grafana/cmd/mcp-grafana@v1.2.0

# Stage 3: Runtime Backend & App Container
FROM python:3.12-slim AS runner
WORKDIR /app

ENV PYTHONUNBUFFERED=1     PYTHONDONTWRITEBYTECODE=1     DEMO_MODE=mock     PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends     curl     ca-certificates     && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
RUN pip install --no-cache-dir --upgrade pip &&     pip install --no-cache-dir .

COPY backend/ ./backend/
COPY synthetic/ ./synthetic/
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist
COPY --from=mcp-builder /out/mcp-grafana /usr/local/bin/mcp-grafana

# Pre-generate synthetic MCAP recording inside container
RUN python -c "from backend.app.integrations.mcap.generator import generate_synthetic_mcap; generate_synthetic_mcap('synthetic/recordings/stage_a_take_003.mcap')"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3   CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
