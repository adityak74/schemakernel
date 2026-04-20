# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies and the package
COPY pyproject.toml .
COPY schemakernel/ ./schemakernel/
COPY README.md .
RUN pip install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (like libpq for postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code (optional if already in venv, but good for clarity/hotfix)
COPY schemakernel/ ./schemakernel/
COPY README.md .

# Run as non-root user
RUN useradd -m schemakernel && chown -R schemakernel:schemakernel /app
USER schemakernel

# Labels
LABEL org.opencontainers.image.source="https://github.com/schemakernel/schemakernel"
LABEL org.opencontainers.image.description="Adaptive form engine powered by LLM-driven structured field planning"

# Default entrypoint
CMD ["python", "-m", "schemakernel"]
