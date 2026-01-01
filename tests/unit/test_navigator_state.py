"""Unit tests for Navigator state models.

Tests the Pydantic models that represent navigator state: BudgetConfig,
DecisionLogEntry, MapMetadata, NavigatorState, TurnReport, and NavigatorOutput.
Focuses on validation rules, computed properties, and serialization behavior.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from collections.abc import Generator

import pytest

from repo_map.core.flight_plan import FlightPlan
from repo_map.navigator.pricing import GEMINI_3_FLASH_PRICING
from repo_map.navigator.state import (
  BudgetConfig,
  DecisionLogEntry,
  MapMetadata,
  NavigatorOutput,
  NavigatorState,
  TurnReport,
)


class TestBudgetConfig:
  """Tests for BudgetConfig model."""

  def test_default_values(self) -> None:
    """Test default budget configuration."""
    config = BudgetConfig(model_pricing=GEMINI_3_FLASH_PRICING)
    assert config.max_spend_usd == Decimal("0.50")
    assert config.current_spend_usd == Decimal("0.0")
    assert config.model_pricing == GEMINI_3_FLASH_PRICING

  def test_remaining_budget(self) -> None:
    """Test remaining budget calculation."""
    config = BudgetConfig(
      max_spend_usd=Decimal("5.0"),
      current_spend_usd=Decimal("1.5"),
      model_pricing=GEMINI_3_FLASH_PRICING,
    )
    assert config.remaining_budget == Decimal("3.5")

  def test_budget_utilization_pct(self) -> None:
    """Test budget utilization percentage."""
    config = BudgetConfig(
      max_spend_usd=Decimal("10.0"),
      current_spend_usd=Decimal("2.5"),
      model_pricing=GEMINI_3_FLASH_PRICING,
    )
    assert config.budget_utilization_pct == 25.0

  def test_validation_max_spend_positive(self) -> None:
    """Test that max_spend_usd must be positive."""
    with pytest.raises(ValueError, match="greater than 0"):
      BudgetConfig(max_spend_usd=Decimal(0), model_pricing=GEMINI_3_FLASH_PRICING)

  def test_validation_current_spend_non_negative(self) -> None:
    """Test that current_spend_usd cannot be negative."""
    with pytest.raises(ValueError, match="greater than or equal to 0"):
      BudgetConfig(current_spend_usd=Decimal(-1), model_pricing=GEMINI_3_FLASH_PRICING)


class TestDecisionLogEntry:
  """Tests for DecisionLogEntry model."""

  def test_valid_entry(self) -> None:
    """Test creating a valid decision log entry."""
    expected_patch = [
      {
        "op": "add",
        "path": "/verbosity/0",
        "value": {"pattern": "src/auth/**", "level": 4},
      }
    ]
    entry = DecisionLogEntry(
      step=1,
      action="update_flight_plan",
      reasoning="Increasing verbosity on auth files",
      config_patch=expected_patch,
    )
    assert entry.step == 1
    assert entry.action == "update_flight_plan"
    assert entry.reasoning == "Increasing verbosity on auth files"
    assert entry.config_patch == expected_patch
    assert isinstance(entry.timestamp, datetime)

  def test_create_patch_static_method(self) -> None:
    """Test creating RFC 6902 JSON Patch from two flight plans."""
    old_plan = FlightPlan(budget=10000)
    new_plan = FlightPlan(budget=20000)

    patch = DecisionLogEntry.create_patch(old_plan, new_plan)

    # Should contain a replace operation for budget
    assert len(patch) >= 1
    budget_op = next((op for op in patch if op["path"] == "/budget"), None)
    assert budget_op is not None
    assert budget_op["op"] == "replace"
    assert budget_op["value"] == 20000

  def test_step_must_be_positive(self) -> None:
    """Test that step must be greater than 0."""
    with pytest.raises(ValueError, match="greater than 0"):
      DecisionLogEntry(step=0, action="update_flight_plan", reasoning="test")

  def test_reasoning_non_empty(self) -> None:
    """Test that reasoning cannot be empty."""
    with pytest.raises(ValueError, match="at least 1 character"):
      DecisionLogEntry(step=1, action="update_flight_plan", reasoning="")

  def test_invalid_action(self) -> None:
    """Test that action must be valid literal."""
    with pytest.raises(ValueError, match="Input should be"):
      DecisionLogEntry(step=1, action="invalid_action", reasoning="test")  # type: ignore


class TestMapMetadata:
  """Tests for MapMetadata model."""

  def test_default_values(self) -> None:
    """Test default metadata values."""
    metadata = MapMetadata()
    assert metadata.total_tokens == 0
    assert metadata.file_count == 0
    assert metadata.focus_areas == []
    assert metadata.excluded_count == 0
    assert metadata.budget_utilization == 0.0

  def test_with_values(self) -> None:
    """Test metadata with explicit values."""
    metadata = MapMetadata(
      total_tokens=15000,
      file_count=42,
      focus_areas=["src/auth/", "src/middleware/"],
      excluded_count=100,
      budget_utilization=75.0,
    )
    assert metadata.total_tokens == 15000
    assert metadata.file_count == 42
    assert metadata.focus_areas == ["src/auth/", "src/middleware/"]
    assert metadata.excluded_count == 100
    assert metadata.budget_utilization == 75.0

  def test_budget_utilization_bounds(self) -> None:
    """Test that budget_utilization is bounded 0-100."""
    with pytest.raises(ValueError, match="less than or equal to 100"):
      MapMetadata(budget_utilization=101.0)


class TestNavigatorState:
  """Tests for NavigatorState model."""

  @pytest.fixture
  def valid_repo_path(self) -> Generator[str, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
      yield tmpdir

  def test_valid_state(self, valid_repo_path: str) -> None:
    """Test creating a valid navigator state."""
    state = NavigatorState(
      user_task="Understand the authentication system",
      repo_path=valid_repo_path,
      budget_config=BudgetConfig(model_pricing=GEMINI_3_FLASH_PRICING),
      flight_plan=FlightPlan(budget=20000),
    )
    assert state.user_task == "Understand the authentication system"
    assert state.repo_path == valid_repo_path
    assert state.execution_mode == "autonomous"
    assert state.decision_log == []
    assert state.exploration_complete is False

  def test_user_task_non_empty(self, valid_repo_path: str) -> None:
    """Test that user_task cannot be empty."""
    with pytest.raises(ValueError, match="at least 1 character"):
      NavigatorState(
        user_task="",
        repo_path=valid_repo_path,
        budget_config=BudgetConfig(model_pricing=GEMINI_3_FLASH_PRICING),
        flight_plan=FlightPlan(budget=20000),
      )

  def test_repo_path_must_exist(self) -> None:
    """Test that repo_path must be an existing directory."""
    with pytest.raises(ValueError, match="Repository path does not exist"):
      NavigatorState(
        user_task="Test task",
        repo_path="/nonexistent/path/that/does/not/exist",
        budget_config=BudgetConfig(model_pricing=GEMINI_3_FLASH_PRICING),
        flight_plan=FlightPlan(budget=20000),
      )

  def test_execution_modes(self, valid_repo_path: str) -> None:
    """Test both execution modes."""
    for mode in ["autonomous", "interactive"]:
      state = NavigatorState(
        user_task="Test task",
        repo_path=valid_repo_path,
        execution_mode=mode,  # type: ignore
        budget_config=BudgetConfig(model_pricing=GEMINI_3_FLASH_PRICING),
        flight_plan=FlightPlan(budget=20000),
      )
      assert state.execution_mode == mode

  def test_serialization_roundtrip(self, valid_repo_path: str) -> None:
    """Test that state can be serialized and deserialized."""
    original = NavigatorState(
      user_task="Test task",
      repo_path=valid_repo_path,
      budget_config=BudgetConfig(
        max_spend_usd=Decimal("5.0"),
        current_spend_usd=Decimal("1.0"),
        model_pricing=GEMINI_3_FLASH_PRICING,
      ),
      flight_plan=FlightPlan(budget=10000),
      decision_log=[
        DecisionLogEntry(
          step=1,
          action="update_flight_plan",
          reasoning="Initial scan",
        )
      ],
    )

    # Serialize to dict (as stored in session.state)
    serialized = original.model_dump(mode="json")

    # Deserialize back
    restored = NavigatorState.model_validate(serialized)

    assert restored.user_task == original.user_task
    assert restored.budget_config.max_spend_usd == original.budget_config.max_spend_usd
    assert len(restored.decision_log) == 1
    assert restored.decision_log[0].reasoning == "Initial scan"


class TestTurnReport:
  """Tests for TurnReport dataclass."""

  def test_turn_report_creation(self) -> None:
    """Test creating a turn report."""
    report = TurnReport(
      step_number=3,
      cost_this_turn=0.0015,
      total_cost=0.0045,
      map_size_tokens=15000,
      budget_remaining=1.9955,
      focus_areas=["src/auth/"],
      last_action="update_flight_plan",
      reasoning="Zooming in on auth directory",
    )
    assert report.step_number == 3
    assert report.cost_this_turn == 0.0015
    assert report.total_cost == 0.0045
    assert report.map_size_tokens == 15000
    assert report.budget_remaining == 1.9955
    assert report.focus_areas == ["src/auth/"]


class TestNavigatorOutput:
  """Tests for NavigatorOutput dataclass."""

  def test_navigator_output_creation(self) -> None:
    """Test creating navigator output."""
    output = NavigatorOutput(
      context_string="# Repository Map\n...",
      flight_plan_yaml="budget: 20000\n",
      reasoning_summary="Focused on auth and middleware",
      total_iterations=5,
      total_cost=0.0075,
      token_count=18500,
    )
    assert output.context_string == "# Repository Map\n..."
    assert output.flight_plan_yaml == "budget: 20000\n"
    assert output.reasoning_summary == "Focused on auth and middleware"
    assert output.total_iterations == 5
    assert output.total_cost == 0.0075
    assert output.token_count == 18500
