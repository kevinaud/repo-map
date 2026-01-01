# Data Model: Navigator Agent

**Date**: December 31, 2025  
**Feature**: 002-navigator-agent

---

## Entities

### NavigatorState (Root Model)

The root state model stored in `session.state["navigator"]`. Contains all information needed for each iteration.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| user_task | str | (required) | The user's goal/task description |
| repo_path | str | (required) | Absolute path to repository being explored |
| execution_mode | Literal["autonomous", "interactive"] | "autonomous" | Execution mode |
| budget_config | BudgetConfig | (required) | Cost budget configuration |
| flight_plan | FlightPlan | (required) | Current repo-map configuration (from Layer 1) |
| decision_log | list[DecisionLogEntry] | [] | History of decisions made |
| map_metadata | MapMetadata | (default) | Metadata about current map |
| interactive_pause | bool | False | Flag for interactive mode pause |
| exploration_complete | bool | False | Flag when exploration is finished |
| reasoning_summary | str | "" | Final reasoning (set by finalize_context) |

### BudgetConfig

Configuration and tracking for cost budget.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| max_spend_usd | float | 2.0 | Maximum allowed spend in USD |
| current_spend_usd | float | 0.0 | Amount spent so far |
| model_pricing_rates | ModelPricingRates | GEMINI_2_FLASH | Pricing configuration |

### ModelPricingRates

Token pricing rates for cost calculation.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| model_name | str | (required) | Model identifier (e.g., "gemini-2.0-flash") |
| input_per_million | float | (required) | USD per 1M input tokens |
| output_per_million | float | (required) | USD per 1M output tokens |

### Preset Pricing Configurations

| Model | Input ($/1M) | Output ($/1M) |
|-------|-------------|---------------|
| gemini-2.0-flash | 0.075 | 0.30 |
| gemini-2.0-flash-thinking | 0.075 | 0.30 |
| gemini-1.5-pro | 1.25 | 5.00 |
| gemini-1.5-flash | 0.075 | 0.30 |

### DecisionLogEntry

A single entry in the decision history.

| Attribute | Type | Description |
|-----------|------|-------------|
| step | int | Step number (1-indexed) |
| action | str | Action type: "update_flight_plan", "finalize_context" |
| reasoning | str | Explanation for the decision |
| config_diff | dict | Changes applied to flight plan (partial FlightPlan dict) |
| timestamp | datetime | When the decision was made |

### MapMetadata

Statistics about the current generated map.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| total_tokens | int | 0 | Estimated token count of current map |
| file_count | int | 0 | Number of files included in map |
| focus_areas | list[str] | [] | Paths currently at high verbosity (L3-L4) |
| excluded_count | int | 0 | Number of files at L0 (excluded) |
| budget_utilization | float | 0.0 | Percentage of token budget used |

### TurnReport

Output structure for interactive mode breakpoints.

| Attribute | Type | Description |
|-----------|------|-------------|
| step_number | int | Current iteration number |
| cost_this_turn | float | USD cost of the last iteration |
| total_cost | float | Cumulative USD cost |
| map_size_tokens | int | Current map token count |
| budget_remaining | float | Remaining USD budget |
| focus_areas | list[str] | High-verbosity paths |
| last_action | str | What the agent did last |
| reasoning | str | Agent's reasoning for last action |

### NavigatorOutput

Final output structure when exploration completes.

| Attribute | Type | Description |
|-----------|------|-------------|
| context_string | str | The final rendered map content |
| flight_plan_yaml | str | Serialized FlightPlan for reproduction |
| reasoning_summary | str | Agent's explanation of final selection |
| total_iterations | int | Number of refinement cycles |
| total_cost | float | Total USD spent on exploration |
| token_count | int | Final context size in tokens |

### FlightPlan (Reused from Layer 1)

Imported from `repo_map.core.flight_plan`. Complete configuration for rendering.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| budget | int | 20000 | Token budget limit |
| focus | Focus \| None | None | Focus boosting configuration |
| verbosity | list[VerbosityRule] | [] | Per-path verbosity rules |
| custom_queries | list[CustomQuery] | [] | Custom tree-sitter queries |

---

## Relationships

