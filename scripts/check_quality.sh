#!/bin/bash
# ============================================================
# Quality Check Script
# ============================================================
# Runs code quality checks for the Python project.
# Exits immediately if any check fails.
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "========================================"
echo "  Code Quality Checks"
echo "========================================"

echo ""
echo "----------------------------------------"
echo "  Python"
echo "----------------------------------------"

echo "Running Pyright (type check)..."
uv run pyright

echo "Running Ruff (lint)..."
uv run ruff check .

echo "Running Ruff (format check)..."
uv run ruff format --check .

echo "✅ Python checks passed!"

echo ""
echo "========================================"
echo "  ✅ All quality checks passed!"
echo "========================================"
