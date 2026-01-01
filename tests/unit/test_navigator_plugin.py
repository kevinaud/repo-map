"""Unit tests for BudgetEnforcementPlugin.

Tests the budget enforcement plugin's ability to:
- Track token usage costs after LLM calls
- Block requests when budget would be exceeded
- Handle edge cases like missing state or zero tokens
"""

from __future__ import annotations

import sys
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from google.adk.agents import LlmAgent
from google.adk.models import LlmResponse
from google.adk.models.llm_request import LlmRequest
from google.genai import types

from repo_map.core.flight_plan import FlightPlan
from repo_map.navigator.plugin import BudgetEnforcementPlugin
from repo_map.navigator.pricing import GEMINI_3_FLASH_PRICING
from repo_map.navigator.state import (
  NAVIGATOR_STATE_KEY,
  BudgetConfig,
  NavigatorState,
  NavigatorStateError,
  get_navigator_state,
)

# adk_helpers is a sibling module in tests/
sys.path.insert(0, str(Path(__file__).parent.parent))
from adk_helpers import FakeLlm, create_callback_context

if TYPE_CHECKING:
  from collections.abc import Generator


def create_navigator_state(
  repo_path: str,
  max_spend: Decimal = Decimal("2.0"),
  current_spend: Decimal = Decimal("0.0"),
) -> dict:
  """Create NavigatorState as a dict for session state initialization.

  Args:
      repo_path: Path to the repository.
      max_spend: Maximum allowed spend in USD.
      current_spend: Current accumulated spend in USD.

  Returns:
      NavigatorState serialized as dict for session state.
  """
  state = NavigatorState(
    user_task="Test task",
    repo_path=repo_path,
    budget_config=BudgetConfig(
      max_spend_usd=max_spend,
      current_spend_usd=current_spend,
      model_pricing=GEMINI_3_FLASH_PRICING,
    ),
    flight_plan=FlightPlan(budget=20000),
  )
  return state.model_dump(mode="json")


def create_llm_request(content_text: str = "Test prompt") -> LlmRequest:
  """Create a real LlmRequest for testing.

  Args:
      content_text: The text content for the request.

  Returns:
      LlmRequest with the specified content.
  """
  return LlmRequest(
    contents=[
      types.Content(
        role="user",
        parts=[types.Part.from_text(text=content_text)],
      )
    ]
  )


def create_llm_response(
  input_tokens: int = 1000,
  output_tokens: int = 500,
) -> LlmResponse:
  """Create a real LlmResponse with usage metadata.

  Args:
      input_tokens: Number of input tokens to report.
      output_tokens: Number of output tokens to report.

  Returns:
      LlmResponse with usage metadata.
  """
  return LlmResponse(
    content=types.Content(
      role="model",
      parts=[types.Part.from_text(text="Response text")],
    ),
    usage_metadata=types.GenerateContentResponseUsageMetadata(
      prompt_token_count=input_tokens,
      candidates_token_count=output_tokens,
      total_token_count=input_tokens + output_tokens,
    ),
  )


def create_test_agent() -> LlmAgent:
  """Create a simple test agent using FakeLlm."""
  return LlmAgent(name="test_agent", model=FakeLlm())


