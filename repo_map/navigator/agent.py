"""Navigator agent definition and instruction provider.

This module provides the LlmAgent configuration and dynamic instruction
generation for the Navigator agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from google.adk.agents import LlmAgent

from repo_map.navigator.prompts import (
  build_prompt_context,
  load_map_content,
  render_bootstrap_prompt,
  render_navigator_prompt,
)
from repo_map.navigator.state import NavigatorStateError, get_navigator_state
from repo_map.navigator.tools import NAVIGATOR_TOOLS

if TYPE_CHECKING:
  from google.adk.agents.readonly_context import ReadonlyContext


async def navigator_instruction_provider(context: ReadonlyContext) -> str:
  """Build dynamic instruction from current state.

  This function orchestrates prompt generation in three phases:
  1. Data gathering - load state and artifacts
  2. Data transformation - build prompt context
  3. Rendering - generate prompt via Jinja2 template

  Args:
      context: ADK ReadonlyContext with state and artifact access

  Returns:
      Formatted instruction string for the agent
  """
  # Phase 1: Data gathering
  try:
    state = get_navigator_state(context)
  except (ValueError, KeyError, NavigatorStateError):
    # Initial state not set yet - provide bootstrap instruction
    return render_bootstrap_prompt()

  map_content = await load_map_content(context)

  # Phase 2: Data transformation
  prompt_context = build_prompt_context(state, map_content)

  # Phase 3: Rendering
  return render_navigator_prompt(prompt_context)


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
