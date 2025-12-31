# Tasks: Context Engine - Multi-Resolution Rendering

**Input**: Design documents from `/specs/001-context-engine/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US7)
- File paths are relative to repository root

---

## Phase 1: Setup

**Purpose**: Project initialization and dependencies

- [ ] T001 Add PyYAML dependency with `uv add pyyaml`
- [ ] T002 [P] Create test fixtures directory structure in tests/fixtures/sample-repo/
- [ ] T003 [P] Create test fixtures directory structure in tests/fixtures/flight-plans/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required by ALL user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create VerbosityLevel enum in repo_map/core/verbosity.py
- [ ] T005 Create FlightPlan Pydantic models in repo_map/core/flight_plan.py
- [ ] T006 [P] Implement YAML loading with validation in repo_map/core/flight_plan.py
- [ ] T007 [P] Create cost estimation utilities in repo_map/core/cost.py
- [ ] T008 Add --config flag to CLI in repo_map/cli/app.py
- [ ] T009 Wire FlightPlan loading to mapper in repo_map/mapper.py
- [ ] T010 [P] Unit tests for FlightPlan validation in tests/unit/test_flight_plan.py
- [ ] T011 [P] Unit tests for cost estimation in tests/unit/test_cost.py

**Checkpoint**: Foundation ready - FlightPlan loads and validates, cost estimation works

---

## Phase 3: User Story 1 - Basic Multi-Resolution Rendering (Priority: P1) 🎯 MVP

**Goal**: Request different verbosity levels (0-4) for different parts of the codebase

**Independent Test**: Provide verbosity instructions via YAML, verify output matches requested detail levels

### Implementation for User Story 1

- [ ] T012 [US1] Create python-structure.scm (Level 2) in repo_map/core/queries/tree-sitter-language-pack/
- [ ] T013 [P] [US1] Create python-interface.scm (Level 3) in repo_map/core/queries/tree-sitter-language-pack/
- [ ] T014 [P] [US1] Create markdown-structure.scm (Level 2) in repo_map/core/queries/tree-sitter-language-pack/
- [ ] T015 [P] [US1] Create markdown-interface.scm (Level 3) in repo_map/core/queries/tree-sitter-language-pack/
- [ ] T016 [US1] Add verbosity parameter to get_tags_from_code() in repo_map/core/tags.py
- [ ] T017 [US1] Implement get_scm_fname(lang, level) for tiered query loading in repo_map/core/tags.py
- [ ] T018 [US1] Create ContextRenderer class in repo_map/core/renderer.py
- [ ] T019 [US1] Implement verbosity rule matching (glob patterns) in repo_map/core/renderer.py
- [ ] T020 [US1] Implement render_file_at_level() for each verbosity level in repo_map/core/renderer.py
- [ ] T021 [US1] Wire ContextRenderer to mapper pipeline in repo_map/mapper.py
- [ ] T022 [P] [US1] Unit tests for tiered query loading in tests/unit/test_tags_verbosity.py
- [ ] T023 [P] [US1] Unit tests for verbosity rule matching in tests/unit/test_renderer.py
- [ ] T024 [US1] Integration test: verbosity levels in tests/integration/test_context_engine.py

**Checkpoint**: Multi-resolution rendering works - can request L1-L4 for different file patterns

---

## Phase 4: User Story 2 - Cost Prediction for Budget Planning (Priority: P1)

**Goal**: Know token cost of each file at every verbosity level for budget planning

**Independent Test**: Request cost metadata for files, verify accurate token counts at all 5 levels

### Implementation for User Story 2

- [ ] T025 [US2] Implement calculate_file_costs() returning costs for all levels in repo_map/core/cost.py
- [ ] T026 [US2] Add FileNode dataclass with costs attribute in repo_map/core/renderer.py
- [ ] T027 [US2] Implement cost annotation header format in repo_map/core/renderer.py
- [ ] T028 [US2] Add --show-costs flag to CLI in repo_map/cli/app.py
- [ ] T029 [US2] Implement budget tracking in ContextRenderer.render() in repo_map/core/renderer.py
- [ ] T030 [US2] Implement budget warning (soft mode) in repo_map/core/renderer.py
- [ ] T031 [US2] Add --strict flag for budget enforcement in repo_map/cli/app.py
- [ ] T032 [US2] Implement strict mode error with detailed breakdown in repo_map/core/renderer.py
- [ ] T033 [P] [US2] Unit tests for cost calculation accuracy in tests/unit/test_cost.py
- [ ] T034 [US2] Integration test: cost annotations and budget warning in tests/integration/test_context_engine.py

**Checkpoint**: Cost prediction works - Navigator can plan context windows mathematically

---

## Phase 5: User Story 3 - Markdown Documentation Rendering (Priority: P1)

**Goal**: Multi-resolution control for markdown files (headings, summaries, full content)

**Independent Test**: Provide markdown files, verify correct rendering at each verbosity level

### Implementation for User Story 3

- [ ] T035 [US3] Enhance markdown-tags.scm to capture heading hierarchy in repo_map/core/queries/tree-sitter-language-pack/
- [ ] T036 [US3] Implement Section dataclass for markdown sections in repo_map/core/renderer.py
- [ ] T037 [US3] Extract section boundaries from markdown AST in repo_map/core/tags.py
- [ ] T038 [US3] Implement Level 2 rendering (headings only) for markdown in repo_map/core/renderer.py
- [ ] T039 [US3] Implement Level 3 rendering (headings + first paragraph) for markdown in repo_map/core/renderer.py
- [ ] T040 [P] [US3] Unit tests for markdown section extraction in tests/unit/test_markdown_sections.py
- [ ] T041 [US3] Integration test: markdown verbosity levels in tests/integration/test_context_engine.py

**Checkpoint**: Markdown rendering works - docs have same multi-resolution control as code

---

## Phase 6: User Story 4 - Intra-File Section Control (Priority: P2)

**Goal**: Different verbosity levels for different sections within the same file

**Independent Test**: Specify section-level verbosity, verify only requested sections appear

### Implementation for User Story 4

- [ ] T042 [US4] Implement section-level verbosity rules in FlightPlan in repo_map/core/flight_plan.py
- [ ] T043 [US4] Implement match_section_level() using fnmatch in repo_map/core/renderer.py
- [ ] T044 [US4] Extract code sections (class/function boundaries) in repo_map/core/tags.py
- [ ] T045 [US4] Implement per-section rendering in ContextRenderer in repo_map/core/renderer.py
- [ ] T046 [US4] Calculate section-level costs in repo_map/core/cost.py
- [ ] T047 [P] [US4] Unit tests for section verbosity matching in tests/unit/test_renderer.py
- [ ] T048 [US4] Integration test: intra-file section control in tests/integration/test_context_engine.py

**Checkpoint**: Intra-file control works - can zoom into specific sections within files

---

## Phase 7: User Story 5 - Symbol Boosting for Focused Analysis (Priority: P2)

**Goal**: Boost specific symbols/paths in ranking algorithm

**Independent Test**: Add focus symbols, verify they rank higher than without boosting

### Implementation for User Story 5

- [ ] T049 [US5] Implement _build_personalization() in repo_map/core/repomap.py
- [ ] T050 [US5] Add focus_boosts parameter to _get_ranked_tags() in repo_map/core/repomap.py
- [ ] T051 [US5] Integrate personalization vector with nx.pagerank() in repo_map/core/repomap.py
- [ ] T052 [US5] Implement symbol name to file path resolution in repo_map/core/repomap.py
- [ ] T053 [US5] Add --focus CLI flag for quick boosting in repo_map/cli/app.py
- [ ] T054 [US5] Wire Focus config from FlightPlan to RepoMap in repo_map/mapper.py
- [ ] T055 [P] [US5] Unit tests for personalization vector building in tests/unit/test_boosting.py
- [ ] T056 [US5] Integration test: focus boosting effects in tests/integration/test_context_engine.py

**Checkpoint**: Focus boosting works - can steer PageRank to prioritize specific areas

---

## Phase 8: User Story 6 - YAML Configuration for Complex Queries (Priority: P2)

**Goal**: Express complex rendering instructions in YAML flight plan

**Independent Test**: Provide complex YAML config, verify all settings are respected

### Implementation for User Story 6

- [ ] T057 [US6] Add -v pattern:level shorthand parsing in repo_map/cli/app.py
- [ ] T058 [US6] Implement CLI override of FlightPlan values in repo_map/mapper.py
- [ ] T059 [US6] Add detailed YAML validation error messages in repo_map/core/flight_plan.py
- [ ] T060 [US6] Create sample flight-plan files in tests/fixtures/flight-plans/
- [ ] T061 [P] [US6] Unit tests for CLI/YAML precedence in tests/unit/test_flight_plan.py
- [ ] T062 [US6] Integration test: complex YAML configurations in tests/integration/test_context_engine.py

**Checkpoint**: YAML flight plans work - Navigator can express sophisticated queries

---

## Phase 9: User Story 7 - Custom Tree-sitter Queries (Priority: P3)

**Goal**: Inject custom tree-sitter queries for domain-specific patterns

**Independent Test**: Provide custom query, verify only matching AST nodes extracted

### Implementation for User Story 7

- [ ] T063 [US7] Add custom_queries support to FlightPlan schema in repo_map/core/flight_plan.py
- [ ] T064 [US7] Implement custom query loading in tags.py in repo_map/core/tags.py
- [ ] T065 [US7] Validate .scm query syntax on load in repo_map/core/flight_plan.py
- [ ] T066 [US7] Wire custom queries to tag extraction pipeline in repo_map/mapper.py
- [ ] T067 [P] [US7] Unit tests for custom query validation in tests/unit/test_flight_plan.py
- [ ] T068 [US7] Integration test: custom query extraction in tests/integration/test_context_engine.py

**Checkpoint**: Custom queries work - can extract domain-specific patterns

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, edge cases, and final validation

- [ ] T069 [P] Create comprehensive sample-repo fixture with src/, docs/, README.md in tests/fixtures/sample-repo/
- [ ] T070 [P] Update CLI help text with new options in repo_map/cli/app.py
- [ ] T071 [P] Add example flight plans to documentation
- [ ] T072 Handle binary files (exclude, Level 1 path only) in repo_map/core/renderer.py
- [ ] T073 Handle files without AST parser (fallback to full text) in repo_map/core/tags.py
- [ ] T074 Edge case tests (empty dirs, malformed markdown) in tests/integration/test_edge_cases.py
- [ ] T075 Performance test with large repository (10k files, <30s) in tests/integration/test_performance.py (SC-003)
- [ ] T076 Verify deterministic output (identical inputs = identical outputs) in tests/integration/test_determinism.py (SC-008)
- [ ] T077 [P] Validate cost estimation accuracy <10% error in tests/integration/test_cost_accuracy.py (SC-002)
- [ ] T078 [P] Validate intra-file section control achieves 50%+ token reduction in tests/integration/test_section_efficiency.py (SC-005)
- [ ] T079 [P] Validate focus boosting moves items from top 20% to top 5% in tests/integration/test_boost_effectiveness.py (SC-006)
- [ ] T080 Run `make presubmit` and fix any issues

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ────────────────────────┐
                                        ▼
Phase 2 (Foundational) ─────────────────┤
                                        │
    ┌───────────────────────────────────┴───────────────────────────────────┐
    ▼                   ▼                   ▼                               │
Phase 3 (US1)      Phase 4 (US2)       Phase 5 (US3)                       │
Multi-Resolution   Cost Prediction     Markdown Rendering                  │
    │                   │                   │                               │
    └───────────────────┴───────────────────┘                               │
                        │                                                   │
    ┌───────────────────┴───────────────────┐                               │
    ▼                   ▼                   ▼                               │
Phase 6 (US4)      Phase 7 (US5)       Phase 8 (US6)                       │
Intra-File         Focus Boosting      YAML Config                         │
                                                                            │
                        │                                                   │
                        ▼                                                   │
                   Phase 9 (US7)                                            │
                   Custom Queries                                           │
                        │                                                   │
                        ▼                                                   │
                   Phase 10 (Polish) ◄──────────────────────────────────────┘
```

