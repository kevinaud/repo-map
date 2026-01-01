"""Unit tests for Navigator agent and instruction provider."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from repo_map.core.flight_plan import FlightPlan
from repo_map.navigator.agent import (
  create_navigator_agent,
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
  from tests.adk_helpers import create_callback_context as _create_callback_context

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
      max_spend_usd=Decimal("2.0"),
      current_spend_usd=Decimal("0.01"),
      model_pricing=GEMINI_3_FLASH_PRICING,
    ),
    flight_plan=FlightPlan(budget=20000),
    decision_log=[
      DecisionLogEntry(
        step=1,
        action="update_flight_plan",
        reasoning="Initial scan of repository structure",
        config_patch=[
          {
            "op": "add",
            "path": "/verbosity/-",
            "value": {"pattern": "**/*", "level": 1},
          }
        ],
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
    state.budget_config.current_spend_usd = Decimal("0.50")
    state.budget_config.max_spend_usd = Decimal("2.0")
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
    # update_flight_plan, finalize_context
    assert len(agent.tools) == 2  # pyright: ignore[reportUnknownMemberType]

  def test_creates_agent_with_custom_model(self) -> None:
    """Test agent creation with custom model."""
    agent = create_navigator_agent(model="gemini-1.5-pro")

    assert agent.model == "gemini-1.5-pro"

  def test_agent_has_instruction_provider(self) -> None:
    """Test that agent has instruction provider configured."""
    agent = create_navigator_agent()

    # The instruction should be the async function
    assert agent.instruction == navigator_instruction_provider
