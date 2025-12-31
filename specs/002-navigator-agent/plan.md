# Implementation Plan: Navigator Agent (Layer 2)

**Branch**: `002-navigator-agent` | **Date**: December 31, 2025 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-navigator-agent/spec.md`

## Summary

Build "Layer 2: The Navigator" - an autonomous AI agent that orchestrates the repo-map CLI through iterative refinement cycles. The agent uses Google Agent Development Kit (ADK) for Python with a single `LlmAgent` running in an `InMemoryRunner`. It implements a State-over-History pattern using strongly-typed Pydantic models stored in `session.state`, avoiding conversation history bloat. The system supports both autonomous (budget-capped) and interactive (step-by-step) execution modes.

**Technical approach**:
1. Pydantic-typed `NavigatorState` model stored in `session.state`
2. Custom `InstructionProvider` for dynamic context injection (goal + current map + decision log)
3. `BudgetEnforcementPlugin` for cost tracking via `before_model_callback`/`after_model_callback`
4. Two tools: `update_flight_plan` (runs CLI) and `finalize_context` (ends exploration)
5. Artifact storage for current map output via `ArtifactService`

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: google-adk (Agent Development Kit), pydantic (state models), pyyaml (config serialization)  
**Storage**: In-memory session state + ArtifactService for map outputs  
**Testing**: pytest with classical style; mock LLM responses for unit tests, real CLI for integration  
**Target Platform**: CLI tool, cross-platform  
**Project Type**: Single project (extends existing structure)  
**Performance Goals**: Complete exploration in <5 minutes for repos up to 10k files (SC-001)  
**Constraints**: Cost budget adherence with zero overruns (SC-003), token budget ±5% (SC-002)  
**Scale/Scope**: Context maps up to 50k tokens, exploration budgets up to $10

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. First Principles Design | Builds on Layer 1 FlightPlan; reuses existing CLI pipeline; aligns with goal of intelligent context generation | ✅ |
| II. Simplicity | Single agent with two tools; state-over-history avoids complex prompt chaining; ADK handles orchestration | ✅ |
| III. Testing Strategy | Unit tests for state models/plugins; e2e tests with mock LLM + real CLI against fixture repos | ✅ |
| IV. Clean Modern Python | Type hints, Pydantic models, async patterns, structlog logging; 2-space indent | ✅ |
| V. Makefile Workflows | No new targets needed; existing `make test`, `make quality` cover new code | ✅ |
| VI. Environment as Code | `uv add google-adk`; no manual setup | ✅ |

## Project Structure

### Documentation (this feature)

```text
specs/002-navigator-agent/
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
│   └── app.py              # MODIFY: Add `navigate` command
├── core/
│   ├── __init__.py
│   ├── flight_plan.py      # (existing - reuse FlightPlan model)
│   ├── cost.py             # (existing - reuse token estimation)
│   └── verbosity.py        # (existing - reuse VerbosityLevel)
├── navigator/              # NEW: Navigator agent module
│   ├── __init__.py
│   ├── state.py            # NEW: NavigatorState Pydantic models
│   ├── agent.py            # NEW: LlmAgent definition + InstructionProvider
│   ├── tools.py            # NEW: update_flight_plan, finalize_context tools
│   ├── plugin.py           # NEW: BudgetEnforcementPlugin
│   ├── runner.py           # NEW: Runner setup + execution modes
│   └── pricing.py          # NEW: Model pricing configuration
├── mapper.py               # (existing - called by update_flight_plan tool)
├── settings.py             # MODIFY: Add navigator-specific settings
└── logging_config.py       # (existing)

tests/
├── conftest.py             # MODIFY: Add navigator fixtures
├── fixtures/
│   ├── sample-repo/        # (existing - reuse for navigator e2e)
│   └── flight-plans/       # (existing - reuse sample configs)
├── integration/
│   ├── __init__.py
│   ├── test_context_engine.py  # (existing)
│   └── test_navigator.py       # NEW: Navigator e2e tests
└── unit/
    ├── __init__.py
    ├── test_navigator_state.py     # NEW: State model tests
    ├── test_navigator_plugin.py    # NEW: Budget plugin tests
    ├── test_navigator_tools.py     # NEW: Tool function tests
    └── test_navigator_runner.py    # NEW: Runner/mode tests
```

**Structure Decision**: Navigator functionality isolated in `repo_map/navigator/` module. Reuses existing `core/` modules (FlightPlan, cost estimation, verbosity). Clear separation between agent logic and CLI integration.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |

---

## Phase 0: Research

### Research Tasks

1. **Google ADK State Management** - How to properly store/retrieve Pydantic models in session.state
2. **ADK Plugin Callbacks** - Exact signatures for before_model_callback/after_model_callback and how to intercept/terminate
3. **ADK Artifact Service** - In-memory artifact storage patterns for map outputs
4. **LLM Response Usage Metadata** - How to extract token counts from LlmResponse for cost calculation
5. **Model Pricing Data** - Gemini and other model pricing for input/output tokens
6. **Interactive Execution Pattern** - How to yield control back to user mid-agent-loop

### Findings

See [research.md](research.md) for detailed findings.

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) for entity definitions.

### API Contracts

See [contracts/](contracts/) for:
- `navigator-state-schema.md` - NavigatorState Pydantic model specification
- `cli-navigate-interface.md` - CLI `navigate` command specification
- `turn-report-schema.md` - Turn Report output format

### Quickstart

See [quickstart.md](quickstart.md) for implementation sequence.

---

## Post-Design Constitution Re-Check

| Principle | Re-Check After Design | Status |
|-----------|----------------------|--------|
| I. First Principles Design | Reuses FlightPlan from Layer 1; ADK provides proven orchestration | ✅ |
| II. Simplicity | Single agent, two tools, one plugin; no custom orchestration code | ✅ |
| III. Testing Strategy | Mock LLM for unit tests; real CLI + fixture repos for e2e | ✅ |
| IV. Clean Modern Python | All models typed; async patterns; structlog | ✅ |
| V. Makefile Workflows | No changes needed | ✅ |
| VI. Environment as Code | Single `uv add google-adk` | ✅ |
