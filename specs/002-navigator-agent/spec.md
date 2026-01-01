# Feature Specification: Navigator Agent (Layer 2)

**Feature Branch**: `002-navigator-agent`  
**Created**: December 31, 2025  
**Status**: Draft  
**Input**: User description: "Develop Layer 2: The Navigator, an autonomous AI agent designed to operate the repo-map CLI to intelligently explore a codebase and construct the optimal context window for a specific user task."

## Overview

The Navigator Agent is an autonomous AI system that orchestrates the repo-map CLI through iterative refinement cycles. It starts with a broad "satellite view" of a repository and progressively zooms in on relevant areas while zooming out on irrelevant ones, constructing an optimal context window for a specific user task within defined token and cost constraints.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Autonomous Context Discovery (Priority: P1)

A developer wants to understand authentication logic in a large codebase. They provide a goal like "Refactor the auth middleware" and a token budget. The Navigator autonomously explores the repo, identifies auth-related files, increases detail on relevant modules, and delivers a focused context map without manual intervention.

**Why this priority**: This is the core value proposition—automated, intelligent context discovery that saves developers from manually navigating unfamiliar codebases.

**Independent Test**: Can be fully tested by providing a goal and budget, then verifying the output contains relevant auth-related code with appropriate detail levels while staying within token limits.

**Acceptance Scenarios**:

1. **Given** a repository path, a user goal "Refactor the auth middleware", and a 10,000 token budget, **When** the Navigator runs in autonomous mode, **Then** the final context map contains auth-related files with high verbosity and unrelated files excluded or minimized.
2. **Given** a cost budget of $1.00 and a complex exploration task, **When** the Navigator runs autonomously, **Then** execution stops before exceeding the budget and delivers the best context achieved so far.
3. **Given** an exploration that completes successfully, **When** the Navigator finishes, **Then** it outputs the final context string, a reproducible Flight Plan YAML, and a reasoning summary.

---

### User Story 2 - Interactive Step-by-Step Exploration (Priority: P2)

A developer wants fine-grained control over the exploration process. They run the Navigator in interactive mode, reviewing each iteration's changes, costs, and reasoning before approving the next step.

**Why this priority**: Provides transparency and control for users who want to understand the agent's decision-making or have strict cost constraints.

**Independent Test**: Can be tested by running one iteration, verifying the turn report displays correct cost/status information, and confirming the system waits for explicit approval.

**Acceptance Scenarios**:

1. **Given** interactive mode is selected, **When** the Navigator completes one iteration, **Then** it pauses and displays a Turn Report with: cost of last turn, total cost so far, current map size, and key focus areas.
2. **Given** a Turn Report is displayed, **When** the user provides approval, **Then** the Navigator proceeds to the next iteration.
3. **Given** a Turn Report is displayed, **When** the user declines or provides feedback, **Then** the Navigator stops or incorporates the feedback into the next iteration.

---

### User Story 3 - Reproducible Context Generation (Priority: P3)

A developer has previously explored a codebase and wants to regenerate the same context map without running the full exploration again. They use the saved Flight Plan YAML to deterministically reproduce the exact context.

**Why this priority**: Enables caching, sharing context configurations across team members, and consistent context generation for CI/CD pipelines.

**Independent Test**: Can be tested by taking a Flight Plan output from a previous run and using it to regenerate the exact same context map.

**Acceptance Scenarios**:

1. **Given** a Flight Plan YAML from a previous Navigator run, **When** the user runs context generation with this plan, **Then** the output is byte-identical to the original final context (excluding timestamp metadata in YAML comments).
2. **Given** a Flight Plan YAML, **When** the repository has not changed, **Then** regeneration produces byte-identical output with zero exploration cost.

---

### User Story 4 - Budget-Aware Termination (Priority: P2)

A developer sets a maximum cost limit to prevent runaway exploration costs. The system tracks accumulated costs and stops before exceeding the limit.

**Why this priority**: Essential for production use where uncontrolled API costs could be problematic.

**Independent Test**: Can be tested by setting a low budget and verifying the system stops at the correct threshold with partial results.

**Acceptance Scenarios**:

1. **Given** a cost budget of $0.50, **When** the next iteration would cost $0.15 and current spend is $0.40, **Then** the Navigator stops and delivers results before exceeding budget.
2. **Given** budget exhaustion occurs, **When** the Navigator stops, **Then** it clearly reports why it stopped and what was achieved within the budget.

---

### Edge Cases

- What happens when the token budget is too small to include even essential files? → System reports constraint conflict and delivers best-effort output with explanation.
- What happens when the repository has no files matching the user's goal? → System reports no relevant content found after initial scan.
- How does the system handle interrupted execution? → **Out of scope for MVP.** System outputs partial Flight Plan if possible; state persistence for resumption deferred to future iteration.
- What happens when cost estimation is inaccurate? → System uses conservative estimates and stops slightly before theoretical limit.
- How does the system handle conflicting goals (e.g., "include everything" with small token budget)? → System prioritizes based on relevance ranking and explains trade-offs in reasoning summary.

