"""Prompt rendering for the Navigator agent using Jinja2 templates.

This module separates prompt construction into three clear phases:
1. Data gathering - collect all necessary state and artifacts
2. Data transformation - format data for template consumption
3. Rendering - pass data to Jinja2 template

The templates live in the templates/ subdirectory.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

if TYPE_CHECKING:
  from google.adk.agents.readonly_context import ReadonlyContext

  from repo_map.navigator.state import DecisionLogEntry, NavigatorState

# Template directory relative to this module
TEMPLATE_DIR = Path(__file__).parent / "templates"


def _format_number(value: int | float) -> str:
  """Format a number with thousand separators."""
  if isinstance(value, float):
    return f"{value:,.1f}"
  return f"{value:,}"


def _format_pct(value: float) -> str:
  """Format a percentage value."""
  return f"{value:.1f}%"


def _format_currency(value: Decimal | float) -> str:
  """Format a currency value."""
  if isinstance(value, Decimal):
    # Use 4 decimal places for small values, 2 for larger
    if value < Decimal("0.01"):
      return f"{float(value):.4f}"
    return f"{float(value):.2f}"
  if value < 0.01:
    return f"{value:.4f}"
  return f"{value:.2f}"


def _create_jinja_env() -> Environment:
  """Create a configured Jinja2 environment."""
  env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(default=False),
    trim_blocks=True,
    lstrip_blocks=True,
  )

  # Register custom filters
  env.filters["format_number"] = _format_number
  env.filters["format_pct"] = _format_pct
  env.filters["format_currency"] = _format_currency

  return env


# Singleton environment instance
_jinja_env: Environment | None = None


def get_jinja_env() -> Environment:
  """Get or create the Jinja2 environment singleton."""
  global _jinja_env
  if _jinja_env is None:
    _jinja_env = _create_jinja_env()
  return _jinja_env


@dataclass
class DecisionEntry:
  """Transformed decision log entry for template rendering."""

  step: int
  action: str
  reasoning: str
  changes: list[str]


@dataclass
class PromptContext:
  """All data needed to render the navigator prompt.

  This dataclass represents the complete context passed to the Jinja2
  template. All data transformation happens before constructing this
  object, keeping the template logic minimal.
  """

  # User's task
  user_task: str

  # Token budget
  token_budget: int
  token_used: int
  token_utilization_pct: float
  file_count: int
  excluded_count: int

  # Cost budget
  cost_used: Decimal
  cost_max: Decimal
  cost_utilization_pct: float
  cost_remaining: Decimal

  # Decision history
  decision_history: list[DecisionEntry]

  # Map content
  map_content: str


def _format_config_patch(patch: list[dict[str, Any]]) -> list[str]:
  """Format JSON Patch operations into human-readable changes.

  Args:
      patch: List of RFC 6902 JSON Patch operations

  Returns:
      List of human-readable change descriptions
  """
  changes: list[str] = []
  for op in patch:
    operation: str = str(op.get("op", ""))
    path: str = str(op.get("path", ""))
    value: Any = op.get("value")

    if path == "/budget":
      changes.append(f"budget → {value}")
    elif path.startswith("/verbosity"):
      if operation == "add" and isinstance(value, dict):
        pattern = str(value.get("pattern", "?"))  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
        level = value.get("level", "?")  # pyright: ignore[reportUnknownMemberType]
        changes.append(f"{pattern} → L{level}")
      elif operation == "replace" and "/level" in path:
        changes.append(f"verbosity level → {value}")
      else:
        changes.append("verbosity updated")
    elif path.startswith("/focus"):
      changes.append("focus updated")
    else:
      # Generic path description
      field = path.split("/")[-1] if "/" in path else path
      changes.append(f"{field} updated")

  return changes

  return changes


def transform_decision_log(
  entries: list[DecisionLogEntry],
  max_entries: int = 5,
) -> list[DecisionEntry]:
  """Transform decision log entries for template rendering.

  Args:
      entries: Raw decision log entries from state
      max_entries: Maximum number of recent entries to include

  Returns:
      List of transformed DecisionEntry objects
  """
  if not entries:
    return []

  recent = entries[-max_entries:]
  result: list[DecisionEntry] = []

  for entry in recent:
    changes = _format_config_patch(entry.config_patch)
    result.append(
      DecisionEntry(
        step=entry.step,
        action=entry.action,
        reasoning=entry.reasoning,
        changes=changes,
      )
    )

  return result


def build_prompt_context(
  state: NavigatorState,
  map_content: str,
) -> PromptContext:
  """Build the complete prompt context from navigator state.

  This is the data transformation phase - all business logic for
  preparing template data happens here.

  Args:
      state: Current NavigatorState
      map_content: Current map content string

  Returns:
      PromptContext ready for template rendering
  """
  # Token utilization
  token_budget = state.flight_plan.budget
  token_used = state.map_metadata.total_tokens
  token_pct = (token_used / token_budget * 100) if token_budget > 0 else 0.0

  # Decision history transformation
  decision_history = transform_decision_log(state.decision_log)

  return PromptContext(
    user_task=state.user_task,
    token_budget=token_budget,
    token_used=token_used,
    token_utilization_pct=token_pct,
    file_count=state.map_metadata.file_count,
    excluded_count=state.map_metadata.excluded_count,
    cost_used=state.budget_config.current_spend_usd,
    cost_max=state.budget_config.max_spend_usd,
    cost_utilization_pct=state.budget_config.budget_utilization_pct,
    cost_remaining=state.budget_config.remaining_budget,
    decision_history=decision_history,
    map_content=map_content,
  )


def render_navigator_prompt(ctx: PromptContext) -> str:
  """Render the navigator prompt from context.

  This is the rendering phase - pure template execution with no
  business logic.

  Args:
      ctx: Complete prompt context

  Returns:
      Rendered prompt string
  """
  env = get_jinja_env()
  template = env.get_template("navigator_prompt.jinja2")
  return template.render(
    user_task=ctx.user_task,
    token_budget=ctx.token_budget,
    token_used=ctx.token_used,
    token_utilization_pct=ctx.token_utilization_pct,
    file_count=ctx.file_count,
    excluded_count=ctx.excluded_count,
    cost_used=ctx.cost_used,
    cost_max=ctx.cost_max,
    cost_utilization_pct=ctx.cost_utilization_pct,
    cost_remaining=ctx.cost_remaining,
    decision_history=ctx.decision_history,
    map_content=ctx.map_content,
  )


def render_bootstrap_prompt() -> str:
  """Render the bootstrap prompt for uninitialized state.

  Returns:
      Bootstrap prompt string
  """
  env = get_jinja_env()
  template = env.get_template("bootstrap_prompt.jinja2")
  return template.render()


async def load_map_content(context: ReadonlyContext) -> str:
  """Load map content from artifacts or session state.

  Args:
      context: ADK ReadonlyContext

  Returns:
      Map content string
  """
  # Try loading from artifact first (updated via tools)
  try:
    map_artifact = await context.load_artifact(filename="current_map.txt")  # pyright: ignore[reportUnknownMemberType]
    if map_artifact and map_artifact.text:  # pyright: ignore[reportUnknownMemberType]
      return str(map_artifact.text)  # pyright: ignore[reportUnknownMemberType]
  except Exception:
    pass

  # Fall back to initial map from session state
  initial_map = context.state.get("initial_map")
  if initial_map:
    return str(initial_map)

  return "(No map generated yet - call update_flight_plan)"
