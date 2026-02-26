ARG PYTHON_VERSION=3.13.8
FROM python:${PYTHON_VERSION}-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install build dependencies
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libglib2.0-0 \
    libgobject-2.0-0 \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install the project's dependencies based on pyproject.toml
# Use --no-install-project so uv does not try to install the local package
# (the source tree is not copied yet at this stage).
COPY pyproject.toml /app/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --all-groups --no-install-project

COPY entrypoint.sh /app/entrypoint.sh

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

# Development stage
FROM base AS development

WORKDIR /app

# Copy source code
COPY . .

# Ensure entrypoint remains executable after copying source
RUN chmod +x /app/entrypoint.sh

# Use entrypoint to download models at runtime, then start with hot reload
CMD ["uv", "run", "--frozen", "python", "-m", "watchdog.watchmedo", "auto-restart", "--directory", "/app", "--patterns=*.py;*.yaml", "--recursive", "--no-restart-on-command-exit", "--debounce-interval", "0.2", "--", "python3", "src/agent.py", "start"]

# Production stage
FROM base AS production

WORKDIR /app

# Create non-privileged user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/app" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    user

# Copy source code
COPY . .

# Create cache directory and set permissions
RUN mkdir -p /app/.cache/uv && \
    chmod +x /app/entrypoint.sh && \
    chown -R user:user /app

USER user

# Set UV cache directory to a writable location
ENV UV_CACHE_DIR=/app/.cache/uv

CMD ["uv", "run", "src/agent.py", "start"]