## Requirements *(mandatory)*

### Functional Requirements

#### Iterative Exploration Loop

- **FR-001**: System MUST implement a scan-analyze-refine-repeat loop for context discovery.
- **FR-002**: System MUST start with a low-fidelity "satellite view" showing mostly file paths and top-level structures.
- **FR-003**: System MUST compare the current view against the user's goal to identify relevant areas.
- **FR-004**: System MUST increase verbosity on files/directories deemed relevant to the goal.
- **FR-005**: System MUST decrease verbosity or exclude files/directories deemed irrelevant to the goal.
- **FR-006**: System MUST continue iteration until context is deemed sufficient OR constraints are hit.

#### Token Budget Management

- **FR-007**: System MUST continuously monitor the generated map size in tokens.
- **FR-008**: System MUST ensure final output does not exceed the user-defined Context Token Limit.
- **FR-009**: System MUST prioritize high-value information when approaching token limits.

#### State-over-History Context Strategy

- **FR-010**: System MUST NOT feed full history of previous map iterations into the agent's context.
- **FR-011**: System MUST construct a fresh, synthetic context for each iteration containing only:
  - The immutable user goal
  - The current map output (result of last CLI run)
  - A concise decision log of past configuration changes and reasoning
- **FR-012**: Decision log MUST be append-only and contain structured entries with step number, action taken, and reasoning.

#### Execution Modes

- **FR-013**: System MUST support Autonomous (Budget-Capped) mode where the agent runs loop-over-loop until completion or budget exhaustion.
- **FR-014**: System MUST support Interactive (Step-by-Step) mode where execution pauses after each iteration for user approval.
- **FR-015**: In Autonomous mode, system MUST automatically terminate if next projected step would exceed remaining budget.
- **FR-016**: In Autonomous mode, system MUST terminate when agent declares exploration complete.
- **FR-017**: In Interactive mode, system MUST present a Turn Report after each iteration.
- **FR-018**: Turn Report MUST include: cost of last turn, total cost incurred, current map size, and key focus areas.
- **FR-019**: In Interactive mode, system MUST wait for explicit user confirmation before proceeding.

#### Cost Tracking and Control

- **FR-020**: System MUST track accumulated input tokens used by the Navigator Agent.
- **FR-021**: System MUST track accumulated output tokens used by the Navigator Agent.
- **FR-022**: System MUST allow users to set a maximum spend limit in USD.
- **FR-023**: System MUST project the cost of the next iteration before executing it.

#### Output Deliverables

- **FR-024**: System MUST output the Final Context String (raw text of the optimized map).
- **FR-025**: System MUST output the Flight Plan (YAML configuration for reproducible generation).
- **FR-026**: System MUST output a Reasoning Summary explaining why specific areas were highlighted or excluded.
- **FR-027**: Flight Plan MUST be sufficient to deterministically regenerate the same context without re-running exploration.

### Key Entities

- **User Goal**: The immutable task description that drives relevance decisions (e.g., "Refactor the auth middleware"). Contains the goal text and optional constraints.
- **Context Map**: The current state of the generated repository map, including file paths, code structures, and their verbosity levels.
- **Decision Log**: An append-only record of exploration decisions containing step number, action type (`update_flight_plan` or `finalize_context`), target paths, and reasoning.
- **Turn Report**: A snapshot of iteration status including token costs, map metrics, and focus areas for user review.
- **Flight Plan**: A YAML configuration capturing the final verbosity settings per file/directory, enabling deterministic regeneration.
- **Budget State**: Tracks remaining token budget and remaining cost budget, along with accumulated usage.

## Assumptions

- The repo-map CLI already supports configurable verbosity levels per file/directory through Flight Plan YAML.
- Token counting/estimation is available through existing infrastructure.
- Cost calculation can be performed using model-specific pricing (input/output token rates).
- The agent will use an LLM API for decision-making during exploration (pricing varies by model).
- Users have access to appropriate LLM API credentials for the Navigator Agent to function.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can obtain a focused context map for a specific task in under 5 minutes for repositories up to 10,000 files.
- **SC-002**: Final context maps stay within 5% of the specified token budget.
- **SC-003**: Navigator agent cost stays within the user-specified budget limit with zero overruns.
- **SC-004**: Relevance accuracy: 80% of files included at high verbosity are confirmed relevant by users in feedback.
- **SC-005**: Reproducibility: Flight Plans regenerate identical context maps 100% of the time when repository state is unchanged.
- **SC-006**: Interactive mode users can make informed decisions based on Turn Reports, with all required information present.
- **SC-007**: Token efficiency: Navigator uses at least 50% fewer context tokens compared to feeding full iteration history.
