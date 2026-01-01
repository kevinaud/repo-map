"""Unit tests for Navigator prompt rendering."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from repo_map.core.flight_plan import FlightPlan
from repo_map.navigator.pricing import GEMINI_3_FLASH_PRICING
from repo_map.navigator.prompts import (
  DecisionEntry,
  PromptContext,
  build_prompt_context,
  render_navigator_prompt,
  transform_decision_log,
)
from repo_map.navigator.state import (
  BudgetConfig,
  DecisionLogEntry,
  MapMetadata,
  NavigatorState,
)

if TYPE_CHECKING:
  from collections.abc import Generator


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


class TestTransformDecisionLog:
  """Tests for transform_decision_log function."""

  def test_empty_log(self) -> None:
    """Test transforming empty decision log."""
    result = transform_decision_log([])
    assert result == []

  def test_single_entry_with_verbosity_add(self) -> None:
    """Test transforming single decision with verbosity add."""
    entries = [
      DecisionLogEntry(
        step=1,
        action="update_flight_plan",
        reasoning="Initial scan",
        config_patch=[
          {
            "op": "add",
            "path": "/verbosity/-",
            "value": {"pattern": "src/**", "level": 3},
          }
        ],
        timestamp=datetime.now(UTC),
      ),
    ]
    result = transform_decision_log(entries)

    assert len(result) == 1
    assert result[0].step == 1
    assert result[0].action == "update_flight_plan"
    assert result[0].reasoning == "Initial scan"
    assert "src/** → L3" in result[0].changes

  def test_budget_change(self) -> None:
    """Test transforming budget change."""
    entries = [
      DecisionLogEntry(
        step=1,
        action="update_flight_plan",
        reasoning="Increase budget",
        config_patch=[{"op": "replace", "path": "/budget", "value": 30000}],
        timestamp=datetime.now(UTC),
      ),
    ]
    result = transform_decision_log(entries)

    assert "budget → 30000" in result[0].changes

  def test_max_entries_limit(self) -> None:
    """Test that max_entries limits output."""
    entries = [
      DecisionLogEntry(
        step=i,
        action="update_flight_plan",
        reasoning=f"Decision {i}",
        config_patch=[],
        timestamp=datetime.now(UTC),
      )
      for i in range(1, 10)
    ]

    result = transform_decision_log(entries, max_entries=3)

    # Should only have steps 7, 8, 9 (last 3)
    assert len(result) == 3
    assert result[0].step == 7
    assert result[1].step == 8
    assert result[2].step == 9


class TestBuildPromptContext:
  """Tests for build_prompt_context function."""

  @pytest.fixture
  def temp_dir(self) -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
      yield tmpdir

  def test_basic_context_building(self, temp_dir: str) -> None:
    """Test basic prompt context construction."""
    state = create_test_state(temp_dir)
    ctx = build_prompt_context(state, "# Test Map")

    assert ctx.user_task == "Understand the authentication system"
    assert ctx.token_budget == 20000
    assert ctx.token_used == 5000
    assert ctx.token_utilization_pct == 25.0
    assert ctx.file_count == 42
    assert ctx.excluded_count == 10
    assert ctx.cost_used == Decimal("0.01")
    assert ctx.cost_max == Decimal("2.0")
    assert ctx.map_content == "# Test Map"

  def test_context_includes_decision_history(self, temp_dir: str) -> None:
    """Test that decision history is transformed."""
    state = create_test_state(temp_dir)
    ctx = build_prompt_context(state, "# Test Map")

    assert len(ctx.decision_history) == 1
    assert ctx.decision_history[0].step == 1
    assert "**/* → L1" in ctx.decision_history[0].changes


class TestRenderNavigatorPrompt:
  """Tests for render_navigator_prompt function."""

  def test_renders_user_task(self) -> None:
    """Test that user task is rendered."""
    ctx = PromptContext(
      user_task="Refactor the payment system",
      token_budget=20000,
      token_used=5000,
      token_utilization_pct=25.0,
      file_count=42,
      excluded_count=10,
      cost_used=Decimal("0.01"),
      cost_max=Decimal("2.0"),
      cost_utilization_pct=0.5,
      cost_remaining=Decimal("1.99"),
      decision_history=[],
      map_content="# Test Map",
    )

    result = render_navigator_prompt(ctx)

    assert "Refactor the payment system" in result

  def test_renders_budget_info(self) -> None:
    """Test that budget information is rendered."""
    ctx = PromptContext(
      user_task="Test",
      token_budget=20000,
      token_used=5000,
      token_utilization_pct=25.0,
      file_count=42,
      excluded_count=10,
      cost_used=Decimal("0.50"),
      cost_max=Decimal("2.0"),
      cost_utilization_pct=25.0,
      cost_remaining=Decimal("1.50"),
      decision_history=[],
      map_content="# Test Map",
    )

    result = render_navigator_prompt(ctx)

    assert "$0.50" in result
    assert "$2.00" in result
    assert "25.0%" in result

  def test_renders_token_budget(self) -> None:
    """Test that token budget is rendered."""
    ctx = PromptContext(
      user_task="Test",
      token_budget=20000,
      token_used=5000,
      token_utilization_pct=25.0,
      file_count=42,
      excluded_count=10,
      cost_used=Decimal("0.01"),
      cost_max=Decimal("2.0"),
      cost_utilization_pct=0.5,
      cost_remaining=Decimal("1.99"),
      decision_history=[],
      map_content="# Test Map",
    )

    result = render_navigator_prompt(ctx)

    assert "20,000" in result
    assert "5,000" in result

  def test_renders_decision_history(self) -> None:
    """Test that decision history is rendered."""
    ctx = PromptContext(
      user_task="Test",
      token_budget=20000,
      token_used=5000,
      token_utilization_pct=25.0,
      file_count=42,
      excluded_count=10,
      cost_used=Decimal("0.01"),
      cost_max=Decimal("2.0"),
      cost_utilization_pct=0.5,
      cost_remaining=Decimal("1.99"),
      decision_history=[
        DecisionEntry(
          step=1,
          action="update_flight_plan",
          reasoning="Initial scan",
          changes=["src/** → L3"],
        ),
      ],
      map_content="# Test Map",
    )

    result = render_navigator_prompt(ctx)

    assert "Step 1" in result
    assert "update flight plan" in result
    assert "Initial scan" in result
    assert "src/** → L3" in result

  def test_renders_empty_decision_history(self) -> None:
    """Test that empty decision history shows placeholder."""
    ctx = PromptContext(
      user_task="Test",
      token_budget=20000,
      token_used=5000,
      token_utilization_pct=25.0,
      file_count=42,
      excluded_count=10,
      cost_used=Decimal("0.01"),
      cost_max=Decimal("2.0"),
      cost_utilization_pct=0.5,
      cost_remaining=Decimal("1.99"),
      decision_history=[],
      map_content="# Test Map",
    )

    result = render_navigator_prompt(ctx)

    assert "(No previous decisions)" in result

  def test_renders_map_content(self) -> None:
    """Test that map content is rendered."""
    ctx = PromptContext(
      user_task="Test",
      token_budget=20000,
      token_used=5000,
      token_utilization_pct=25.0,
      file_count=42,
      excluded_count=10,
      cost_used=Decimal("0.01"),
      cost_max=Decimal("2.0"),
      cost_utilization_pct=0.5,
      cost_remaining=Decimal("1.99"),
      decision_history=[],
      map_content="# Repository Map\n## src/main.py",
    )

    result = render_navigator_prompt(ctx)

    assert "Repository Map" in result
    assert "src/main.py" in result

  def test_renders_verbosity_levels(self) -> None:
    """Test that verbosity level explanations are included."""
    ctx = PromptContext(
      user_task="Test",
      token_budget=20000,
      token_used=5000,
      token_utilization_pct=25.0,
      file_count=42,
      excluded_count=10,
      cost_used=Decimal("0.01"),
      cost_max=Decimal("2.0"),
      cost_utilization_pct=0.5,
      cost_remaining=Decimal("1.99"),
      decision_history=[],
      map_content="# Test",
    )

    result = render_navigator_prompt(ctx)

    assert "Level 0" in result
    assert "Level 4" in result
    assert "Exclude" in result
