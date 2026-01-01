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

import jsonpatch
import structlog
from google.adk.tools import (  # noqa: TC002 - ToolContext needed at runtime for ADK
  FunctionTool,
  ToolContext,
)
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


def _apply_flight_plan_patch(
  current: FlightPlan,
  patch_operations: list[dict[str, Any]],
) -> FlightPlan:
  """Apply RFC 6902 JSON Patch operations to a flight plan.

  Args:
      current: Current FlightPlan
      patch_operations: List of RFC 6902 patch operations (op, path, value)

  Returns:
      New FlightPlan with patches applied
  """
  current_dict = current.model_dump(mode="json")
  patch = jsonpatch.JsonPatch(patch_operations)
  patched_dict = patch.apply(current_dict)  # type: ignore[reportUnknownMemberType]
  return FlightPlan.model_validate(patched_dict)


async def update_flight_plan(
  reasoning: str,
  patch_operations: list[dict[str, Any]],
  tool_context: ToolContext,
) -> UpdateFlightPlanResult:
  """Update the flight plan configuration and regenerate the context map.

  This tool modifies the Navigator's flight plan based on the agent's analysis
  and regenerates the context map directly using the repo-map library.

  Args:
      reasoning: Explanation for why these changes are being made.
      patch_operations: RFC 6902 JSON Patch operations to apply to the flight plan.
          Each operation is a dict with 'op', 'path', and optionally 'value'.
          Example: [{"op": "replace", "path": "/budget", "value": 30000}]

  Returns:
      UpdateFlightPlanResult with status and map metadata.

  Raises:
      NavigatorStateError: If navigator state is not initialized.
  """
  # Get state - raises NavigatorStateError if not initialized
  state = get_navigator_state(tool_context)

  # Apply patch operations to flight plan
  try:
    updated_plan = _apply_flight_plan_patch(state.flight_plan, patch_operations)
  except Exception as e:
    logger.warning(
      "flight_plan_update_failed", error=str(e), patch_operations=patch_operations
    )
    return UpdateFlightPlanResult(
      status="error",
      error=f"Invalid flight plan patch: {e}",
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

  # Log decision - use the patch_operations directly as config_patch
  state.decision_log.append(
    DecisionLogEntry(
      step=len(state.decision_log) + 1,
      action="update_flight_plan",
      reasoning=reasoning,
      config_patch=patch_operations,
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
