"""Navigator state models for agent state management.

This module provides Pydantic models for the Navigator agent's state,
including budget configuration, decision logging, and output structures.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

import jsonpatch
from pydantic import BaseModel, Field, field_validator

from repo_map.core.flight_plan import FlightPlan  # noqa: TC001
from repo_map.navigator.pricing import (  # noqa: TC001
  GEMINI_3_FLASH_PRICING,
  ModelPricing,
)

if TYPE_CHECKING:
  from google.adk.agents.readonly_context import ReadonlyContext
  from google.adk.tools import ToolContext


class BudgetConfig(BaseModel):
  """Cost budget configuration and tracking."""

  max_spend_usd: Decimal = Field(
    default=Decimal("0.50"), gt=0, description="Max spend in USD"
  )
  current_spend_usd: Decimal = Field(
    default=Decimal("0.0"), ge=0, description="Amount spent so far"
  )
  model_pricing: ModelPricing = Field(default_factory=lambda: GEMINI_3_FLASH_PRICING)

  @property
  def remaining_budget(self) -> Decimal:
    """Calculate remaining budget in USD."""
    return max(Decimal("0.0"), self.max_spend_usd - self.current_spend_usd)

  @property
  def budget_utilization_pct(self) -> float:
    """Calculate budget utilization as percentage."""
    if self.max_spend_usd <= 0:
      return 100.0
    return float((self.current_spend_usd / self.max_spend_usd) * 100)


class DecisionLogEntry(BaseModel):
  """A single decision in the exploration history.

  Uses RFC 6902 JSON Patch format for config diffs to provide a robust,
  standard representation of changes between flight plan states.
  """

  step: int = Field(gt=0, description="Step number (1-indexed)")
  action: Literal["update_flight_plan", "finalize_context"] = Field(
    description="Action type"
  )
  reasoning: str = Field(min_length=1, description="Explanation for the decision")
  config_patch: list[dict[str, Any]] = Field(
    default_factory=list,
    description="RFC 6902 JSON Patch operations describing flight plan changes",
  )
  timestamp: datetime = Field(default_factory=datetime.now)

  @staticmethod
  def create_patch(
    old_flight_plan: FlightPlan, new_flight_plan: FlightPlan
  ) -> list[dict[str, Any]]:
    """Create an RFC 6902 JSON Patch from two flight plan states.

    Args:
        old_flight_plan: The previous flight plan state
        new_flight_plan: The new flight plan state

    Returns:
        List of JSON Patch operations (op, path, value)
    """
    old_dict = old_flight_plan.model_dump(mode="json")
    new_dict = new_flight_plan.model_dump(mode="json")
    patch = jsonpatch.make_patch(old_dict, new_dict)  # type: ignore[reportUnknownMemberType]
    return list(patch.patch)  # type: ignore[reportUnknownMemberType]


class MapMetadata(BaseModel):
  """Statistics about the current map output."""

  total_tokens: int = Field(default=0, ge=0, description="Estimated token count")
  file_count: int = Field(default=0, ge=0, description="Number of files included")
  focus_areas: list[str] = Field(
    default_factory=list, description="Paths at high verbosity"
  )
  excluded_count: int = Field(default=0, ge=0, description="Files at L0 (excluded)")
  budget_utilization: float = Field(
    default=0.0, ge=0, le=100, description="Token budget utilization %"
  )


class NavigatorState(BaseModel):
  """Root state model for the Navigator agent.

  Stored in session.state["navigator"] and reconstructed each iteration.
  """

  user_task: str = Field(min_length=1, description="User's goal/task description")
  repo_path: str = Field(description="Absolute path to repository")
  execution_mode: Literal["autonomous", "interactive"] = Field(
    default="autonomous", description="Execution mode"
  )
  budget_config: BudgetConfig = Field(description="Cost budget configuration")
  flight_plan: FlightPlan = Field(description="Current repo-map configuration")
  decision_log: list[DecisionLogEntry] = Field(
    default_factory=list, description="History of decisions"
  )
  map_metadata: MapMetadata = Field(
    default_factory=MapMetadata, description="Current map statistics"
  )
  interactive_pause: bool = Field(
    default=False, description="Flag for interactive mode pause"
  )
  exploration_complete: bool = Field(
    default=False, description="Flag when exploration is finished"
  )
  reasoning_summary: str = Field(
    default="", description="Final reasoning (set by finalize_context)"
  )

  @field_validator("repo_path")
  @classmethod
  def validate_repo_path(cls, v: str) -> str:
    """Validate that repo_path exists as a directory."""
    from pathlib import Path

    if not Path(v).is_dir():
      raise ValueError(f"Repository path does not exist: {v}")
    return v


@dataclass
class TurnReport:
  """Report returned after each interactive turn.

  Contains cost and status information for user review.
  """

  step_number: int
  cost_this_turn: float
  total_cost: float
  map_size_tokens: int
  budget_remaining: float
  focus_areas: list[str]
  last_action: str
  reasoning: str


@dataclass
class NavigatorOutput:
  """Final output structure when exploration completes."""

  context_string: str
  flight_plan_yaml: str
  reasoning_summary: str
  total_iterations: int
  total_cost: float
  token_count: int


# State key used in session.state
NAVIGATOR_STATE_KEY = "navigator"


def get_navigator_state(context: ReadonlyContext | ToolContext) -> NavigatorState:
  """Deserialize NavigatorState from session.state.

  Args:
      context: ADK context with access to session state (ReadonlyContext or ToolContext)

  Returns:
      NavigatorState reconstructed from session state

  Raises:
      ValueError: If state is missing or invalid
  """
  # Use .get() directly - works with both MappingProxyType and ADK's State class
  # Do NOT use dict(context.state) - ADK's State class doesn't support iteration
  navigator_data = context.state.get(NAVIGATOR_STATE_KEY)

  if navigator_data is None:
    raise ValueError("Navigator state not found in session.state")

  return NavigatorState.model_validate(navigator_data)


def update_navigator_state(tool_context: ToolContext, state: NavigatorState) -> None:
  """Serialize and persist NavigatorState to session.state.

  Args:
      tool_context: ADK tool context for state updates
      state: NavigatorState to persist
  """
  tool_context.state[NAVIGATOR_STATE_KEY] = state.model_dump(mode="json")
