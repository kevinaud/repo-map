# Tasks: Navigator Agent (Layer 2)

**Input**: Design documents from `/specs/002-navigator-agent/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US4)
- File paths are relative to repository root

## User Story Mapping

| Story | Title | Priority | Description |
|-------|-------|----------|-------------|
| US1 | Autonomous Context Discovery | P1 | Core autonomous exploration loop |
| US2 | Interactive Step-by-Step Exploration | P2 | Interactive mode with Turn Reports |
| US3 | Reproducible Context Generation | P3 | Flight Plan YAML export/import |
| US4 | Budget-Aware Termination | P2 | Cost tracking and budget enforcement |

---

## Phase 1: Setup

**Purpose**: Project initialization, dependencies, and basic module structure

- [X] T001 Add google-adk dependency via `uv add google-adk`
- [X] T002 [P] Create repo_map/navigator/__init__.py with module docstring
- [X] T003 [P] Add navigator settings to repo_map/settings.py (NAVIGATOR_MODEL, NAVIGATOR_DEFAULT_TOKEN_BUDGET, NAVIGATOR_DEFAULT_COST_LIMIT_USD env vars)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core state models and infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### State Models

- [X] T004 [P] Create ModelPricingRates Pydantic model in repo_map/navigator/pricing.py with preset configs (gemini-2.0-flash, gemini-1.5-pro)
- [X] T005 [P] Create BudgetConfig Pydantic model in repo_map/navigator/state.py with max_spend_usd, current_spend_usd, model_pricing_rates
- [X] T006 [P] Create DecisionLogEntry Pydantic model in repo_map/navigator/state.py with step, action, reasoning, config_diff, timestamp
- [X] T007 [P] Create MapMetadata Pydantic model in repo_map/navigator/state.py with total_tokens, file_count, focus_areas, excluded_count, budget_utilization
- [X] T008 Create NavigatorState root Pydantic model in repo_map/navigator/state.py with all nested models and validators
- [X] T009 [P] Create TurnReport dataclass in repo_map/navigator/state.py for interactive mode output
- [X] T010 [P] Create NavigatorOutput dataclass in repo_map/navigator/state.py for final exploration output

### State Helpers

- [X] T011 Implement get_navigator_state(context) helper in repo_map/navigator/state.py for deserializing state from session.state
- [X] T012 Implement update_navigator_state(context, state) helper in repo_map/navigator/state.py for persisting state to session.state

### Pricing Utilities

- [X] T013 [P] Implement calculate_cost(input_tokens, output_tokens, pricing) function in repo_map/navigator/pricing.py
- [X] T014 [P] Implement get_pricing_for_model(model_name) function in repo_map/navigator/pricing.py

### Unit Tests for Foundation

- [X] T015 [P] Create tests/unit/test_navigator_state.py with tests for NavigatorState model validation
- [X] T016 [P] Create tests/unit/test_navigator_pricing.py with tests for cost calculation accuracy

**Checkpoint**: Foundation ready - all state models validated, user story implementation can begin

---

## Phase 3: User Story 1 - Autonomous Context Discovery (Priority: P1) 🎯 MVP

**Goal**: Autonomous exploration loop that discovers relevant context without manual intervention

**Independent Test**: Run `repo-map navigate . -g "understand auth"` and verify it produces focused context map within token budget

### Budget Plugin (US1 + US4 shared)

- [X] T017 [US1] Create BudgetEnforcementPlugin class extending BasePlugin in repo_map/navigator/plugin.py
- [X] T018 [US1] Implement after_model_callback in plugin.py to track token usage from LlmResponse.usage_metadata
- [X] T019 [US1] Add unit tests for BudgetEnforcementPlugin in tests/unit/test_navigator_plugin.py

### Tools

- [X] T020 [US1] Implement update_flight_plan tool function in repo_map/navigator/tools.py with reasoning, updates parameters
- [X] T021 [US1] Add subprocess execution of repo-map CLI in update_flight_plan tool
- [X] T022 [US1] Add artifact storage for map output via context.save_artifact in update_flight_plan tool
- [X] T023 [US1] Implement parse_map_header helper in repo_map/navigator/tools.py to extract MapMetadata from CLI output
- [X] T024 [US1] Implement finalize_context tool function in repo_map/navigator/tools.py with summary parameter
- [X] T025 [US1] Create FunctionTool wrappers for both tools in repo_map/navigator/tools.py
- [X] T026 [P] [US1] Add unit tests for tools in tests/unit/test_navigator_tools.py with mock subprocess

### Agent & InstructionProvider

- [X] T027 [US1] Implement navigator_instruction_provider async function in repo_map/navigator/agent.py
- [X] T028 [US1] Add format_decision_log helper in repo_map/navigator/agent.py for prompt construction
- [X] T029 [US1] Create LlmAgent definition in repo_map/navigator/agent.py with tools and instruction provider
- [X] T030 [P] [US1] Add unit tests for instruction generation in tests/unit/test_navigator_agent.py

### Runner - Autonomous Mode

- [X] T031 [US1] Create create_navigator_runner factory function in repo_map/navigator/runner.py
- [X] T032 [US1] Configure InMemorySessionService and InMemoryArtifactService in runner.py
- [X] T033 [US1] Implement initialize_session function in runner.py to set up initial NavigatorState
- [X] T034 [US1] Implement run_autonomous async function in repo_map/navigator/runner.py for continuous loop execution
- [X] T035 [US1] Add progress event yielding in run_autonomous for status updates
- [X] T036 [P] [US1] Add unit tests for runner in tests/unit/test_navigator_runner.py

### CLI Integration - Basic

- [X] T037 [US1] Add navigate subcommand to repo_map/cli/app.py with path and --goal arguments
- [X] T038 [US1] Add --tokens and --model options to navigate command
- [X] T039 [US1] Wire navigate command to run_autonomous execution
- [X] T040 [US1] Implement progress display using Rich console in navigate command
- [X] T041 [US1] Output NavigatorOutput (context_string, flight_plan_yaml, reasoning_summary) on completion

### Integration Test

- [X] T042 [US1] Create tests/integration/test_navigator.py with e2e test using fixture sample-repo and mock LLM

**Checkpoint**: User Story 1 (Autonomous Mode) complete - can discover and generate context autonomously

---

## Phase 4: User Story 4 - Budget-Aware Termination (Priority: P2)

**Goal**: Cost tracking with automatic termination when budget would be exceeded

**Independent Test**: Set --cost-limit 0.01 and verify exploration stops gracefully with partial results

### Budget Enforcement

- [ ] T043 [US4] Implement before_model_callback in BudgetEnforcementPlugin to check projected cost
- [ ] T044 [US4] Implement mock LlmResponse generation for budget exceeded termination
- [ ] T045 [US4] Update run_autonomous to handle budget termination gracefully and output partial results
- [ ] T046 [P] [US4] Add budget enforcement tests in tests/unit/test_navigator_plugin.py for edge cases

### CLI Integration

- [ ] T047 [US4] Add --cost-limit option to navigate command in repo_map/cli/app.py
- [ ] T048 [US4] Display budget status (spent/remaining) in progress output
- [ ] T049 [US4] Set exit code 0 when budget exhausted with partial results, exit code 1 only when zero useful output

### Integration Test

- [ ] T050 [US4] Add budget termination e2e test in tests/integration/test_navigator.py

**Checkpoint**: User Story 4 complete - budget enforcement prevents cost overruns

---

## Phase 5: User Story 2 - Interactive Step-by-Step Exploration (Priority: P2)

**Goal**: Interactive mode with Turn Reports and user approval between iterations

**Independent Test**: Run `repo-map navigate . -g "auth" --interactive` and verify Turn Report displays, waits for input

### Turn Report Generation

- [ ] T051 [US2] Implement build_turn_report function in repo_map/navigator/runner.py
- [ ] T052 [US2] Add render_turn_report function in repo_map/navigator/runner.py for Rich console output

### Interactive Runner

- [ ] T053 [US2] Implement run_interactive_step async function in repo_map/navigator/runner.py
- [ ] T054 [US2] Add interactive_pause flag handling in update_flight_plan tool
- [ ] T055 [US2] Implement user input handling (y/n/feedback) in runner.py
- [ ] T056 [P] [US2] Add unit tests for interactive execution in tests/unit/test_navigator_runner.py

### CLI Integration

- [ ] T057 [US2] Add --interactive flag to navigate command in repo_map/cli/app.py
- [ ] T058 [US2] Implement interactive loop in navigate command with Rich prompt
- [ ] T059 [US2] Add --verbose flag for detailed Turn Report output
- [ ] T060 [US2] Set exit code 5 when user cancels interactive mode

### Integration Test

- [ ] T061 [US2] Add interactive mode e2e test in tests/integration/test_navigator.py with simulated input

**Checkpoint**: User Story 2 complete - interactive exploration with user control

---

## Phase 6: User Story 3 - Reproducible Context Generation (Priority: P3)

**Goal**: Export Flight Plan YAML for deterministic regeneration without exploration cost

**Independent Test**: Save Flight Plan from run, use it to regenerate identical context

### Flight Plan Export

- [ ] T062 [US3] Implement format_flight_plan_with_metadata in repo_map/navigator/runner.py to add comments
- [ ] T063 [US3] Add flight_plan_yaml generation to NavigatorOutput construction

### CLI Integration

- [ ] T064 [US3] Add --flight-plan (-f) option to navigate command for YAML export path
- [ ] T065 [US3] Add --output (-o) option to navigate command for context file output
- [ ] T066 [US3] Add --copy (-c) flag to copy context to clipboard
- [ ] T067 [P] [US3] Implement Flight Plan file writing with metadata header

### Regeneration Path

- [ ] T068 [US3] Verify existing generate command accepts Flight Plan YAML from Navigator output
- [ ] T069 [P] [US3] Add documentation comments in output Flight Plan explaining regeneration

### Integration Test

- [ ] T070 [US3] Add reproducibility e2e test in tests/integration/test_navigator.py comparing regenerated output

**Checkpoint**: User Story 3 complete - Flight Plans enable reproducible context generation

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Quality improvements across all user stories

### Error Handling

- [ ] T071 [P] Add graceful error handling for missing GOOGLE_API_KEY in runner.py
- [ ] T072 [P] Add repository not found validation with exit code 3 in navigate command
- [ ] T073 [P] Add agent error handling with exit code 4 in navigate command

### Output Improvements

- [ ] T074 [P] Add --quiet flag support to suppress progress output
- [ ] T075 [P] Add --max-iterations option to limit exploration cycles
- [ ] T076 [P] Improve reasoning summary formatting in final output

### Test Fixtures

- [ ] T077 [P] Add navigator-specific mock LLM responses to tests/conftest.py
- [ ] T078 [P] Add navigator fixture for pre-initialized runner in tests/conftest.py

### Documentation

- [ ] T079 [P] Add docstrings to all public functions in navigator module
- [ ] T080 Run make quality to verify type hints and linting pass
- [ ] T081 Run make test to verify all unit and integration tests pass

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← BLOCKS all user stories
    ↓
    ├── Phase 3 (US1: Autonomous) ← MVP, start here
    │       ↓
    ├── Phase 4 (US4: Budget) ← Extends US1 plugin
    │       ↓
    ├── Phase 5 (US2: Interactive) ← Builds on US1 runner
    │       ↓
    └── Phase 6 (US3: Reproducible) ← Uses US1 output format
            ↓
        Phase 7 (Polish)
```

