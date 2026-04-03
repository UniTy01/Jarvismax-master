# ================================================================
# JARVIS MAX — Dockerfile (multi-stage production build)
# ================================================================

FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ──────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*
# NOTE: git is required by core/self_improvement/git_agent.py (subprocess git commands).
# If SI is fully disabled in prod, git can be removed to reduce attack surface.

# Node.js 22 LTS — required for MCP server stdio transport (npx)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version && npx --version

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# App code
COPY . .

# Create directories
RUN mkdir -p /app/workspace/projects \
             /app/workspace/reports \
             /app/workspace/missions \
             /app/workspace/patches \
             /app/workspace/.backups \
             /app/data/modules \
             /app/data/mcp \
             /app/logs

# Ensure critical pip packages are installed
RUN pip install --no-cache-dir PyJWT>=2.0 mcp-server-fetch mcp-server-sqlite

# Pre-download sentence-transformers model so it's cached in image
# Eliminates ~120s cold-start delay on first mission
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" \
    2>/dev/null || echo "sentence-transformers not installed, skipping model cache"

# Entrypoint: creates runtime data dirs that are hidden by the ./:/app bind-mount
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Non-root user
RUN useradd -m jarvis && chown -R jarvis:jarvis /app
USER jarvis

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "main.py"]