### User Story Dependencies

| Story | Can Start After | Dependencies on Other Stories |
|-------|-----------------|-------------------------------|
| US1 (P1) | Phase 2 | None - core foundation |
| US2 (P1) | Phase 2 | None - can parallel with US1 |
| US3 (P1) | Phase 2 | None - can parallel with US1, US2 |
| US4 (P2) | Phase 3 (US1) | Needs multi-resolution rendering |
| US5 (P2) | Phase 2 | None - independent of rendering |
| US6 (P2) | Phase 3 (US1) | Needs rendering to test configs |
| US7 (P3) | Phase 3 (US1) | Needs tag extraction infrastructure |

### Within Each User Story

1. Query files (.scm) before tags.py modifications
2. Core logic before CLI integration
3. Implementation before integration tests
4. Commit after each logical group

### Parallel Opportunities per Phase

**Phase 2** (Foundational):
```
T005, T006 ─── FlightPlan ───┐
T007 ────────── Cost ────────┼── All can start in parallel
T010, T011 ─── Tests ────────┘
```

**Phase 3** (US1 - Multi-Resolution):
```
T012 ─── python-structure.scm ────┐
T013 ─── python-interface.scm ────┼── All .scm files in parallel
T014 ─── markdown-structure.scm ──┤
T015 ─── markdown-interface.scm ──┘
         │
         ▼
T016, T017 ─── tags.py modifications ──► T018, T019, T020 ─── renderer.py
```