class TestBudgetEnforcementPlugin:
  """Tests for BudgetEnforcementPlugin."""

  @pytest.fixture
  def plugin(self) -> BudgetEnforcementPlugin:
    """Create a plugin instance for testing."""
    return BudgetEnforcementPlugin()

  @pytest.fixture
  def temp_dir(self) -> Generator[str, None, None]:
    """Create a temporary directory for repo_path."""
    with tempfile.TemporaryDirectory() as tmpdir:
      yield tmpdir

  @pytest.mark.asyncio
  async def test_before_model_allows_within_budget(
    self,
    plugin: BudgetEnforcementPlugin,
    temp_dir: str,
  ) -> None:
    """Test that requests within budget are allowed."""
    state_dict = create_navigator_state(
      temp_dir, max_spend=Decimal("2.0"), current_spend=Decimal("0.0")
    )
    callback_ctx = await create_callback_context(
      create_test_agent(),
      state={NAVIGATOR_STATE_KEY: state_dict},
    )
    llm_request = create_llm_request("Short prompt")

    result = await plugin.before_model_callback(
      callback_context=callback_ctx,
      llm_request=llm_request,
    )

    assert result is None  # None means proceed

  @pytest.mark.asyncio
  async def test_before_model_blocks_over_budget(
    self,
    plugin: BudgetEnforcementPlugin,
    temp_dir: str,
  ) -> None:
    """Test that requests over budget return termination response."""
    # Set budget nearly exhausted
    state_dict = create_navigator_state(
      temp_dir, max_spend=Decimal("0.001"), current_spend=Decimal("0.0009")
    )
    callback_ctx = await create_callback_context(
      create_test_agent(),
      state={NAVIGATOR_STATE_KEY: state_dict},
    )
    llm_request = create_llm_request("A" * 10000)  # ~2500 tokens

    result = await plugin.before_model_callback(
      callback_context=callback_ctx,
      llm_request=llm_request,
    )

    assert result is not None
    assert result.content is not None
    assert result.content.parts is not None
    assert result.content.parts[0].text is not None
    assert "BUDGET_EXCEEDED" in result.content.parts[0].text

  @pytest.mark.asyncio
  async def test_before_model_raises_on_missing_state(
    self,
    plugin: BudgetEnforcementPlugin,
  ) -> None:
    """Test that missing state raises NavigatorStateError."""
    callback_ctx = await create_callback_context(
      create_test_agent(),
      state={},
    )
    llm_request = create_llm_request()

    with pytest.raises(NavigatorStateError, match="Navigator state not found"):
      await plugin.before_model_callback(
        callback_context=callback_ctx,
        llm_request=llm_request,
      )

  @pytest.mark.asyncio
  async def test_after_model_tracks_usage(
    self,
    plugin: BudgetEnforcementPlugin,
    temp_dir: str,
  ) -> None:
    """Test that token usage is tracked after LLM call."""
    state_dict = create_navigator_state(
      temp_dir, max_spend=Decimal("2.0"), current_spend=Decimal("0.0")
    )
    callback_ctx = await create_callback_context(
      create_test_agent(),
      state={NAVIGATOR_STATE_KEY: state_dict},
    )
    llm_response = create_llm_response(input_tokens=10000, output_tokens=2000)

    result = await plugin.after_model_callback(
      callback_context=callback_ctx,
      llm_response=llm_response,
    )

    assert result is None  # Should not modify response

    # Check that state was updated via proper accessor
    updated_state = get_navigator_state(callback_ctx)
    assert updated_state.budget_config.current_spend_usd > 0

    # Verify cost calculation with Gemini 3 Flash pricing:
    # (10k/1M * 0.50) + (2k/1M * 3.00) = 0.005 + 0.006 = 0.011
    expected_cost = Decimal("0.011")
    assert updated_state.budget_config.current_spend_usd == expected_cost

  @pytest.mark.asyncio
  async def test_after_model_skips_tracking_on_no_usage_metadata(
    self,
    plugin: BudgetEnforcementPlugin,
    temp_dir: str,
  ) -> None:
    """Test that missing usage metadata is handled gracefully.

    Warning logged, no cost update.
    """
    state_dict = create_navigator_state(temp_dir)
    callback_ctx = await create_callback_context(
      create_test_agent(),
      state={NAVIGATOR_STATE_KEY: state_dict},
    )
    llm_response = LlmResponse(
      content=types.Content(
        role="model",
        parts=[types.Part.from_text(text="Response")],
      ),
      usage_metadata=None,
    )

    # Should return None (no error raised) and skip cost tracking
    result = await plugin.after_model_callback(
      callback_context=callback_ctx,
      llm_response=llm_response,
    )
    assert result is None

    # State should be unchanged (no cost added)
    updated_state = NavigatorState.model_validate(
      callback_ctx.state[NAVIGATOR_STATE_KEY]
    )
    assert updated_state.budget_config.current_spend_usd == Decimal("0.0")

  @pytest.mark.asyncio
  async def test_last_iteration_cost_tracked(
    self,
    plugin: BudgetEnforcementPlugin,
    temp_dir: str,
  ) -> None:
    """Test that last iteration cost is accessible."""
    state_dict = create_navigator_state(temp_dir)
    callback_ctx = await create_callback_context(
      create_test_agent(),
      state={NAVIGATOR_STATE_KEY: state_dict},
    )
    llm_response = create_llm_response(input_tokens=5000, output_tokens=1000)

    await plugin.after_model_callback(
      callback_context=callback_ctx,
      llm_response=llm_response,
    )

    # Gemini 3 Flash: (5k/1M * 0.50) + (1k/1M * 3.00) = 0.0025 + 0.003 = 0.0055
    expected = Decimal("0.0055")
    assert plugin.last_iteration_cost == expected

  @pytest.mark.asyncio
  async def test_cumulative_spend_tracking(
    self,
    plugin: BudgetEnforcementPlugin,
    temp_dir: str,
  ) -> None:
    """Test that spend accumulates across multiple calls."""
    initial_spend = Decimal("0.01")
    state_dict = create_navigator_state(temp_dir, current_spend=initial_spend)
    callback_ctx = await create_callback_context(
      create_test_agent(),
      state={NAVIGATOR_STATE_KEY: state_dict},
    )

    # First call
    llm_response1 = create_llm_response(input_tokens=10000, output_tokens=2000)
    await plugin.after_model_callback(
      callback_context=callback_ctx,
      llm_response=llm_response1,
    )

    first_state = get_navigator_state(callback_ctx)
    first_total = first_state.budget_config.current_spend_usd
    assert first_total > initial_spend

    # Second call
    llm_response2 = create_llm_response(input_tokens=5000, output_tokens=1000)
    await plugin.after_model_callback(
      callback_context=callback_ctx,
      llm_response=llm_response2,
    )

    second_state = get_navigator_state(callback_ctx)
    second_total = second_state.budget_config.current_spend_usd
    assert second_total > first_total


