"""Unit tests for Navigator agent and instruction provider."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from repo_map.core.flight_plan import FlightPlan
from repo_map.navigator.agent import (
  create_navigator_agent,
  format_decision_log,
  navigator_instruction_provider,
)
from repo_map.navigator.pricing import GEMINI_3_FLASH_PRICING
from repo_map.navigator.state import (
  NAVIGATOR_STATE_KEY,
  BudgetConfig,
  DecisionLogEntry,
  MapMetadata,
  NavigatorState,
)
from tests.adk_helpers import create_callback_context as _create_callback_context

if TYPE_CHECKING:
  from collections.abc import Generator

  from google.adk.agents.callback_context import CallbackContext


async def create_test_callback_context(
  state: dict | None = None,
  artifact_content: str | None = None,
) -> CallbackContext:
  """Create a CallbackContext for testing using shared adk_helpers.

  Args:
      state: Session state dictionary.
      artifact_content: Optional text content to save as current_map.txt artifact.

  Returns:
      A real CallbackContext backed by in-memory services.
  """
  agent = create_navigator_agent()
  artifacts: dict[str, str | bytes] | None = None
  if artifact_content is not None:
    artifacts = {"current_map.txt": artifact_content}

  return await _create_callback_context(agent, state=state, artifacts=artifacts)


def create_test_state(
  repo_path: str,
  user_task: str = "Understand the authentication system",
) -> NavigatorState:
  """Create a NavigatorState for testing."""
  return NavigatorState(
    user_task=user_task,
    repo_path=repo_path,
    budget_config=BudgetConfig(
      max_spend_usd=2.0,
      current_spend_usd=0.01,
      model_pricing_rates=GEMINI_3_FLASH_PRICING,
    ),
    flight_plan=FlightPlan(budget=20000),
    decision_log=[
      DecisionLogEntry(
        step=1,
        action="update_flight_plan",
        reasoning="Initial scan of repository structure",
        config_diff={"verbosity": [{"pattern": "**/*", "level": 1}]},
        timestamp=datetime.now(UTC),
      ),
    ],
    map_metadata=MapMetadata(
      total_tokens=5000,
      file_count=42,
      focus_areas=["src/auth/"],
      excluded_count=10,
      budget_utilization=25.0,
    ),
  )


class TestFormatDecisionLog:
  """Tests for format_decision_log function."""

  @pytest.fixture
  def temp_dir(self) -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
      yield tmpdir

  def test_empty_log(self, temp_dir: str) -> None:
    """Test formatting empty decision log."""
    state = NavigatorState(
      user_task="Test",
      repo_path=temp_dir,
      budget_config=BudgetConfig(model_pricing_rates=GEMINI_3_FLASH_PRICING),
      flight_plan=FlightPlan(budget=20000),
      decision_log=[],
    )
    result = format_decision_log(state)
    assert result == "(No previous decisions)"

  def test_single_entry(self, temp_dir: str) -> None:
    """Test formatting single decision."""
    state = create_test_state(temp_dir)
    result = format_decision_log(state)

    assert "Step 1" in result
    assert "update flight plan" in result
    assert "Initial scan" in result
    assert "**/* → L1" in result

  def test_max_entries_limit(self, temp_dir: str) -> None:
    """Test that max_entries limits output."""
    state = create_test_state(temp_dir)
    # Add more entries
    for i in range(2, 10):
      state.decision_log.append(
        DecisionLogEntry(
          step=i,
          action="update_flight_plan",
          reasoning=f"Decision {i}",
          timestamp=datetime.now(UTC),
        )
      )

    result = format_decision_log(state, max_entries=3)

    # Should only have steps 7, 8, 9 (last 3)
    assert "Step 7" in result
    assert "Step 8" in result
    assert "Step 9" in result
    assert "Step 1" not in result
    assert "Step 6" not in result


class TestNavigatorInstructionProvider:
  """Tests for navigator_instruction_provider function."""

  @pytest.fixture
  def temp_dir(self) -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
      yield tmpdir

  @pytest.mark.asyncio
  async def test_instruction_includes_user_goal(self, temp_dir: str) -> None:
    """Test that instruction includes user's goal."""
    state = create_test_state(temp_dir, user_task="Refactor the payment system")
    context = await create_test_callback_context(
      state={NAVIGATOR_STATE_KEY: state.model_dump(mode="json")},
    )

    instruction = await navigator_instruction_provider(context)

    assert "Refactor the payment system" in instruction

  @pytest.mark.asyncio
  async def test_instruction_includes_budget_info(self, temp_dir: str) -> None:
    """Test that instruction includes budget information."""
    state = create_test_state(temp_dir)
    state.budget_config.current_spend_usd = 0.50
    state.budget_config.max_spend_usd = 2.0
    context = await create_test_callback_context(
      state={NAVIGATOR_STATE_KEY: state.model_dump(mode="json")},
    )

    instruction = await navigator_instruction_provider(context)

    assert "$0.50" in instruction or "0.5000" in instruction
    assert "$2.00" in instruction

  @pytest.mark.asyncio
  async def test_instruction_includes_token_budget(self, temp_dir: str) -> None:
    """Test that instruction includes token budget info."""
    state = create_test_state(temp_dir)
    context = await create_test_callback_context(
      state={NAVIGATOR_STATE_KEY: state.model_dump(mode="json")},
    )

    instruction = await navigator_instruction_provider(context)

    assert "20,000 tokens" in instruction or "20000" in instruction
    assert "5,000 tokens" in instruction or "5000" in instruction

  @pytest.mark.asyncio
  async def test_instruction_includes_map_content(self, temp_dir: str) -> None:
    """Test that instruction includes current map."""
    state = create_test_state(temp_dir)
    context = await create_test_callback_context(
      state={NAVIGATOR_STATE_KEY: state.model_dump(mode="json")},
      artifact_content="# Repository Map\n## src/main.py\nclass Main:\n...",
    )

    instruction = await navigator_instruction_provider(context)

    assert "Repository Map" in instruction
    assert "src/main.py" in instruction

  @pytest.mark.asyncio
  async def test_instruction_handles_missing_state(self) -> None:
    """Test instruction when state is not initialized."""
    context = await create_test_callback_context(state={})

    instruction = await navigator_instruction_provider(context)

    assert "initializing" in instruction.lower()

  @pytest.mark.asyncio
  async def test_instruction_includes_verbosity_levels(self, temp_dir: str) -> None:
    """Test that instruction explains verbosity levels."""
    state = create_test_state(temp_dir)
    context = await create_test_callback_context(
      state={NAVIGATOR_STATE_KEY: state.model_dump(mode="json")},
    )

    instruction = await navigator_instruction_provider(context)

    assert "Level 0" in instruction
    assert "Level 4" in instruction
    assert "Exclude" in instruction


class TestCreateNavigatorAgent:
  """Tests for create_navigator_agent function."""

  def test_creates_agent_with_defaults(self) -> None:
    """Test agent creation with default settings."""
    agent = create_navigator_agent()

    assert agent.name == "navigator"
    assert len(agent.tools) == 2  # update_flight_plan, finalize_context

  def test_creates_agent_with_custom_model(self) -> None:
    """Test agent creation with custom model."""
    agent = create_navigator_agent(model="gemini-1.5-pro")

    assert agent.model == "gemini-1.5-pro"

  def test_agent_has_instruction_provider(self) -> None:
    """Test that agent has instruction provider configured."""
    agent = create_navigator_agent()

    # The instruction should be the async function
    assert agent.instruction == navigator_instruction_provider
