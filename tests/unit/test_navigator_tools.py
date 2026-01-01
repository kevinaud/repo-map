"""Unit tests for Navigator tools.

Tests the Navigator agent's tools: parse_map_header, _merge_flight_plan_updates,
update_flight_plan, and finalize_context. Uses real ADK services via adk_helpers
rather than mocking ADK internals.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
  from collections.abc import Generator

  from google.adk.agents import LlmAgent

import pytest

from repo_map.core.flight_plan import FlightPlan, VerbosityRule
from repo_map.navigator.agent import create_navigator_agent
from repo_map.navigator.pricing import GEMINI_3_FLASH_PRICING
from repo_map.navigator.state import (
  NAVIGATOR_STATE_KEY,
  BudgetConfig,
  NavigatorState,
)
from repo_map.navigator.tools import (
  _merge_flight_plan_updates,
  finalize_context,
  parse_map_header,
  update_flight_plan,
)
from tests.adk_helpers import create_tool_context


class TestParseMapHeader:
  """Tests for parse_map_header function."""

  def test_parse_tokens_and_files(self) -> None:
    """Test parsing standard header format."""
    output = """# Repository Map (15,234 tokens, 42 files)

## src/main.py
..."""
    metadata = parse_map_header(output)
    assert metadata.total_tokens == 15234
    assert metadata.file_count == 42

  def test_parse_without_commas(self) -> None:
    """Test parsing numbers without thousand separators."""
    output = """# Repository Map (5000 tokens, 10 files)"""
    metadata = parse_map_header(output)
    assert metadata.total_tokens == 5000
    assert metadata.file_count == 10

  def test_parse_focus_areas(self) -> None:
    """Test extracting focus areas from headers."""
    output = """# Repository Map (1000 tokens, 5 files)

## src/auth/login.py
code here

## src/auth/middleware.py
more code"""
    metadata = parse_map_header(output)
    assert "src/auth/login.py" in metadata.focus_areas
    assert "src/auth/middleware.py" in metadata.focus_areas

  def test_parse_empty_output(self) -> None:
    """Test parsing empty or minimal output."""
    metadata = parse_map_header("")
    assert metadata.total_tokens == 0
    assert metadata.file_count == 0
    assert metadata.focus_areas == []

  def test_parse_malformed_header(self) -> None:
    """Test parsing when header is missing expected info."""
    output = """# Repository Map

Some content without stats"""
    metadata = parse_map_header(output)
    assert metadata.total_tokens == 0
    assert metadata.file_count == 0


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
    budget_config=BudgetConfig(model_pricing_rates=GEMINI_3_FLASH_PRICING),
    flight_plan=FlightPlan(budget=20000),
  )
  return state.model_dump(mode="json")


@pytest.fixture
def sample_agent() -> LlmAgent:
  """Create a Navigator agent for tool context.

  Uses the real agent factory - the model isn't called when testing tools
  directly, so using the default model string is fine.
  """
  return create_navigator_agent()


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

    # Mock subprocess to simulate CLI execution (external process - OK to mock)
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = (
      "# Repository Map (15000 tokens, 25 files)\n\n## src/main.py\n..."
    )
    mock_result.stderr = ""

    with patch("repo_map.navigator.tools.subprocess.run", return_value=mock_result):
      result = await update_flight_plan(
        reasoning="Increasing verbosity on source files",
        updates={"verbosity": [{"pattern": "src/**", "level": 4}]},
        tool_context=tool_ctx,
      )

    assert result["status"] == "success"
    assert result["map_tokens"] == 15000
    assert result["files_included"] == 25

    # Verify state was updated via real session state
    updated_state = tool_ctx.state[NAVIGATOR_STATE_KEY]
    assert len(updated_state["decision_log"]) == 1
    assert updated_state["decision_log"][0]["action"] == "update_flight_plan"

  @pytest.mark.asyncio
  async def test_cli_error_handling(
    self, temp_dir: str, sample_agent: LlmAgent
  ) -> None:
    """Test handling of CLI errors."""
    initial_state = {
      NAVIGATOR_STATE_KEY: create_navigator_state_dict(temp_dir),
    }
    tool_ctx = await create_tool_context(sample_agent, state=initial_state)

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Error: invalid configuration"

    with patch("repo_map.navigator.tools.subprocess.run", return_value=mock_result):
      result = await update_flight_plan(
        reasoning="Test",
        updates={},
        tool_context=tool_ctx,
      )

    assert result["status"] == "error"
    assert "CLI error" in result["error"]

  @pytest.mark.asyncio
  async def test_missing_state_error(self, sample_agent: LlmAgent) -> None:
    """Test error when state is not initialized."""
    tool_ctx = await create_tool_context(sample_agent, state={})

    result = await update_flight_plan(
      reasoning="Test",
      updates={},
      tool_context=tool_ctx,
    )

    assert result["status"] == "error"
    assert "State not initialized" in result["error"]

  @pytest.mark.asyncio
  async def test_interactive_pause_flag(
    self, temp_dir: str, sample_agent: LlmAgent
  ) -> None:
    """Test that interactive mode sets pause flag."""
    state_dict = create_navigator_state_dict(temp_dir)
    state_dict["execution_mode"] = "interactive"
    initial_state = {NAVIGATOR_STATE_KEY: state_dict}
    tool_ctx = await create_tool_context(sample_agent, state=initial_state)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "# Repository Map (1000 tokens, 5 files)"

    with patch("repo_map.navigator.tools.subprocess.run", return_value=mock_result):
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
    state_dict["budget_config"]["current_spend_usd"] = 0.05
    state_dict["map_metadata"]["total_tokens"] = 15000
    initial_state = {NAVIGATOR_STATE_KEY: state_dict}
    tool_ctx = await create_tool_context(sample_agent, state=initial_state)

    result = await finalize_context(
      summary=(
        "Focused on authentication and middleware directories for the refactoring task."
      ),
      tool_context=tool_ctx,
    )

    assert result["status"] == "complete"
    assert result["total_iterations"] == 1  # finalize_context adds itself
    assert result["total_cost"] == 0.05
    assert result["token_count"] == 15000

    # Verify state was updated via real session state
    updated_state = tool_ctx.state[NAVIGATOR_STATE_KEY]
    assert updated_state["exploration_complete"] is True
    assert "authentication" in updated_state["reasoning_summary"]

  @pytest.mark.asyncio
  async def test_missing_state_error(self, sample_agent: LlmAgent) -> None:
    """Test error when state is not initialized."""
    tool_ctx = await create_tool_context(sample_agent, state={})

    result = await finalize_context(
      summary="Test summary",
      tool_context=tool_ctx,
    )

    assert result["status"] == "error"
    assert "State not initialized" in result["error"]

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
        "config_diff": {},
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
