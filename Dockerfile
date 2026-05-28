# FundGenesis - Financial Reflexivity Multi-Agent Simulation
# Multi-stage build for production deployment

# ── Stage 1: Builder ──────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Production ──────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="FundGenesis Team"
LABEL description="Narrative-Driven Financial Reflexivity Multi-Agent World Model"
LABEL version="1.0"

# Create non-root user
RUN groupadd -r fundgenesis && useradd -r -g fundgenesis -d /app fundgenesis

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy project source
COPY core/ ./core/
COPY agents/ ./agents/
COPY narrative/ ./narrative/
COPY social/ ./social/
COPY trust/ ./trust/
COPY monitor/ ./monitor/
COPY risk/ ./risk/
COPY experiments/ ./experiments/
COPY dashboard/ ./dashboard/
COPY config/ ./config/
COPY main.py .
COPY pytest.ini .
COPY tests/ ./tests/

# Create outputs directory
RUN mkdir -p outputs && chown -R fundgenesis:fundgenesis /app

USER fundgenesis

# Default port for dashboard API
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')" || exit 1

# Default command: run the dashboard API server
CMD ["python", "dashboard/app.py", "--port", "8765"]
