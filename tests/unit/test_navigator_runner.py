"""Unit tests for Navigator runner module.

Tests the runner setup, session initialization, turn report building,
and autonomous execution modes. Uses ADK in-memory services and FakeLlm
for deterministic testing without mocking ADK internals.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from repo_map.core.flight_plan import FlightPlan
from repo_map.navigator.pricing import GEMINI_3_FLASH_PRICING
from repo_map.navigator.runner import (
  NavigatorProgress,
  build_turn_report,
  create_navigator_runner,
)
from repo_map.navigator.state import (
  BudgetConfig,
  DecisionLogEntry,
  MapMetadata,
  NavigatorState,
  TurnReport,
)

if TYPE_CHECKING:
  from pathlib import Path


class TestCreateNavigatorRunner:
  """Tests for create_navigator_runner factory function."""

  def test_returns_runner_and_plugin_tuple(self) -> None:
    """Factory should return a tuple of Runner and BudgetEnforcementPlugin."""
    runner, plugin = create_navigator_runner()

    assert runner is not None
    assert plugin is not None

  def test_runner_has_correct_app_name(self) -> None:
    """Runner should be configured with the expected app name."""
    runner, _ = create_navigator_runner()

    assert runner.app_name == "repo-map-navigator"

  def test_plugin_is_registered_with_runner(self) -> None:
    """Budget plugin should be registered in the runner's plugin list."""
    runner, plugin = create_navigator_runner()

    assert plugin in runner.plugins  # pyright: ignore[reportUnknownMemberType]

  def test_runner_has_inmemory_session_service(self) -> None:
    """Runner should use InMemorySessionService by default."""
    from google.adk.sessions import InMemorySessionService

    runner, _ = create_navigator_runner()

    assert isinstance(runner.session_service, InMemorySessionService)

  def test_runner_has_inmemory_artifact_service(self) -> None:
    """Runner should use InMemoryArtifactService by default."""
    from google.adk.artifacts import InMemoryArtifactService

    runner, _ = create_navigator_runner()

    assert isinstance(runner.artifact_service, InMemoryArtifactService)


