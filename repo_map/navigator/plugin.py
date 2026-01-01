"""Budget enforcement plugin for Navigator cost tracking.

This module provides an ADK plugin that tracks token usage and enforces
cost budget limits during agent execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.genai.types import Content, Part

from repo_map.navigator.pricing import calculate_cost
from repo_map.navigator.state import (
  NAVIGATOR_STATE_KEY,
  get_navigator_state,
)

if TYPE_CHECKING:
  from google.adk.agents.callback_context import CallbackContext
  from google.adk.models.llm_request import LlmRequest

  from repo_map.navigator.state import NavigatorState

logger = structlog.get_logger()


class BudgetEnforcementPlugin(BasePlugin):
  """Plugin to enforce cost budget limits during Navigator execution.

  Tracks token usage via after_model_callback and can terminate execution
  before budget is exceeded via before_model_callback.
  """

  def __init__(self) -> None:
    super().__init__(name="budget_enforcement")
    self._last_iteration_cost: float = 0.0

  @property
  def last_iteration_cost(self) -> float:
    """Get the cost of the last LLM call."""
    return self._last_iteration_cost

  def _estimate_request_cost(
    self,
    llm_request: LlmRequest,
    state: NavigatorState,
  ) -> float:
    """Estimate cost of an LLM request before execution.

    Uses a conservative estimate based on typical response size.
    """
    # Estimate input tokens from request content
    input_text = ""
    if llm_request.contents:
      for content in llm_request.contents:
        if content.parts:
          for part in content.parts:
            if hasattr(part, "text") and part.text:
              input_text += part.text

    # Rough estimate: 4 chars per token
    estimated_input_tokens = len(input_text) // 4

    # Conservative output estimate: assume 2000 tokens
    estimated_output_tokens = 2000

    return calculate_cost(
      estimated_input_tokens,
      estimated_output_tokens,
      state.budget_config.model_pricing_rates,
    )

  async def before_model_callback(
    self,
    *,
    callback_context: CallbackContext,
    llm_request: LlmRequest,
  ) -> LlmResponse | None:
    """Check budget before LLM call; return mock response if exceeded.

    Args:
        callback_context: ADK callback context with state access
        llm_request: The LLM request about to be sent

    Returns:
        Mock LlmResponse if budget would be exceeded, None to proceed
    """
    try:
      state = get_navigator_state(callback_context)
    except (ValueError, KeyError):
      # State not initialized yet, allow request
      return None

    estimated_cost = self._estimate_request_cost(llm_request, state)
    projected_total = state.budget_config.current_spend_usd + estimated_cost

    if projected_total > state.budget_config.max_spend_usd:
      logger.warning(
        "budget_exceeded",
        current_spend=state.budget_config.current_spend_usd,
        estimated_cost=estimated_cost,
        max_spend=state.budget_config.max_spend_usd,
      )

      # Return a termination response that the agent will understand
      return LlmResponse(
        content=Content(
          parts=[
            Part(
              text=(
                "BUDGET_EXCEEDED: The cost budget has been exhausted. "
                "Call finalize_context to deliver the current results."
              )
            )
          ]
        ),
      )

    return None  # Allow LLM call to proceed

  async def after_model_callback(
    self,
    *,
    callback_context: CallbackContext,
    llm_response: LlmResponse,
  ) -> LlmResponse | None:
    """Track actual token usage after LLM call.

    Args:
        callback_context: ADK callback context with state access
        llm_response: The LLM response received

    Returns:
        None (does not modify response)
    """
    if not llm_response.usage_metadata:
      logger.debug("no_usage_metadata_in_response")
      self._last_iteration_cost = 0.0
      return None

    try:
      state = get_navigator_state(callback_context)
    except (ValueError, KeyError) as e:
      # State not available, skip tracking
      logger.debug("state_unavailable_for_cost_tracking", error=str(e))
      return None

    # Extract token counts
    input_tokens = llm_response.usage_metadata.prompt_token_count or 0
    output_tokens = llm_response.usage_metadata.candidates_token_count or 0

    # Calculate and track cost
    cost = calculate_cost(
      input_tokens,
      output_tokens,
      state.budget_config.model_pricing_rates,
    )
    self._last_iteration_cost = cost

    # Update state with new spend
    state.budget_config.current_spend_usd += cost

    # Persist updated state
    callback_context.state[NAVIGATOR_STATE_KEY] = state.model_dump(mode="json")

    logger.debug(
      "token_usage_tracked",
      input_tokens=input_tokens,
      output_tokens=output_tokens,
      cost=cost,
      total_spend=state.budget_config.current_spend_usd,
    )

    return None  # Don't modify response
