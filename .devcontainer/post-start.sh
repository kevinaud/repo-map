#!/bin/bash
# ============================================================
# Dev Container Post-Start Script
# ============================================================
# Runs every time the container starts (not just on create)
# ============================================================

# ------------------------------------------------------------
# GitHub CLI Auto-Login
# ------------------------------------------------------------
# The token file is bind-mounted from the host at container start.
# This must run in postStartCommand (not postCreateCommand)
# because the mount isn't available during image build/create.
# ------------------------------------------------------------
TOKEN_FILE="/home/vscode/.gh_token_file"

if [ -s "$TOKEN_FILE" ]; then
    echo "🔑 Auto-logging into GitHub CLI..."
    gh auth login --with-token < "$TOKEN_FILE"
    echo "✅ GitHub CLI authenticated"
else
    echo "⚠️  No GitHub token found at $TOKEN_FILE"
    echo "   To enable auto-login, create ~/.gh_token_file on your host"
    echo "   with a GitHub personal access token."
fi

# Sync dependencies (in case lock file changed)
uv sync
