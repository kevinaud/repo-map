# Implementation Plan: Context Engine - Multi-Resolution Rendering

**Branch**: `001-context-engine` | **Date**: 2025-12-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-context-engine/spec.md`

## Summary

Transform repo-map from a static visualization tool into a dynamic, queryable rendering engine. The engine accepts YAML "Flight Plans" specifying token budgets, verbosity levels (0-4) per file/section, focus boosting, and custom queries. It outputs deterministic, budget-aware context windows optimized for LLM consumption.

**Technical approach**: Extend existing PageRank-based architecture with:
1. Pydantic `FlightPlan` schema for YAML configuration validation
2. Tiered tree-sitter query system for multi-resolution extraction
3. Personalization vector injection for symbol/path boosting
4. New `ContextRenderer` class for budget-aware output composition

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: typer (CLI), pydantic + PyYAML (config), networkx (graphing), tree-sitter via grep-ast (parsing)  
**Storage**: diskcache/SQLite for tag caching (existing)  
**Testing**: pytest with classical style, fixtures in `tests/fixtures/`  
**Target Platform**: CLI tool, cross-platform  
**Project Type**: Single project (existing structure)  
**Performance Goals**: 10,000-file repository in <30 seconds (SC-003)  
**Constraints**: Token budget accuracy within ±5% (SC-001), deterministic output (SC-008)  
**Scale/Scope**: Repositories up to 10k files, flight plans with 50+ verbosity rules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. First Principles Design | Extends existing PageRank architecture rather than replacing; aligns with core goal of context optimization | ✅ |
| II. Simplicity | Single new module (`flight_plan.py`), extends existing `tags.py` and `repomap.py`; no new abstractions beyond what's required | ✅ |
| III. Testing Strategy | Unit tests for FlightPlan validation, e2e tests with fixture repos for verbosity levels and cost accuracy | ✅ |
| IV. Clean Modern Python | Type hints, pydantic models, structlog logging; 2-space indent per project convention | ✅ |
| V. Makefile Workflows | No new Makefile targets needed; existing `make test`, `make quality` cover new code | ✅ |
| VI. Environment as Code | `uv add pyyaml` for new dependency; no manual setup | ✅ |

## Project Structure

### Documentation (this feature)

```text
specs/001-context-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
repo_map/
├── __init__.py
├── cli/
│   └── app.py              # MODIFY: Add --config, --strict, --show-costs flags
├── core/
│   ├── __init__.py
│   ├── repomap.py          # MODIFY: Add personalization parameter to PageRank
│   ├── tags.py             # MODIFY: Support tiered query loading
│   ├── special.py          # (unchanged)
│   ├── verbosity.py        # NEW: VerbosityLevel enum
│   ├── flight_plan.py      # NEW: FlightPlan Pydantic model + validation
│   ├── renderer.py         # NEW: ContextRenderer for budget-aware output
│   ├── cost.py             # NEW: Cost calculation utilities
│   └── queries/
│       └── tree-sitter-language-pack/
│           ├── python-tags.scm       # (unchanged, becomes Level 2+3 default)
│           ├── python-structure.scm  # NEW: Level 2 - definitions only
│           ├── python-interface.scm  # NEW: Level 3 - defs + signatures + docstrings
│           ├── markdown-tags.scm     # (unchanged)
│           ├── markdown-structure.scm # NEW: Level 2 - headings only
│           ├── markdown-interface.scm # NEW: Level 3 - headings + first paragraph
│           └── ...                   # Similar for other languages
├── mapper.py               # MODIFY: Accept FlightPlan, wire to new components
├── settings.py             # (unchanged)
└── logging_config.py       # (unchanged)

tests/
├── conftest.py
├── fixtures/
│   ├── sample-repo/        # NEW: Sample repo for e2e tests
│   │   ├── src/
│   │   ├── docs/
│   │   └── README.md
│   └── flight-plans/       # NEW: Sample YAML configs
│       ├── basic.yaml
│       └── complex.yaml
├── integration/
│   ├── __init__.py
│   └── test_context_engine.py  # NEW: E2E tests for full rendering pipeline
└── unit/
    ├── __init__.py
    ├── test_flight_plan.py     # NEW: FlightPlan validation tests
    ├── test_cost.py            # NEW: Cost calculation tests
    ├── test_renderer.py        # NEW: Renderer unit tests
    └── test_markdown_tags.py   # (existing)
```

**Structure Decision**: Extends existing single-project structure. New modules added to `repo_map/core/` following established patterns. New test fixtures for e2e testing with realistic repositories.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |

---

## Phase 0: Research

### Research Tasks

1. **NetworkX personalization API** - How to inject personalization vector for PageRank biasing
2. **Tree-sitter query patterns** - Best practices for extracting signatures/docstrings at different granularities
3. **YAML configuration patterns** - Pydantic + PyYAML integration for strict schema validation
4. **Glob pattern matching** - pathspec library usage for file and symbol matching

### Findings

See [research.md](research.md) for detailed findings.

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) for entity definitions.

### API Contracts

See [contracts/](contracts/) for:
- `flight-plan-schema.yaml` - YAML configuration schema
- `cli-interface.md` - CLI argument specifications

### Quickstart

See [quickstart.md](quickstart.md) for implementation sequence.

---

## Post-Design Constitution Re-Check

| Principle | Check | Status |
|-----------|-------|--------|
| I. First Principles Design | Design extends existing architecture; no unnecessary rewrites | ✅ |
| II. Simplicity | 3 new modules (flight_plan, cost, renderer); minimal abstraction | ✅ |
| III. Testing Strategy | Unit tests per module + e2e with fixtures; classical style | ✅ |
| IV. Clean Modern Python | Pydantic models, type hints, 2-space indent | ✅ |
| V. Makefile Workflows | Existing targets cover new code | ✅ |
| VI. Environment as Code | Only `uv add pyyaml` needed | ✅ |

**Gate Status**: ✅ PASSED - Ready for Phase 2 (task breakdown via `/speckit.tasks`)