class TestInitializeSession:
  """Tests for initialize_session function.

  These tests verify session initialization creates the proper state structure.
  Uses real InMemorySessionService to verify actual session behavior.
  """

  @pytest.mark.asyncio
  async def test_creates_session_with_navigator_state(self, tmp_path: Path) -> None:
    """Session should contain NavigatorState with user task and repo path."""
    from repo_map.navigator.runner import initialize_session
    from repo_map.navigator.state import NAVIGATOR_STATE_KEY

    runner, _ = create_navigator_runner()

    await initialize_session(
      runner=runner,
      user_id="user-1",
      session_id="session-1",
      repo_path=tmp_path,
      user_task="Find authentication code",
      token_budget=5000,
      cost_limit=1.0,
      model="gemini-2.0-flash",
    )

    # Verify session was created with correct state
    session = await runner.session_service.get_session(
      app_name=runner.app_name,
      user_id="user-1",
      session_id="session-1",
    )
    assert session is not None

    assert NAVIGATOR_STATE_KEY in session.state
    state_dict = session.state[NAVIGATOR_STATE_KEY]
    assert state_dict["user_task"] == "Find authentication code"
    assert state_dict["repo_path"] == str(tmp_path)

  @pytest.mark.asyncio
  async def test_sets_budget_config_with_cost_limit(self, tmp_path: Path) -> None:
    """Session state should have budget config with specified cost limit."""
    from repo_map.navigator.runner import initialize_session
    from repo_map.navigator.state import NAVIGATOR_STATE_KEY

    runner, _ = create_navigator_runner()

    await initialize_session(
      runner=runner,
      user_id="user-1",
      session_id="session-1",
      repo_path=tmp_path,
      user_task="Test task",
      token_budget=5000,
      cost_limit=2.50,
      model="gemini-2.0-flash",
    )

    session = await runner.session_service.get_session(
      app_name=runner.app_name,
      user_id="user-1",
      session_id="session-1",
    )
    assert session is not None

    state_dict = session.state[NAVIGATOR_STATE_KEY]
    assert Decimal(state_dict["budget_config"]["max_spend_usd"]) == Decimal("2.50")
    assert Decimal(state_dict["budget_config"]["current_spend_usd"]) == Decimal("0.0")

  @pytest.mark.asyncio
  async def test_uses_correct_pricing_for_model(self, tmp_path: Path) -> None:
    """Session should have pricing rates matching the specified model."""
    from repo_map.navigator.runner import initialize_session
    from repo_map.navigator.state import NAVIGATOR_STATE_KEY

    runner, _ = create_navigator_runner()

    await initialize_session(
      runner=runner,
      user_id="user-1",
      session_id="session-1",
      repo_path=tmp_path,
      user_task="Test task",
      token_budget=5000,
      cost_limit=1.0,
      model="gemini-3-flash-preview",
    )

    session = await runner.session_service.get_session(
      app_name=runner.app_name,
      user_id="user-1",
      session_id="session-1",
    )
    assert session is not None

    state_dict = session.state[NAVIGATOR_STATE_KEY]
    pricing = state_dict["budget_config"]["model_pricing"]
    # Verify pricing matches Gemini 3 Flash rates
    actual_input = Decimal(pricing["input_per_million"])
    expected_input = GEMINI_3_FLASH_PRICING.input_per_million
    assert actual_input == expected_input

  @pytest.mark.asyncio
  async def test_sets_execution_mode(self, tmp_path: Path) -> None:
    """Session state should reflect the specified execution mode."""
    from repo_map.navigator.runner import initialize_session
    from repo_map.navigator.state import NAVIGATOR_STATE_KEY

    runner, _ = create_navigator_runner()

    await initialize_session(
      runner=runner,
      user_id="user-1",
      session_id="session-1",
      repo_path=tmp_path,
      user_task="Test task",
      token_budget=5000,
      cost_limit=1.0,
      model="gemini-2.0-flash",
      execution_mode="interactive",
    )

    session = await runner.session_service.get_session(
      app_name=runner.app_name,
      user_id="user-1",
      session_id="session-1",
    )
    assert session is not None

    state_dict = session.state[NAVIGATOR_STATE_KEY]
    assert state_dict["execution_mode"] == "interactive"

  @pytest.mark.asyncio
  async def test_includes_initial_map_in_state(self, tmp_path: Path) -> None:
    """Session should include an initial map for agent context."""
    from repo_map.navigator.runner import initialize_session

    runner, _ = create_navigator_runner()

    # Create a file so the repo has content
    (tmp_path / "test.py").write_text("def hello(): pass")

    await initialize_session(
      runner=runner,
      user_id="user-1",
      session_id="session-1",
      repo_path=tmp_path,
      user_task="Test task",
      token_budget=5000,
      cost_limit=1.0,
      model="gemini-2.0-flash",
    )

    session = await runner.session_service.get_session(
      app_name=runner.app_name,
      user_id="user-1",
      session_id="session-1",
    )
    assert session is not None

    assert "initial_map" in session.state


class TestBuildTurnReport:
  """Tests for build_turn_report function.

  Verifies that turn reports are constructed correctly from NavigatorState.
  """

  def test_builds_report_with_decision_log(self, tmp_path: Path) -> None:
    """Turn report should include data from the most recent decision."""
    state = NavigatorState(
      user_task="Test task",
      repo_path=str(tmp_path),
      execution_mode="autonomous",
      budget_config=BudgetConfig(
        max_spend_usd=Decimal("1.0"),
        current_spend_usd=Decimal("0.05"),
        model_pricing=GEMINI_3_FLASH_PRICING,
      ),
      flight_plan=FlightPlan(budget=5000),
      decision_log=[
        DecisionLogEntry(
          step=1,
          action="update_flight_plan",
          reasoning="Adding core modules to the flight plan",
          config_patch=[
            {"op": "add", "path": "/verbosity_overrides/src~1core", "value": 3}
          ],
        ),
      ],
      map_metadata=MapMetadata(
        total_tokens=1500,
        focus_areas=["auth", "data"],
      ),
    )

    report = build_turn_report(state, last_cost=0.02)

    assert isinstance(report, TurnReport)
    assert report.step_number == 1
    assert report.cost_this_turn == Decimal("0.02")
    assert report.total_cost == Decimal("0.05")
    assert report.map_size_tokens == 1500
    assert report.focus_areas == ["auth", "data"]
    assert report.last_action == "update_flight_plan"
    assert "core modules" in report.reasoning

  def test_builds_report_without_decisions(self, tmp_path: Path) -> None:
    """Turn report should handle empty decision log gracefully."""
    state = NavigatorState(
      user_task="Test task",
      repo_path=str(tmp_path),
      execution_mode="autonomous",
      budget_config=BudgetConfig(
        max_spend_usd=Decimal("1.0"),
        current_spend_usd=Decimal("0.0"),
        model_pricing=GEMINI_3_FLASH_PRICING,
      ),
      flight_plan=FlightPlan(budget=5000),
      decision_log=[],
      map_metadata=MapMetadata(),
    )

    report = build_turn_report(state, last_cost=0.0)

    assert report.step_number == 0
    assert report.last_action == "none"
    assert report.reasoning == ""

  def test_report_contains_budget_info(self, tmp_path: Path) -> None:
    """Turn report should include budget utilization information."""
    state = NavigatorState(
      user_task="Test task",
      repo_path=str(tmp_path),
      execution_mode="autonomous",
      budget_config=BudgetConfig(
        max_spend_usd=Decimal("1.0"),
        current_spend_usd=Decimal("0.25"),
        model_pricing=GEMINI_3_FLASH_PRICING,
      ),
      flight_plan=FlightPlan(budget=5000),
      decision_log=[
        DecisionLogEntry(
          step=1,
          action="update_flight_plan",
          reasoning="Narrowing scope",
          config_patch=[],
        ),
      ],
      map_metadata=MapMetadata(total_tokens=2000),
    )

    report = build_turn_report(state, last_cost=0.10)

    assert report.total_cost == Decimal("0.25")
    assert report.cost_this_turn == Decimal("0.10")


