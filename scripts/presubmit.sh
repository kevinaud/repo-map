#!/bin/bash
# ============================================================
# Presubmit Checks
# ============================================================
# Runs the full suite of CI checks:
# 1. Quality checks (linting, formatting, type checking)
# 2. Unit and integration tests
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🚀 Starting Presubmit Checks..."

# Run Quality Checks
echo ""
echo "📋 Running Quality Checks..."
./scripts/check_quality.sh

# Run Unit and Integration Tests
echo ""
echo "🧪 Running Tests..."
uv run pytest tests/unit tests/integration -v

echo ""
echo "✅ All presubmit checks passed!"
