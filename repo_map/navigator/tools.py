"""Navigator tools for flight plan manipulation.

This module provides the ADK tools used by the Navigator agent:
- update_flight_plan: Modify flight plan and regenerate context map
- finalize_context: Complete exploration and prepare final output
"""

from __future__ import annotations

import asyncio
import re
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from google.adk.tools import FunctionTool
from google.genai.types import Part

from repo_map.core.flight_plan import FlightPlan
from repo_map.navigator.state import (
  DecisionLogEntry,
  MapMetadata,
  get_navigator_state,
  update_navigator_state,
)

if TYPE_CHECKING:
  from google.adk.tools import ToolContext

logger = structlog.get_logger()


def parse_map_header(map_output: str) -> MapMetadata:
  """Parse the repo-map output header to extract metadata.

  The repo-map CLI outputs a header with statistics like:
  # Repository Map (15,234 tokens, 42 files)

  Args:
      map_output: Raw output from repo-map CLI

  Returns:
      MapMetadata with extracted statistics
  """
  metadata = MapMetadata()

  # Try to extract token count from header
  # Pattern: "Repository Map (X tokens" or "X tokens"
  token_match = re.search(r"(\d[\d,]*)\s*tokens?", map_output)
  if token_match:
    # Remove commas and convert to int
    metadata.total_tokens = int(token_match.group(1).replace(",", ""))

  # Try to extract file count
  file_match = re.search(r"(\d[\d,]*)\s*files?", map_output)
  if file_match:
    metadata.file_count = int(file_match.group(1).replace(",", ""))

  # Extract focus areas from high-verbosity patterns
  # Look for paths that appear in detailed sections
  focus_areas: list[str] = []
  for line in map_output.split("\n"):
    # Look for file paths with content (not just listed)
    if line.startswith("## ") and "/" in line:
      # Extract path from markdown header
      path = line.lstrip("# ").strip()
      if path and not path.startswith("Repository"):
        focus_areas.append(path)

  metadata.focus_areas = focus_areas[:10]  # Limit to top 10

  return metadata


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
) -> dict[str, Any]:
  """Update the flight plan configuration and regenerate the context map.

  This tool modifies the Navigator's flight plan based on the agent's analysis
  and runs the repo-map CLI to generate an updated context map.

  Args:
      reasoning: Explanation for why these changes are being made.
      updates: Partial dictionary of FlightPlan fields to update.
          - verbosity: List of {pattern, level} rules (0-4)
          - focus: {paths: [{pattern, weight}], symbols: [{name, weight}]}
          - budget: Token budget limit

  Returns:
      Dictionary with status and map metadata:
      - status: "success" or "error"
      - map_tokens: Current map size in tokens
      - files_included: Number of files in the map
      - error: Error message if status is "error"
  """
  try:
    state = get_navigator_state(tool_context)
  except (ValueError, KeyError) as e:
    return {"status": "error", "error": f"State not initialized: {e}"}

  # Apply updates to flight plan
  try:
    updated_plan = _merge_flight_plan_updates(state.flight_plan, updates)
  except Exception as e:
    logger.warning("flight_plan_update_failed", error=str(e), updates=updates)
    return {"status": "error", "error": f"Invalid flight plan updates: {e}"}

  # Write flight plan to temp file
  with tempfile.NamedTemporaryFile(
    mode="w",
    suffix=".yaml",
    delete=False,
  ) as f:
    f.write(updated_plan.to_yaml())
    config_path = f.name

  try:
    # Execute repo-map CLI in thread pool to avoid blocking
    def run_cli() -> subprocess.CompletedProcess[str]:
      return subprocess.run(
        [
          "repo-map",
          "generate",
          str(state.repo_path),
          "--config",
          config_path,
        ],
        capture_output=True,
        text=True,
        timeout=120,  # 2 minute timeout
      )

    result = await asyncio.to_thread(run_cli)

    if result.returncode != 0:
      logger.warning(
        "repo_map_cli_error",
        returncode=result.returncode,
        stderr=result.stderr,
      )
      return {
        "status": "error",
        "error": f"CLI error: {result.stderr[:500]}",
      }

    map_output = result.stdout

  except subprocess.TimeoutExpired:
    return {"status": "error", "error": "CLI execution timed out"}
  except FileNotFoundError:
    return {"status": "error", "error": "repo-map CLI not found"}
  finally:
    # Clean up temp file
    Path(config_path).unlink(missing_ok=True)

  # Save output as artifact
  map_artifact = Part.from_text(text=map_output)
  await tool_context.save_artifact(
    filename="current_map.txt",
    artifact=map_artifact,
  )

  # Parse metadata from output
  map_metadata = parse_map_header(map_output)

  # Calculate budget utilization
  if updated_plan.budget > 0:
    map_metadata.budget_utilization = (
      map_metadata.total_tokens / updated_plan.budget
    ) * 100

  # Log decision
  state.decision_log.append(
    DecisionLogEntry(
      step=len(state.decision_log) + 1,
      action="update_flight_plan",
      reasoning=reasoning,
      config_diff=updates,
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

  return {
    "status": "success",
    "map_tokens": map_metadata.total_tokens,
    "files_included": map_metadata.file_count,
    "budget_utilization": f"{map_metadata.budget_utilization:.1f}%",
  }


async def finalize_context(
  summary: str,
  tool_context: ToolContext,
) -> dict[str, Any]:
  """Finalize the exploration and prepare final outputs.

  Call this tool when the context map is optimal for the user's goal,
  or when budget constraints require stopping.

  Args:
      summary: Reasoning summary explaining the final context selection,
          including what areas were focused on and why.

  Returns:
      Dictionary with final status:
      - status: "complete"
      - total_iterations: Number of exploration steps taken
      - total_cost: Total USD spent on exploration
      - token_count: Final context size in tokens
  """
  try:
    state = get_navigator_state(tool_context)
  except (ValueError, KeyError) as e:
    return {"status": "error", "error": f"State not initialized: {e}"}

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
    total_cost=state.budget_config.current_spend_usd,
    tokens=state.map_metadata.total_tokens,
  )

  return {
    "status": "complete",
    "total_iterations": len(state.decision_log),
    "total_cost": state.budget_config.current_spend_usd,
    "token_count": state.map_metadata.total_tokens,
  }


# Create FunctionTool wrappers for ADK
update_flight_plan_tool = FunctionTool(func=update_flight_plan)
finalize_context_tool = FunctionTool(func=finalize_context)

# Export list of all tools
NAVIGATOR_TOOLS: list[FunctionTool] = [update_flight_plan_tool, finalize_context_tool]