**Phase 4-5** (US2, US3): Can run in parallel with separate developers

---

## Implementation Strategy

### MVP First (User Stories 1-3)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T011)
3. Complete Phase 3: US1 Multi-Resolution (T012-T024)
4. **VALIDATE**: Test verbosity levels work correctly
5. Complete Phase 4: US2 Cost Prediction (T025-T034)
6. Complete Phase 5: US3 Markdown (T035-T041)
7. **STOP and DEMO**: MVP complete - core Engine functionality

### Incremental Delivery

After MVP:
- Add US4 (Intra-File) → Enables precise section control
- Add US5 (Focus Boosting) → Enables Navigator steering
- Add US6 (YAML Config) → Full flight plan support
- Add US7 (Custom Queries) → Advanced use cases

### Estimated Task Counts

| Phase | Tasks | Parallelizable |
|-------|-------|----------------|
| Setup | 3 | 2 |
| Foundational | 8 | 4 |
| US1 | 13 | 4 |
| US2 | 10 | 1 |
| US3 | 7 | 1 |
| US4 | 7 | 1 |
| US5 | 8 | 1 |
| US6 | 6 | 1 |
| US7 | 6 | 1 |
| Polish | 12 | 6 |
| **Total** | **80** | **22** |

---

## Notes

- Tests are included for each story (unit + integration)
- [P] marks tasks that can run in parallel within their phase
- Each user story should be independently testable at its checkpoint
- Commit after each task or logical group
- Run `make quality` frequently during implementation
- Run `make presubmit` before completing any phase
