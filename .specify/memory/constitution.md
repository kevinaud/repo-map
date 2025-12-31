<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version change: 0.0.0 → 1.0.0 (MAJOR: Initial constitution ratification)

Modified principles: N/A (initial version)

Added sections:
  - Core Principles (6 principles)
  - Development Workflow
  - Quality Gates
  - Governance

Removed sections: N/A

Templates requiring updates:
  ✅ plan-template.md - Constitution Check section aligned with principles
  ✅ spec-template.md - No changes required
  ✅ tasks-template.md - No changes required

Follow-up TODOs: None
================================================================================
-->

# repo-map Constitution

## Core Principles

### I. First Principles Design

Every feature and change MUST be evaluated against the fundamental goals of the
project. When working on individual features, always consider the big picture:

- **Question existing designs**: Before adding new code, evaluate whether
  existing architecture, patterns, or implementations should be reconsidered
  in light of new requirements.
- **Incremental reconsideration**: Each incremental requirement is an
  opportunity to reassess prior decisions—not just extend them.
- **Root cause focus**: Solve problems at their source rather than adding
  workarounds or patches.
- **Design for change**: Prefer designs that remain adaptable as understanding
  evolves.

**Rationale**: Code accumulates complexity over time. Constant reevaluation
prevents technical debt from compounding and ensures the codebase remains
aligned with actual needs rather than historical assumptions.

### II. Simplicity Above All

Simplicity is a primary design goal, not a secondary concern:

- **YAGNI enforced**: Do not implement functionality until it is actually needed.
- **Remove before adding**: When adding a feature, first consider what can be
  removed or simplified.
- **Minimal abstractions**: Introduce abstractions only when they reduce overall
  complexity; premature abstraction is a form of complexity.
- **Clear over clever**: Prefer straightforward, readable solutions over
  sophisticated but opaque ones.
- **Single responsibility**: Each module, class, and function should have one
  clear purpose.

**Rationale**: Simple systems are easier to understand, test, modify, and debug.
Complexity should require explicit justification.

### III. Testing Strategy

Maintain a healthy balance of unit tests and end-to-end (e2e) tests:

**Unit Tests (Classical Style)**:
- Prefer "classical" testing over "mockist" testing.
- Provide real implementations of dependencies whenever doing so does NOT
  significantly impact test execution speed or setup complexity.
- Fall back to mocking ONLY when real implementations introduce unacceptable
  overhead (I/O latency, external services, database setup complexity).
- Test behavior through public interfaces, not implementation details.

**End-to-End Tests**:
- E2E tests MUST execute the real CLI against example project directories.
- Use fixtures in `tests/fixtures/` representing realistic repository structures.
- E2E tests validate the complete user workflow, not individual components.

**Test Organization**:
- Unit tests in `tests/unit/`
- Integration/E2E tests in `tests/integration/` (marked with `@pytest.mark.integration`)

**Rationale**: Classical testing with real dependencies catches integration
issues that mocks hide. E2E tests ensure the tool works as users will actually
use it.

### IV. Clean Modern Python

Write clean, modern Python code following current best practices:

- **Python 3.12+**: Use modern language features (type hints, pattern matching,
  dataclasses, etc.).
- **Full type hints**: All public functions, methods, and module-level variables
  MUST have type annotations.
- **`from __future__ import annotations`**: Use for forward reference support.
- **2-space indentation**: Configured via ruff.
- **Imports**: Place type-only imports in `TYPE_CHECKING` blocks.
- **Structured logging**: Use `structlog` for all logging.
- **Settings**: Use pydantic-settings for configuration.
- **CLI output**: Logs to stderr via `rich.Console(stderr=True)`, data to stdout.

**Rationale**: Type hints improve maintainability and catch errors early.
Consistent style reduces cognitive load. Modern patterns leverage language
improvements.

### V. Makefile-Driven Workflows

All common developer workflows MUST be represented in the root Makefile:

- **Single entry point**: Developers should not need to remember complex
  commands or tool-specific invocations.
- **Required targets**: `make help`, `make quality`, `make test`, `make test-unit`,
  `make test-int`, `make format`, `make presubmit`.
- **Self-documenting**: `make help` MUST list all available targets with
  descriptions.
- **Composable**: Complex workflows should compose simpler targets.

**Completion Gate**: Code is not considered complete until `make presubmit`
passes.

**Rationale**: A consistent, discoverable interface for development tasks
reduces onboarding friction and prevents "works on my machine" issues.

### VI. Environment as Code

All environmental dependencies MUST be declared and reproducible:

**Dev Container**:
- System-level dependencies MUST be added to `.devcontainer/Dockerfile` or
  `devcontainer.json` features.
- Never install system packages directly in a running container—update the
  configuration instead.

**Python Dependencies**:
- All Python dependencies MUST be managed via `uv`.
- Use `uv sync` for installation, `uv add` for adding dependencies.
- Never use `pip install` directly.

**Rationale**: Reproducible environments eliminate setup friction and ensure
all developers and CI systems work with identical tooling.

## Development Workflow

### Standard Development Cycle

1. **Understand**: Review existing code and architecture before making changes.
2. **Question**: Ask whether the existing approach is still appropriate.
3. **Simplify**: Look for opportunities to reduce complexity.
4. **Implement**: Write clean, tested code.
5. **Verify**: Run `make presubmit` before considering work complete.

### Adding Dependencies

- **Python packages**: `uv add <package>` (dev dependencies: `uv add --dev <package>`)
- **System tools**: Update `.devcontainer/Dockerfile` or `devcontainer.json`
- **Never**: `pip install`, `apt install` in running container, or manual setup steps

## Quality Gates

### Pre-commit Checklist

Before code is considered complete, verify:

- [ ] `make presubmit` passes (linting, formatting, type checking, tests)
- [ ] New functionality has appropriate test coverage (unit and/or e2e)
- [ ] No unnecessary complexity introduced
- [ ] Existing patterns followed or explicitly improved
- [ ] Type hints present on all public interfaces

### Code Review Focus Areas

- Does this change align with first principles?
- Could this be simpler?
- Are tests testing behavior, not implementation?
- Is the change consistent with existing patterns (or improving them)?

## Governance

This constitution establishes the foundational principles for repo-map
development. All code changes, architectural decisions, and process
modifications MUST align with these principles.

**Amendment Process**:
- Amendments require documented rationale explaining why the change improves
  the project.
- Version increments follow semantic versioning:
  - MAJOR: Principle removal or fundamental redefinition
  - MINOR: New principle or significant expansion
  - PATCH: Clarifications and wording improvements

**Compliance**:
- All contributions are expected to follow this constitution.
- When principles conflict, resolve by applying First Principles Design
  (Principle I) to determine which approach better serves the project's goals.

**Guidance Reference**: See `.github/copilot-instructions.md` for runtime
development guidance and code conventions.

**Version**: 1.0.0 | **Ratified**: 2025-12-31 | **Last Amended**: 2025-12-31
