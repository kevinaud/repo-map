"""Navigator tools for flight plan manipulation.

This module provides the ADK tools used by the Navigator agent:
- update_flight_plan: Modify flight plan and regenerate context map
- finalize_context: Complete exploration and prepare final output
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from google.adk.tools import FunctionTool
from google.genai.types import Part
from pydantic import BaseModel, Field

from repo_map.core.flight_plan import FlightPlan
from repo_map.mapper import generate_repomap
from repo_map.navigator.state import (
  DecisionLogEntry,
  MapMetadata,
  get_navigator_state,
  update_navigator_state,
)

if TYPE_CHECKING:
  from google.adk.tools import ToolContext

  from repo_map.mapper import MapResult

logger = structlog.get_logger()


class UpdateFlightPlanResult(BaseModel):
  """Result from update_flight_plan tool."""

  status: str = Field(description="'success' or 'error'")
  map_tokens: int = Field(default=0, description="Current map size in tokens")
  files_included: int = Field(default=0, description="Number of files in the map")
  budget_utilization: str = Field(default="0.0%", description="Token budget usage %")
  error: str | None = Field(default=None, description="Error message if failed")


class FinalizeContextResult(BaseModel):
  """Result from finalize_context tool."""

  status: str = Field(description="'complete' or 'error'")
  total_iterations: int = Field(default=0, description="Number of exploration steps")
  total_cost: float = Field(default=0.0, description="Total USD spent")
  token_count: int = Field(default=0, description="Final context size in tokens")
  error: str | None = Field(default=None, description="Error message if failed")


def _merge_flight_plan_updates(
  current: FlightPlan,
  updates: dict[str, Any],
) -> FlightPlan:
  """Deep merge updates into current flight plan.

  Args:
      current: Current FlightPlan
      updates: Partial dictionary of fields to update

  Returns:
      New FlightPlan with updates applied
  """
  current_dict = current.model_dump()

  # Handle verbosity list specially - append/update rather than replace
  if "verbosity" in updates:
    new_verbosity = updates.pop("verbosity", [])
    existing_verbosity = current_dict.get("verbosity", [])

    # Create pattern -> rule mapping for efficient lookup
    pattern_map = {rule["pattern"]: rule for rule in existing_verbosity}

    # Update or add new rules
    for new_rule in new_verbosity:
      pattern_map[new_rule["pattern"]] = new_rule

    current_dict["verbosity"] = list(pattern_map.values())

  # Merge other updates
  for key, value in updates.items():
    if isinstance(value, dict) and isinstance(current_dict.get(key), dict):
      current_dict[key].update(value)
    else:
      current_dict[key] = value

  return FlightPlan.model_validate(current_dict)


async def update_flight_plan(
  reasoning: str,
  updates: dict[str, Any],
  tool_context: ToolContext,
) -> UpdateFlightPlanResult:
  """Update the flight plan configuration and regenerate the context map.

  This tool modifies the Navigator's flight plan based on the agent's analysis
  and regenerates the context map directly using the repo-map library.

  The 'updates' parameter should be provided as an RFC 6902 JSON Patch style
  update, specifying changes to the flight plan configuration.

  Args:
      reasoning: Explanation for why these changes are being made.
      updates: Partial dictionary of FlightPlan fields to update.
          - verbosity: List of {pattern, level} rules (0-4)
          - focus: {paths: [{pattern, weight}], symbols: [{name, weight}]}
          - budget: Token budget limit

  Returns:
      UpdateFlightPlanResult with status and map metadata.

  Raises:
      NavigatorStateError: If navigator state is not initialized.
  """
  # Get state - raises NavigatorStateError if not initialized
  state = get_navigator_state(tool_context)

  # Store old flight plan for config diff
  old_flight_plan = state.flight_plan

  # Apply updates to flight plan
  try:
    updated_plan = _merge_flight_plan_updates(state.flight_plan, updates)
  except Exception as e:
    logger.warning("flight_plan_update_failed", error=str(e), updates=updates)
    return UpdateFlightPlanResult(
      status="error",
      error=f"Invalid flight plan updates: {e}",
    )

  # Generate repo map directly using library API
  def run_repomap() -> MapResult | None:
    return generate_repomap(
      root_dir=Path(state.repo_path),
      flight_plan=updated_plan,
      token_limit=updated_plan.budget,
    )

  result = await asyncio.to_thread(run_repomap)

  if result is None:
    return UpdateFlightPlanResult(
      status="error",
      error="No files found in repository",
    )

  # Save output as artifact
  map_artifact = Part.from_text(text=result.content)
  await tool_context.save_artifact(
    filename="current_map.txt",
    artifact=map_artifact,
  )

  # Create map metadata from result
  map_metadata = MapMetadata(
    total_tokens=result.total_tokens,
    file_count=len(result.files),
    focus_areas=result.focus_areas,
  )

  # Calculate budget utilization
  if updated_plan.budget > 0:
    map_metadata.budget_utilization = (result.total_tokens / updated_plan.budget) * 100

  # Create config patch using RFC 6902 JSON Patch
  config_patch = DecisionLogEntry.create_patch(old_flight_plan, updated_plan)

  # Log decision
  state.decision_log.append(
    DecisionLogEntry(
      step=len(state.decision_log) + 1,
      action="update_flight_plan",
      reasoning=reasoning,
      config_patch=config_patch,
      timestamp=datetime.now(UTC),
    )
  )

  # Update state
  state.flight_plan = updated_plan
  state.map_metadata = map_metadata

  # Set interactive pause if in interactive mode
  if state.execution_mode == "interactive":
    state.interactive_pause = True

  # Persist state
  update_navigator_state(tool_context, state)

  logger.info(
    "flight_plan_updated",
    step=len(state.decision_log),
    tokens=map_metadata.total_tokens,
    files=map_metadata.file_count,
    utilization=f"{map_metadata.budget_utilization:.1f}%",
  )

  return UpdateFlightPlanResult(
    status="success",
    map_tokens=map_metadata.total_tokens,
    files_included=map_metadata.file_count,
    budget_utilization=f"{map_metadata.budget_utilization:.1f}%",
  )


async def finalize_context(
  summary: str,
  tool_context: ToolContext,
) -> FinalizeContextResult:
  """Finalize the exploration and prepare final outputs.

  Call this tool when the context map is optimal for the user's goal,
  or when budget constraints require stopping.

  Args:
      summary: Reasoning summary explaining the final context selection,
          including what areas were focused on and why.

  Returns:
      FinalizeContextResult with final status.

  Raises:
      NavigatorStateError: If navigator state is not initialized.
  """
  # Get state - raises NavigatorStateError if not initialized
  state = get_navigator_state(tool_context)

  # Log final decision
  state.decision_log.append(
    DecisionLogEntry(
      step=len(state.decision_log) + 1,
      action="finalize_context",
      reasoning=summary,
      timestamp=datetime.now(UTC),
    )
  )

  # Mark exploration complete
  state.exploration_complete = True
  state.reasoning_summary = summary

  # Persist state
  update_navigator_state(tool_context, state)

  logger.info(
    "exploration_finalized",
    iterations=len(state.decision_log),
    total_cost=float(state.budget_config.current_spend_usd),
    tokens=state.map_metadata.total_tokens,
  )

  return FinalizeContextResult(
    status="complete",
    total_iterations=len(state.decision_log),
    total_cost=float(state.budget_config.current_spend_usd),
    token_count=state.map_metadata.total_tokens,
  )


# Create FunctionTool wrappers for ADK
update_flight_plan_tool = FunctionTool(func=update_flight_plan)
finalize_context_tool = FunctionTool(func=finalize_context)

# Export list of all tools
NAVIGATOR_TOOLS: list[FunctionTool] = [update_flight_plan_tool, finalize_context_tool]
