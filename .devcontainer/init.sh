#!/bin/bash
# ============================================================
# Dev Container Initialization Script
# ============================================================
# Syncs dependencies after workspace mount.
#
# This runs as postCreateCommand (once after container create).
# See post-start.sh for things that run every container start.
# ============================================================

set -e

echo "🚀 Initializing dev container..."

# ------------------------------------------------------------
# Fix uv-cache permissions (for CI runner compatibility)
# ------------------------------------------------------------
if [ -d "/opt/uv-cache" ]; then
    if [ ! -w "/opt/uv-cache" ]; then
        echo "🔧 Fixing uv-cache permissions..."
        sudo chown -R "$(id -u):$(id -g)" /opt/uv-cache 2>/dev/null || true
    fi
fi

# ------------------------------------------------------------
# Create .env from .env.example if it doesn't exist
# ------------------------------------------------------------
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
fi

# ------------------------------------------------------------
# Python Dependencies: Sync with uv
# ------------------------------------------------------------
echo "🐍 Syncing Python dependencies..."
uv sync

echo "✅ Dev container initialization complete!"
