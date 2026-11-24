# Platform pytest image: Python 3.11 + project deps + Playwright Chromium.
#
# Build:
#   docker build -t platform-pytest .
# Optional Platform mirrors (build-args):
#   docker build \
#     --build-arg PIP_INDEX_URL=https://example.com/simple \
#     --build-arg PLAYWRIGHT_DOWNLOAD_HOST=https://example.com/raw-playwright-proxy/ \
#     -t platform-pytest .

ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE}

ARG PIP_INDEX_URL=
ARG PLAYWRIGHT_DOWNLOAD_HOST=

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

# System libs for Playwright Chromium (also pulled by --with-deps, but keep image self-contained)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      gcc \
      libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy install metadata first for better layer caching; tree matches greenfield layout.
COPY pyproject.toml ./
COPY tests ./tests
COPY config ./config
COPY data ./data
COPY secrets ./secrets
COPY AGENTS.md ./
COPY docs ./docs
COPY scripts ./scripts
COPY .cursor ./.cursor

# Install deps from pyproject (tests run via PYTHONPATH; package may be empty)
RUN if [ -n "$PIP_INDEX_URL" ]; then \
      pip install --index-url "$PIP_INDEX_URL" --no-cache-dir . ; \
    else \
      pip install --no-cache-dir . ; \
    fi

# Drop any non-example secrets that slipped into the build context
RUN find secrets -type f ! -name '*.example.yaml' ! -name '*.example.env' -delete 2>/dev/null || true

RUN if [ -n "$PLAYWRIGHT_DOWNLOAD_HOST" ]; then \
      PLAYWRIGHT_DOWNLOAD_HOST="$PLAYWRIGHT_DOWNLOAD_HOST" playwright install --with-deps chromium ; \
    else \
      playwright install --with-deps chromium ; \
    fi

# Real secrets / env YAML overrides should be mounted at runtime, not baked in.
CMD ["pytest", "--collect-only", "-q"]
