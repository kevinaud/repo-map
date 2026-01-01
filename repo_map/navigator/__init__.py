"""Navigator Agent for intelligent codebase exploration.

The Navigator is an autonomous AI agent that orchestrates the repo-map CLI
through iterative refinement cycles. It starts with a broad "satellite view"
of a repository and progressively zooms in on relevant areas while zooming
out on irrelevant ones, constructing an optimal context window for a specific
user task within defined token and cost constraints.

Key components:
- NavigatorState: Pydantic models for agent state management
- BudgetEnforcementPlugin: Cost tracking and budget enforcement
- Tools: update_flight_plan and finalize_context
- Runner: Execution modes (autonomous and interactive)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from repo_map.navigator.state import (
    BudgetConfig,
    MapMetadata,
    NavigatorOutput,
    NavigatorState,
    TurnReport,
  )

__all__ = [
  "BudgetConfig",
  "MapMetadata",
  "NavigatorOutput",
  "NavigatorState",
  "TurnReport",
]


# Lazy imports to avoid circular dependencies
def __getattr__(name: str):
  if name in ("NavigatorState", "BudgetConfig", "MapMetadata"):
    from repo_map.navigator.state import BudgetConfig, MapMetadata, NavigatorState

    return {
      "NavigatorState": NavigatorState,
      "BudgetConfig": BudgetConfig,
      "MapMetadata": MapMetadata,
    }[name]
  if name in ("TurnReport", "NavigatorOutput"):
    from repo_map.navigator.state import NavigatorOutput, TurnReport

    return {"TurnReport": TurnReport, "NavigatorOutput": NavigatorOutput}[name]
  raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