```
NavigatorState
├── BudgetConfig
│   └── ModelPricingRates
├── FlightPlan (from Layer 1)
│   ├── Focus
│   │   ├── PathBoost[]
│   │   └── SymbolBoost[]
│   ├── VerbosityRule[]
│   └── CustomQuery[]
├── DecisionLogEntry[]
└── MapMetadata

TurnReport (generated from NavigatorState)

NavigatorOutput (final output)
├── context_string (from Artifact)
├── flight_plan_yaml (from NavigatorState.flight_plan)
└── reasoning_summary (from NavigatorState)
```

---

## State Lifecycle

### Initialization

```python
initial_state = NavigatorState(
    user_task="Refactor the auth middleware",
    repo_path="/path/to/repo",
    execution_mode="autonomous",
    budget_config=BudgetConfig(
        max_spend_usd=2.0,
        model_pricing_rates=GEMINI_2_FLASH_PRICING,
    ),
    flight_plan=FlightPlan(budget=20000),  # Start with defaults
    decision_log=[],
    map_metadata=MapMetadata(),
)
```

### After Each Iteration

```python
# Agent calls update_flight_plan tool
state.decision_log.append(DecisionLogEntry(
    step=len(state.decision_log) + 1,
    action="update_flight_plan",
    reasoning="Increasing verbosity on src/auth/ because user mentioned login",
    config_diff={"verbosity": [{"pattern": "src/auth/**", "level": 4}]},
    timestamp=datetime.now(),
))
state.flight_plan = updated_plan
state.map_metadata = new_metadata
state.budget_config.current_spend_usd += iteration_cost
```

### On Completion

```python
# Agent calls finalize_context tool
state.exploration_complete = True
state.reasoning_summary = "Focused on auth/ and middleware/ directories..."

# Output generated
output = NavigatorOutput(
    context_string=load_artifact("current_map.txt"),
    flight_plan_yaml=state.flight_plan.to_yaml(),
    reasoning_summary=state.reasoning_summary,
    total_iterations=len(state.decision_log),
    total_cost=state.budget_config.current_spend_usd,
    token_count=state.map_metadata.total_tokens,
)
```

---

## Validation Rules

### NavigatorState

- `user_task` must be non-empty
- `repo_path` must exist as a directory
- `execution_mode` must be "autonomous" or "interactive"
- `budget_config.max_spend_usd` must be > 0
- `flight_plan.budget` must be > 0

### DecisionLogEntry

- `step` must be > 0
- `action` must be one of: "update_flight_plan", "finalize_context"
- `reasoning` must be non-empty
- `config_diff` must be valid partial FlightPlan

### BudgetConfig

- `current_spend_usd` must be >= 0
- `current_spend_usd` should not exceed `max_spend_usd` (enforced by plugin)

---

## Pydantic Model Definitions

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from repo_map.core.flight_plan import FlightPlan


class ModelPricingRates(BaseModel):
    """Token pricing rates per million tokens."""
    model_name: str
    input_per_million: float = Field(gt=0)
    output_per_million: float = Field(gt=0)


class BudgetConfig(BaseModel):
    """Cost budget configuration and tracking."""
    max_spend_usd: float = Field(default=2.0, gt=0)
    current_spend_usd: float = Field(default=0.0, ge=0)
    model_pricing_rates: ModelPricingRates


class DecisionLogEntry(BaseModel):
    """A single decision in the exploration history."""
    step: int = Field(gt=0)
    action: Literal["update_flight_plan", "finalize_context"]
    reasoning: str = Field(min_length=1)
    config_diff: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class MapMetadata(BaseModel):
    """Statistics about the current map output."""
    total_tokens: int = Field(default=0, ge=0)
    file_count: int = Field(default=0, ge=0)
    focus_areas: list[str] = Field(default_factory=list)
    excluded_count: int = Field(default=0, ge=0)
    budget_utilization: float = Field(default=0.0, ge=0, le=100)


class NavigatorState(BaseModel):
    """Root state model for the Navigator agent."""
    user_task: str = Field(min_length=1)
    repo_path: str
    execution_mode: Literal["autonomous", "interactive"] = "autonomous"
    budget_config: BudgetConfig
    flight_plan: FlightPlan
    decision_log: list[DecisionLogEntry] = Field(default_factory=list)
    map_metadata: MapMetadata = Field(default_factory=MapMetadata)
    interactive_pause: bool = False
    exploration_complete: bool = False
    reasoning_summary: str = ""

    @field_validator("repo_path")
    @classmethod
    def validate_repo_path(cls, v: str) -> str:
        from pathlib import Path
        if not Path(v).is_dir():
            raise ValueError(f"Repository path does not exist: {v}")
        return v
```