class TestBudgetEnforcementEdgeCases:
  """Edge case tests for budget enforcement."""

  @pytest.fixture
  def plugin(self) -> BudgetEnforcementPlugin:
    """Create a plugin instance for testing."""
    return BudgetEnforcementPlugin()

  @pytest.fixture
  def temp_dir(self) -> Generator[str, None, None]:
    """Create a temporary directory for repo_path."""
    with tempfile.TemporaryDirectory() as tmpdir:
      yield tmpdir

  @pytest.mark.asyncio
  async def test_exact_budget_boundary(
    self,
    plugin: BudgetEnforcementPlugin,
    temp_dir: str,
  ) -> None:
    """Test behavior at exact budget boundary."""
    # Set spend just below max
    state_dict = create_navigator_state(
      temp_dir, max_spend=Decimal("0.01"), current_spend=Decimal("0.0099")
    )
    callback_ctx = await create_callback_context(
      create_test_agent(),
      state={NAVIGATOR_STATE_KEY: state_dict},
    )
    llm_request = create_llm_request("Small prompt")

    result = await plugin.before_model_callback(
      callback_context=callback_ctx,
      llm_request=llm_request,
    )

    # Should block because even small request will exceed
    assert result is not None
    assert result.content is not None
    assert result.content.parts is not None
    assert result.content.parts[0].text is not None
    assert "BUDGET_EXCEEDED" in result.content.parts[0].text

  @pytest.mark.asyncio
  async def test_zero_token_response(
    self,
    plugin: BudgetEnforcementPlugin,
    temp_dir: str,
  ) -> None:
    """Test handling of response with zero tokens."""
    state_dict = create_navigator_state(temp_dir)
    callback_ctx = await create_callback_context(
      create_test_agent(),
      state={NAVIGATOR_STATE_KEY: state_dict},
    )
    llm_response = create_llm_response(input_tokens=0, output_tokens=0)

    await plugin.after_model_callback(
      callback_context=callback_ctx,
      llm_response=llm_response,
    )

    assert plugin.last_iteration_cost == 0.0