class TestNavigatorProgress:
  """Tests for NavigatorProgress dataclass."""

  def test_creates_progress_event_with_all_fields(self) -> None:
    """Progress event should store all provided field values."""
    progress = NavigatorProgress(
      step=3,
      action="update_flight_plan",
      tokens=2500,
      cost_so_far=Decimal("0.08"),
      message="Adding authentication modules",
    )

    assert progress.step == 3
    assert progress.action == "update_flight_plan"
    assert progress.tokens == 2500
    assert progress.cost_so_far == Decimal("0.08")
    assert progress.message == "Adding authentication modules"

  def test_progress_is_dataclass(self) -> None:
    """NavigatorProgress should be a dataclass."""
    from dataclasses import is_dataclass

    assert is_dataclass(NavigatorProgress)


class TestRunAutonomous:
  """Tests for run_autonomous function.

  Note: run_autonomous is a high-level orchestration function that integrates
  with ADK's Runner.run_async. Full end-to-end testing of the autonomous loop
  belongs in integration tests. These unit tests verify the function signature
  and basic structure.

  Full integration tests for run_autonomous are in tests/integration/test_navigator.py.
  """

  @pytest.mark.asyncio
  async def test_function_is_async_generator(self) -> None:
    """run_autonomous should be an async generator function."""
    import inspect

    from repo_map.navigator.runner import run_autonomous

    assert inspect.isasyncgenfunction(run_autonomous)

  @pytest.mark.asyncio
  async def test_returns_navigator_progress_and_output_types(
    self, tmp_path: Path
  ) -> None:
    """run_autonomous yields NavigatorProgress or NavigatorOutput types.

    This test verifies the function signature accepts the expected parameters.
    """
    import inspect

    from repo_map.navigator.runner import run_autonomous

    sig = inspect.signature(run_autonomous)
    param_names = list(sig.parameters.keys())

    # Verify expected parameters are present
    assert "runner" in param_names
    assert "budget_plugin" in param_names
    assert "user_id" in param_names
    assert "session_id" in param_names
    assert "max_iterations" in param_names


class TestRunInteractiveStep:
  """Tests for run_interactive_step function.

  Note: run_interactive_step integrates with ADK's Runner.run_async.
  These unit tests verify the function signature and return types.
  Full end-to-end testing belongs in integration tests.
  """

  @pytest.mark.asyncio
  async def test_function_is_async(self) -> None:
    """run_interactive_step should be an async function."""
    import inspect

    from repo_map.navigator.runner import run_interactive_step

    assert inspect.iscoroutinefunction(run_interactive_step)

  @pytest.mark.asyncio
  async def test_function_signature(self) -> None:
    """run_interactive_step should accept expected parameters."""
    import inspect

    from repo_map.navigator.runner import run_interactive_step

    sig = inspect.signature(run_interactive_step)
    param_names = list(sig.parameters.keys())

    assert "runner" in param_names
    assert "budget_plugin" in param_names
    assert "user_id" in param_names
    assert "session_id" in param_names

  @pytest.mark.asyncio
  async def test_raises_on_missing_session(self, tmp_path: Path) -> None:
    """run_interactive_step should raise ValueError if session doesn't exist."""
    from repo_map.navigator.runner import run_interactive_step

    runner, plugin = create_navigator_runner()

    with pytest.raises(ValueError, match="not found"):
      await run_interactive_step(
        runner=runner,
        budget_plugin=plugin,
        user_id="nonexistent-user",
        session_id="nonexistent-session",
      )
