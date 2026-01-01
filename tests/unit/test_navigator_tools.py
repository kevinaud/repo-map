"""Unit tests for Navigator tools.

Tests the Navigator agent's tools: _merge_flight_plan_updates,
update_flight_plan, and finalize_context. Uses real ADK services via adk_helpers
rather than mocking ADK internals.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

if TYPE_CHECKING:
  from collections.abc import Generator

  from google.adk.agents import LlmAgent

# adk_helpers is a sibling module in tests/
import sys
from pathlib import Path

import pytest
from google.adk.agents import LlmAgent

from repo_map.core.flight_plan import FlightPlan, VerbosityRule
from repo_map.mapper import MapResult
from repo_map.navigator.pricing import GEMINI_3_FLASH_PRICING
from repo_map.navigator.state import (
  NAVIGATOR_STATE_KEY,
  BudgetConfig,
  NavigatorState,
  NavigatorStateError,
)
from repo_map.navigator.tools import (
  _merge_flight_plan_updates,
  finalize_context,
  update_flight_plan,
)

sys.path.insert(0, str(Path(__file__).parent.parent))
from adk_helpers import FakeLlm, create_tool_context


class TestMergeFlightPlanUpdates:
  """Tests for _merge_flight_plan_updates helper."""

  def test_update_budget(self) -> None:
    """Test updating budget field."""
    current = FlightPlan(budget=20000)
    updated = _merge_flight_plan_updates(current, {"budget": 30000})
    assert updated.budget == 30000

  def test_merge_verbosity_rules(self) -> None:
    """Test that verbosity rules are merged, not replaced."""
    current = FlightPlan(
      budget=20000,
      verbosity=[
        VerbosityRule(pattern="src/**", level=2),
        VerbosityRule(pattern="tests/**", level=1),
      ],
    )
    updated = _merge_flight_plan_updates(
      current,
      {"verbosity": [{"pattern": "src/**", "level": 4}]},  # Update existing
    )

    # src/** should be updated, tests/** should remain
    patterns = {rule.pattern: rule.level for rule in updated.verbosity}
    assert patterns["src/**"] == 4
    assert patterns["tests/**"] == 1

  def test_add_new_verbosity_rule(self) -> None:
    """Test adding new verbosity rule."""
    current = FlightPlan(
      budget=20000, verbosity=[VerbosityRule(pattern="src/**", level=2)]
    )
    updated = _merge_flight_plan_updates(
      current,
      {"verbosity": [{"pattern": "docs/**", "level": 0}]},
    )

    patterns = {rule.pattern for rule in updated.verbosity}
    assert "src/**" in patterns
    assert "docs/**" in patterns


def create_navigator_state_dict(repo_path: str) -> dict[str, Any]:
  """Create a NavigatorState as a serialized dict for session state.

  Args:
      repo_path: Path to the repository.

  Returns:
      Serialized state dict suitable for session state.
  """
  state = NavigatorState(
    user_task="Test task",
    repo_path=repo_path,
    budget_config=BudgetConfig(model_pricing=GEMINI_3_FLASH_PRICING),
    flight_plan=FlightPlan(budget=20000),
  )
  return state.model_dump(mode="json")


@pytest.fixture
def sample_agent() -> LlmAgent:
  """Create a simple test agent for tool context.

  Uses FakeLlm since the model isn't called when testing tools directly.
  """
  return LlmAgent(name="test_agent", model=FakeLlm())


class TestUpdateFlightPlan:
  """Tests for update_flight_plan tool."""

  @pytest.fixture
  def temp_dir(self) -> Generator[str, None, None]:
    """Create a temporary directory for repo_path."""
    with tempfile.TemporaryDirectory() as tmpdir:
      yield tmpdir

  @pytest.mark.asyncio
  async def test_successful_update(self, temp_dir: str, sample_agent: LlmAgent) -> None:
    """Test successful flight plan update."""
    initial_state = {
      NAVIGATOR_STATE_KEY: create_navigator_state_dict(temp_dir),
    }
    tool_ctx = await create_tool_context(sample_agent, state=initial_state)

    # Mock generate_repomap to simulate direct library invocation
    mock_result = MapResult(
      content="# Repository Map\n\n## src/main.py\n...",
      files=["src/main.py"] * 25,
      total_tokens=15000,
      focus_areas=["src/main.py"],
    )

    with patch("repo_map.navigator.tools.generate_repomap", return_value=mock_result):
      result = await update_flight_plan(
        reasoning="Increasing verbosity on source files",
        updates={"verbosity": [{"pattern": "src/**", "level": 4}]},
        tool_context=tool_ctx,
      )

    assert result.status == "success"
    assert result.map_tokens == 15000
    assert result.files_included == 25

    # Verify state was updated via real session state
    updated_state = tool_ctx.state[NAVIGATOR_STATE_KEY]
    assert len(updated_state["decision_log"]) == 1
    assert updated_state["decision_log"][0]["action"] == "update_flight_plan"

  @pytest.mark.asyncio
  async def test_no_files_found_error(
    self, temp_dir: str, sample_agent: LlmAgent
  ) -> None:
    """Test handling when no files are found in repository."""
    initial_state = {
      NAVIGATOR_STATE_KEY: create_navigator_state_dict(temp_dir),
    }
    tool_ctx = await create_tool_context(sample_agent, state=initial_state)

    # Mock generate_repomap returning None (no files found)
    with patch("repo_map.navigator.tools.generate_repomap", return_value=None):
      result = await update_flight_plan(
        reasoning="Test",
        updates={},
        tool_context=tool_ctx,
      )

    assert result.status == "error"
    assert "No files found" in (result.error or "")

  @pytest.mark.asyncio
  async def test_missing_state_raises_error(self, sample_agent: LlmAgent) -> None:
    """Test that missing state raises NavigatorStateError."""
    tool_ctx = await create_tool_context(sample_agent, state={})

    with pytest.raises(NavigatorStateError, match="Navigator state not found"):
      await update_flight_plan(
        reasoning="Test",
        updates={},
        tool_context=tool_ctx,
      )

  @pytest.mark.asyncio
  async def test_interactive_pause_flag(
    self, temp_dir: str, sample_agent: LlmAgent
  ) -> None:
    """Test that interactive mode sets pause flag."""
    state_dict = create_navigator_state_dict(temp_dir)
    state_dict["execution_mode"] = "interactive"
    initial_state = {NAVIGATOR_STATE_KEY: state_dict}
    tool_ctx = await create_tool_context(sample_agent, state=initial_state)

    mock_result = MapResult(
      content="# Repository Map",
      files=["src/main.py"] * 5,
      total_tokens=1000,
      focus_areas=[],
    )

    with patch("repo_map.navigator.tools.generate_repomap", return_value=mock_result):
      await update_flight_plan(
        reasoning="Test",
        updates={},
        tool_context=tool_ctx,
      )

    updated_state = tool_ctx.state[NAVIGATOR_STATE_KEY]
    assert updated_state["interactive_pause"] is True


class TestFinalizeContext:
  """Tests for finalize_context tool."""

  @pytest.fixture
  def temp_dir(self) -> Generator[str, None, None]:
    """Create a temporary directory for repo_path."""
    with tempfile.TemporaryDirectory() as tmpdir:
      yield tmpdir

  @pytest.mark.asyncio
  async def test_successful_finalization(
    self, temp_dir: str, sample_agent: LlmAgent
  ) -> None:
    """Test successful context finalization."""
    state_dict = create_navigator_state_dict(temp_dir)
    state_dict["budget_config"]["current_spend_usd"] = "0.05"
    state_dict["map_metadata"]["total_tokens"] = 15000
    initial_state = {NAVIGATOR_STATE_KEY: state_dict}
    tool_ctx = await create_tool_context(sample_agent, state=initial_state)

    result = await finalize_context(
      summary=(
        "Focused on authentication and middleware directories for the refactoring task."
      ),
      tool_context=tool_ctx,
    )

    assert result.status == "complete"
    assert result.total_iterations == 1  # finalize_context adds itself
    assert result.total_cost == 0.05
    assert result.token_count == 15000

    # Verify state was updated via real session state
    updated_state = tool_ctx.state[NAVIGATOR_STATE_KEY]
    assert updated_state["exploration_complete"] is True
    assert "authentication" in updated_state["reasoning_summary"]

  @pytest.mark.asyncio
  async def test_missing_state_raises_error(self, sample_agent: LlmAgent) -> None:
    """Test that missing state raises NavigatorStateError."""
    tool_ctx = await create_tool_context(sample_agent, state={})

    with pytest.raises(NavigatorStateError, match="Navigator state not found"):
      await finalize_context(
        summary="Test summary",
        tool_context=tool_ctx,
      )

  @pytest.mark.asyncio
  async def test_decision_log_updated(
    self, temp_dir: str, sample_agent: LlmAgent
  ) -> None:
    """Test that decision log is updated on finalization."""
    state_dict = create_navigator_state_dict(temp_dir)
    # Add some prior decisions
    state_dict["decision_log"] = [
      {
        "step": 1,
        "action": "update_flight_plan",
        "reasoning": "Initial scan",
        "config_patch": [],
        "timestamp": datetime.now(UTC).isoformat(),
      }
    ]
    initial_state = {NAVIGATOR_STATE_KEY: state_dict}
    tool_ctx = await create_tool_context(sample_agent, state=initial_state)

    await finalize_context(
      summary="Final summary",
      tool_context=tool_ctx,
    )

    updated_state = tool_ctx.state[NAVIGATOR_STATE_KEY]
    assert len(updated_state["decision_log"]) == 2
    assert updated_state["decision_log"][1]["action"] == "finalize_context"
    assert updated_state["decision_log"][1]["step"] == 2
