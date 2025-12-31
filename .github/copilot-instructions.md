# Copilot Instructions for repo-map

## Project Overview

A CLI tool that generates concise repository "maps" for LLMs using PageRank-based ranking. Extracts code definitions via tree-sitter, builds a relationship graph, and outputs ranked code structures within a token budget.

## Architecture

```
repo_map/
├── cli/app.py          # Typer CLI entry point
├── mapper.py           # High-level API, file filtering with pathspec
├── core/
│   ├── repomap.py      # PageRank algorithm, caching (diskcache/SQLite)
│   ├── tags.py         # Tree-sitter tag extraction, pygments fallback
│   ├── special.py      # Important file detection (README, configs)
│   └── queries/*.scm   # Tree-sitter query files per language
└── settings.py         # Pydantic settings with .env support
```

**Data flow**: CLI → `generate_repomap()` → `RepoMap.get_repo_map()` → tag extraction → PageRank ranking → tree rendering

## Development Commands

```bash
# Setup
uv sync                           # Install dependencies (uses uv, not pip)

# Quality (run before commits)
make quality                      # Runs: pyright + ruff check + ruff format --check
make format                       # Auto-fix formatting

# Tests
make test                         # All tests
make test-unit                    # Unit tests only
make test-int                     # Integration tests (requires --run-integration)
```

## Code Conventions

### Style
- **2-space indentation** (configured in ruff)
- Python 3.12+ with full type hints
- Use `from __future__ import annotations` for forward references
- Imports in `TYPE_CHECKING` blocks when only needed for types

### Patterns
- **Settings**: Use `repo_map.settings.Settings` (pydantic-settings) for configuration
- **Logging**: Use `structlog` with the configured logger from `logging_config.py`
- **CLI output**: Use `rich.Console(stderr=True)` for logs, stdout for data
- **Caching**: `RepoMap` uses diskcache with SQLite, handles errors gracefully via `_tags_cache_error()`

### Testing
- Unit tests in `tests/unit/`, integration in `tests/integration/`
- Mark integration tests with `@pytest.mark.integration`
- Integration tests skipped by default; run with `--run-integration`

## Key Implementation Details

- **Tag extraction** ([tags.py](repo_map/core/tags.py)): Tree-sitter primary, pygments fallback for references when tree-sitter only provides definitions
- **Default excludes** ([mapper.py](repo_map/mapper.py#L9-L31)): Lock files, IDE folders, caches are excluded by default
- **Token estimation**: Simple heuristic of `len(text) // 4` characters per token

## Entry Point

```bash
uv run repo-map --help            # CLI usage
uv run repo-map generate . -t 5000  # Generate map with 5000 token budget
```

CLI defined in `pyproject.toml`:
```toml
[project.scripts]
repo-map = "repo_map.cli.app:app"
```
