"""Navigator agent definition and instruction provider.

This module provides the LlmAgent configuration and dynamic instruction
generation for the Navigator agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from google.adk.agents import LlmAgent

from repo_map.navigator.state import get_navigator_state
from repo_map.navigator.tools import NAVIGATOR_TOOLS

if TYPE_CHECKING:
  from google.adk.agents.readonly_context import ReadonlyContext

  from repo_map.navigator.state import NavigatorState


def format_decision_log(state: NavigatorState, max_entries: int = 5) -> str:
  """Format decision log for prompt inclusion.

  Args:
      state: Current NavigatorState
      max_entries: Maximum number of recent entries to include

  Returns:
      Formatted string of recent decisions
  """
  if not state.decision_log:
    return "(No previous decisions)"

  # Get most recent entries
  recent = state.decision_log[-max_entries:]

  lines = []
  for entry in recent:
    action_desc = entry.action.replace("_", " ")
    lines.append(f"Step {entry.step}: {action_desc}")
    lines.append(f"  Reasoning: {entry.reasoning}")
    if entry.config_diff:
      changes = []
      for key, value in entry.config_diff.items():
        if key == "verbosity" and isinstance(value, list):
          for rule in value:
            pattern = rule.get("pattern", "?")
            level = rule.get("level", "?")
            changes.append(f"{pattern} → L{level}")
        elif key == "budget":
          changes.append(f"budget → {value}")
        else:
          changes.append(f"{key} updated")
      if changes:
        lines.append(f"  Changes: {', '.join(changes)}")
    lines.append("")

  return "\n".join(lines).strip()


async def navigator_instruction_provider(context: ReadonlyContext) -> str:
  """Build dynamic instruction from current state.

  This function is called before each LLM invocation to construct
  a fresh context containing only the essential information:
  - User's goal (immutable)
  - Current map output
  - Recent decision history
  - Budget status

  Args:
      context: ADK ReadonlyContext with state and artifact access

  Returns:
      Formatted instruction string for the agent
  """
  try:
    state = get_navigator_state(context)
  except (ValueError, KeyError):
    # Initial state not set yet - provide bootstrap instruction
    return (
      "You are the Navigator Agent for repo-map. "
      "Your task is to explore a codebase and build an optimal context window "
      "for the user's goal.\n\n"
      "The system is initializing. Please wait for the initial repository scan."
    )

  # Load current map from artifact (updated via tools)
  map_content = None
  try:
    map_artifact = await context.load_artifact(filename="current_map.txt")
    if map_artifact and map_artifact.text:
      map_content = map_artifact.text
  except Exception:
    pass  # Artifact not found yet

  # Fall back to initial map from session state
  if not map_content:
    initial_map = context.state.get("initial_map")
    map_content = initial_map or "(No map generated yet - call update_flight_plan)"

  # Build economics summary
  budget_used = state.budget_config.current_spend_usd
  budget_max = state.budget_config.max_spend_usd
  budget_pct = state.budget_config.budget_utilization_pct

  # Token utilization
  token_budget = state.flight_plan.budget
  token_used = state.map_metadata.total_tokens
  token_pct = (token_used / token_budget * 100) if token_budget > 0 else 0

  # Format decision history
  decision_history = format_decision_log(state)

  # Build and return instruction
  return f"""You are the Navigator Agent for repo-map.
Your task is to explore a codebase and construct an optimal context window
for the user's specific goal.

## User's Goal
{state.user_task}

## Token Budget
- Target: {token_budget:,} tokens
- Current map: {token_used:,} tokens ({token_pct:.1f}% of budget)
- Files included: {state.map_metadata.file_count}
- Files excluded: {state.map_metadata.excluded_count}

## Cost Budget
- Used: ${budget_used:.4f} / ${budget_max:.2f} ({budget_pct:.1f}%)
- Remaining: ${state.budget_config.remaining_budget:.4f}

## Decision History
{decision_history}

## Current Repository Map
```
{map_content}
```

## Your Task
Analyze the current map against the user's goal. Decide your next action:

1. **Zoom in** - Increase verbosity (level 3-4) on areas needing more detail
2. **Zoom out** - Decrease verbosity (level 0-2) on irrelevant areas
3. **Finalize** - If context is optimal, call finalize_context

### Verbosity Levels
- Level 0: Exclude file completely
- Level 1: File path only
- Level 2: Structure (classes, functions signatures)
- Level 3: Implementation (full function bodies)
- Level 4: Full file content

### Guidelines
- Start broad (low verbosity) to survey the repository structure
- Progressively increase verbosity on areas relevant to the user's goal
- Decrease verbosity on irrelevant areas to save tokens
- Monitor token budget utilization - aim for 80-95% utilization
- When confident the context is comprehensive, call finalize_context
- Provide clear reasoning for every decision

### Important
- Always provide the 'reasoning' parameter explaining your decision
- For update_flight_plan, provide 'updates' with verbosity rules
- Stay within the token budget by balancing zoom-in with zoom-out
"""


def create_navigator_agent(model: str = "gemini-2.0-flash") -> LlmAgent:
  """Create and configure the Navigator LlmAgent.

  Args:
      model: Model identifier to use (default: gemini-2.0-flash)

  Returns:
      Configured LlmAgent instance
  """
  return LlmAgent(
    model=model,
    name="navigator",
    description="Intelligent codebase exploration agent for repo-map",
    instruction=navigator_instruction_provider,
    tools=list(NAVIGATOR_TOOLS),  # type: ignore[arg-type]
  )
