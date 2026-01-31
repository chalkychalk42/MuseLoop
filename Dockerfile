FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Copy application
COPY src/ src/
COPY prompts/ prompts/
COPY examples/ examples/

# Run as non-root user
RUN useradd --create-home --shell /bin/bash museloop \
    && chown -R museloop:museloop /app
USER museloop

ENTRYPOINT ["uv", "run", "museloop"]
