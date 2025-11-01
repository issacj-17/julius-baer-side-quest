# 🏦 Modern Banking Transfer Client - Docker Image
FROM python:3.11-slim

# Set metadata
LABEL maintainer="issacj-17"
LABEL description="Modern Banking Transfer Client with JWT auth and comprehensive features"
LABEL version="0.1.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY uv.lock .
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir httpx>=0.28.1 && \
    pip install --no-cache-dir -e .

# Set environment variables (can be overridden at runtime)
ENV BANKING_API_URL=http://host.docker.internal:8123
ENV BANKING_USERNAME=alice
ENV BANKING_PASSWORD=password123
ENV BANKING_USE_AUTH=true
ENV BANKING_AUTH_SCOPE=transfer
ENV BANKING_LOG_LEVEL=INFO
ENV BANKING_MAX_RETRIES=3
ENV BANKING_RETRY_BACKOFF=1.0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f ${BANKING_API_URL}/accounts/validate/ACC1000 || exit 1

# Set entrypoint to the CLI
ENTRYPOINT ["transfer-client"]

# Default command (can be overridden)
CMD ["--help"]
