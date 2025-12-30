# ============================================================
# repo-map - Developer Makefile
# ============================================================
# This Makefile is the entry point for all common developer workflows.
#
# Usage:
#   make help        - Show available targets
#   make quality     - Run all quality checks
#   make test        - Run all tests
#   make presubmit   - Run full presubmit checks
# ============================================================

.PHONY: help quality lint format test test-unit test-integration presubmit clean


# Default target
.DEFAULT_GOAL := help


# ============================================================
# Help
# ============================================================
help:
	@echo "repo-map - Developer Commands"
	@echo ""

	@echo "Quality:"
	@echo "  make quality      - Run all quality checks (lint, format, types)"
	@echo "  make lint         - Run linters only"
	@echo "  make format       - Auto-format all code"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-unit    - Run unit tests only"
	@echo "  make test-int     - Run integration tests only"
	@echo ""
	@echo "CI:"
	@echo "  make presubmit    - Run full presubmit checks"


# ============================================================
# Quality Checks
# ============================================================

quality:

	@./scripts/check_quality.sh

lint:

	@uv run ruff check .

format:
	@echo "🎨 Formatting code..."
	@uv run ruff check --fix .
	@uv run ruff format .
	@echo "✅ Formatting complete!"

# ============================================================
# Testing
# ============================================================

test:

	@uv run pytest tests/ -v

test-unit:

	@uv run pytest tests/unit -v

test-int:

	@uv run pytest tests/integration -v --run-integration

# ============================================================
# CI / Presubmit
# ============================================================

presubmit:

	@./scripts/presubmit.sh