### User Story Independence

- **US1 (Autonomous)**: Core MVP - all other stories depend on this foundation
- **US4 (Budget)**: Extends US1's plugin - can be done immediately after US1
- **US2 (Interactive)**: Adds interactive mode to US1 runner - parallel with US4
- **US3 (Reproducible)**: Adds export options - can run in parallel with US2/US4

### Within Each Phase

- Models before services/helpers
- Helpers before tools
- Tools before agent
- Agent before runner
- Runner before CLI
- CLI before integration tests

---

## Parallel Execution Examples

### Phase 2 (Foundational) - Models in Parallel

```bash
# These 7 tasks can run simultaneously:
T004: ModelPricingRates in pricing.py
T005: BudgetConfig in state.py
T006: DecisionLogEntry in state.py
T007: MapMetadata in state.py
T009: TurnReport in state.py
T010: NavigatorOutput in state.py
T013: calculate_cost in pricing.py
T014: get_pricing_for_model in pricing.py
```

### Phase 3 (US1) - Tests in Parallel

```bash
# After tools implemented, these tests can run simultaneously:
T026: test_navigator_tools.py
T030: test_navigator_agent.py
T036: test_navigator_runner.py
```

### Across User Stories - After US1 Complete

```bash
# Once US1 (Phase 3) complete, these can run in parallel:
Developer A: US4 (Budget enforcement) - T043-T050
Developer B: US2 (Interactive mode) - T051-T061
Developer C: US3 (Reproducibility) - T062-T070
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T016)
3. Complete Phase 3: User Story 1 (T017-T042)
4. **STOP AND VALIDATE**: Test autonomous exploration works
5. `repo-map navigate . -g "understand the auth system"` produces output

### Incremental Delivery

1. **MVP**: US1 → Basic autonomous exploration
2. **+Budget**: US4 → Cost control for production use
3. **+Interactive**: US2 → User control and transparency
4. **+Reproducible**: US3 → Flight Plan export for sharing/caching

### Estimated Effort

| Phase | Tasks | Estimated Hours |
|-------|-------|-----------------|
| Setup | 3 | 1 |
| Foundational | 13 | 4 |
| US1 (Autonomous) | 26 | 12 |
| US4 (Budget) | 8 | 4 |
| US2 (Interactive) | 11 | 6 |
| US3 (Reproducible) | 9 | 4 |
| Polish | 11 | 4 |
| **Total** | **81** | **~35 hours** |

---

## Notes

- All tasks follow `- [ ] [TaskID] [P?] [Story?] Description with file path` format
- [P] tasks operate on different files with no dependencies on incomplete tasks
- [Story] labels (US1-US4) map to user stories from spec.md
- Integration tests use `tests/fixtures/sample-repo/` and mock LLM responses
- Run `make quality` after each phase to catch issues early
- Commit after each logical group of tasks

