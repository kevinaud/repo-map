FROM mcr.microsoft.com/devcontainers/python:3.12

# ============================================================
# Dev Container Dockerfile
# ============================================================
# Dependencies are installed at build time for caching.
# init.sh syncs dependencies after workspace mount.
# ============================================================

# Install uv from official image (faster, always up-to-date)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Configure uv for optimal caching
ENV UV_LINK_MODE=copy
ENV UV_CACHE_DIR=/opt/uv-cache


# Set working directory for dependency installation
WORKDIR /workspace

# Copy dependency files for caching
# Using uv.loc* pattern so COPY doesn't fail if uv.lock doesn't exist
COPY pyproject.toml uv.loc* ./

# Install dependencies only (not the local project, since source isn't in container yet)
# The local project will be installed when the workspace is mounted
# Use --frozen only if lock file exists and is not empty, otherwise generate it
RUN if [ -s uv.lock ]; then \
      uv sync --frozen --no-install-project; \
    else \
      uv sync --no-install-project; \
    fi
