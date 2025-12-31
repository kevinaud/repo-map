"""Unit tests for ContextRenderer."""

from __future__ import annotations

import pytest

from repo_map.core.flight_plan import FlightPlan, SectionVerbosity, VerbosityRule
from repo_map.core.renderer import ContextRenderer, match_verbosity_rules
from repo_map.core.verbosity import VerbosityLevel


class TestMatchVerbosityRules:
  """Tests for match_verbosity_rules function."""

  def test_no_rules_returns_default(self) -> None:
    """Empty rules should return default level."""
    level, sections = match_verbosity_rules("src/app.py", [], VerbosityLevel.STRUCTURE)
    assert level == VerbosityLevel.STRUCTURE
    assert sections is None

  def test_matching_rule_returns_level(self) -> None:
    """Matching rule should return its level."""
    rules = [
      VerbosityRule(pattern="src/**/*.py", level=3),  # INTERFACE
    ]
    level, _ = match_verbosity_rules("src/app.py", rules)
    assert level == VerbosityLevel.INTERFACE

  def test_non_matching_rule_returns_default(self) -> None:
    """Non-matching rule should return default."""
    rules = [
      VerbosityRule(pattern="tests/**/*.py", level=4),  # IMPLEMENTATION
    ]
    level, _ = match_verbosity_rules("src/app.py", rules, VerbosityLevel.STRUCTURE)
    assert level == VerbosityLevel.STRUCTURE

  def test_last_match_wins(self) -> None:
    """When multiple rules match, last one wins."""
    rules = [
      VerbosityRule(pattern="**/*.py", level=1),  # EXISTENCE
      VerbosityRule(pattern="src/**/*.py", level=3),  # INTERFACE
      VerbosityRule(pattern="src/core/**", level=4),  # IMPLEMENTATION
    ]
    level, _ = match_verbosity_rules("src/core/engine.py", rules)
    assert level == VerbosityLevel.IMPLEMENTATION

  def test_section_rules_returned(self) -> None:
    """Section rules should be returned when present."""
    section_rules = [
      SectionVerbosity(pattern="__init__", level=0),  # EXCLUDE
    ]
    rules = [
      VerbosityRule(pattern="**/*.py", sections=section_rules),
    ]
    level, sections = match_verbosity_rules("app.py", rules)
    # Default level when only sections specified
    assert level == VerbosityLevel.STRUCTURE
    assert sections is not None
    assert len(sections) == 1
    assert sections[0].pattern == "__init__"


class TestContextRenderer:
  """Tests for ContextRenderer class."""

  def test_default_verbosity(self) -> None:
    """Without FlightPlan, should use default verbosity."""
    renderer = ContextRenderer(default_verbosity=VerbosityLevel.INTERFACE)
    level = renderer.get_verbosity_for_path("any/path.py")
    assert level == VerbosityLevel.INTERFACE

  def test_flight_plan_verbosity_rules(self) -> None:
    """FlightPlan rules should determine verbosity."""
    flight_plan = FlightPlan(
      budget=10000,
      verbosity=[
        VerbosityRule(pattern="tests/**", level=0),  # EXCLUDE
        VerbosityRule(pattern="src/**", level=4),  # IMPLEMENTATION
      ],
    )
    renderer = ContextRenderer(flight_plan=flight_plan)

    test_verbosity = renderer.get_verbosity_for_path("tests/test_app.py")
    assert test_verbosity == VerbosityLevel.EXCLUDE
    src_verbosity = renderer.get_verbosity_for_path("src/main.py")
    assert src_verbosity == VerbosityLevel.IMPLEMENTATION

  def test_get_section_verbosity_no_rules(self) -> None:
    """Without section rules, should return file verbosity."""
    renderer = ContextRenderer()
    level = renderer.get_section_verbosity("Calculator", None, VerbosityLevel.INTERFACE)
    assert level == VerbosityLevel.INTERFACE

  def test_get_section_verbosity_matching_rule(self) -> None:
    """Matching section rule should override file verbosity."""
    renderer = ContextRenderer()
    section_rules = [
      SectionVerbosity(pattern="*Test*", level=4),  # IMPLEMENTATION
      SectionVerbosity(pattern="__*__", level=0),  # EXCLUDE
    ]
    level = renderer.get_section_verbosity(
      "TestCalculator", section_rules, VerbosityLevel.STRUCTURE
    )
    assert level == VerbosityLevel.IMPLEMENTATION

  def test_get_section_verbosity_wildcard_patterns(self) -> None:
    """Section rules should support wildcard patterns."""
    renderer = ContextRenderer()
    section_rules = [
      SectionVerbosity(pattern="test_*", level=0),  # EXCLUDE
    ]
    # Matches
    level = renderer.get_section_verbosity(
      "test_something", section_rules, VerbosityLevel.INTERFACE
    )
    assert level == VerbosityLevel.EXCLUDE

    # Doesn't match
    level = renderer.get_section_verbosity(
      "main", section_rules, VerbosityLevel.INTERFACE
    )
    assert level == VerbosityLevel.INTERFACE


class TestContextRendererRenderFile:
  """Tests for ContextRenderer.render_file_at_level method."""

  @pytest.fixture
  def sample_python_code(self) -> str:
    """Sample Python code."""
    return '''class Calculator:
    """A calculator."""

    def add(self, a, b):
        return a + b

def main():
    calc = Calculator()
'''

  def test_exclude_returns_empty(self, sample_python_code: str) -> None:
    """EXCLUDE level should return empty string."""
    renderer = ContextRenderer()
    result = renderer.render_file_at_level(
      "calc.py", sample_python_code, VerbosityLevel.EXCLUDE
    )
    assert result == ""

  def test_existence_returns_empty(self, sample_python_code: str) -> None:
    """EXISTENCE level should return empty (path handled externally)."""
    renderer = ContextRenderer()
    result = renderer.render_file_at_level(
      "calc.py", sample_python_code, VerbosityLevel.EXISTENCE
    )
    assert result == ""

  def test_implementation_returns_full_content(self, sample_python_code: str) -> None:
    """IMPLEMENTATION level should return full content."""
    renderer = ContextRenderer()
    result = renderer.render_file_at_level(
      "calc.py", sample_python_code, VerbosityLevel.IMPLEMENTATION
    )
    assert result == sample_python_code

  def test_structure_extracts_definitions(self, sample_python_code: str) -> None:
    """STRUCTURE level should extract definition lines."""
    renderer = ContextRenderer()
    result = renderer.render_file_at_level(
      "calc.py", sample_python_code, VerbosityLevel.STRUCTURE
    )
    # Should contain class and function names
    assert "class Calculator" in result or "Calculator" in result
    assert "def" in result or "main" in result or "add" in result


class TestContextRendererCalculateCosts:
  """Tests for ContextRenderer.calculate_file_costs method."""

  def test_exclude_cost_is_zero(self) -> None:
    """EXCLUDE level should have 0 cost."""
    renderer = ContextRenderer()
    costs = renderer.calculate_file_costs("test.py", "content here")
    assert costs[VerbosityLevel.EXCLUDE] == 0

  def test_existence_cost_is_path_only(self) -> None:
    """EXISTENCE level cost should be based on path."""
    renderer = ContextRenderer()
    costs = renderer.calculate_file_costs("test.py", "x" * 1000)
    # Path "test.py" should have low cost
    assert costs[VerbosityLevel.EXISTENCE] < 10

  def test_implementation_cost_is_full_content(self) -> None:
    """IMPLEMENTATION level cost should be based on full content."""
    content = "x" * 400  # 400 chars ~= 100 tokens
    renderer = ContextRenderer()
    costs = renderer.calculate_file_costs("test.py", content)
    assert costs[VerbosityLevel.IMPLEMENTATION] >= 90
    assert costs[VerbosityLevel.IMPLEMENTATION] <= 110

  def test_costs_increase_with_verbosity(self) -> None:
    """Higher verbosity levels should generally have higher costs."""
    content = '''class Foo:
    """Docstring."""
    def bar(self):
        return 1
'''
    renderer = ContextRenderer()
    costs = renderer.calculate_file_costs("test.py", content)

    # EXCLUDE should be lowest
    assert costs[VerbosityLevel.EXCLUDE] == 0
    # IMPLEMENTATION should be highest (or equal to interface for small files)
    assert costs[VerbosityLevel.IMPLEMENTATION] >= costs[VerbosityLevel.EXISTENCE]


class TestContextRendererRender:
  """Tests for ContextRenderer.render method."""

  def test_empty_files_list(self) -> None:
    """Empty files list should return budget summary only."""
    renderer = ContextRenderer()
    result = renderer.render([])
    assert "Total:" in result
    assert "0/" in result

  def test_exclude_files_not_rendered(self) -> None:
    """EXCLUDE files should not appear in output."""
    flight_plan = FlightPlan(
      budget=20000,
      verbosity=[
        VerbosityRule(pattern="*.log", level=0),  # EXCLUDE
      ],
    )
    renderer = ContextRenderer(flight_plan=flight_plan)
    result = renderer.render([("app.log", "log content")])
    assert "app.log" not in result.split("\n# Total:")[0]

  def test_existence_shows_path_only(self) -> None:
    """EXISTENCE level should show path only annotation."""
    flight_plan = FlightPlan(
      budget=20000,
      verbosity=[
        VerbosityRule(pattern="*.txt", level=1),  # EXISTENCE
      ],
    )
    renderer = ContextRenderer(flight_plan=flight_plan)
    result = renderer.render([("readme.txt", "some content")])
    assert "readme.txt" in result
    assert "path only" in result

  def test_show_costs_includes_annotations(self) -> None:
    """show_costs=True should include cost annotations."""
    renderer = ContextRenderer()
    result = renderer.render([("test.py", "content")], show_costs=True)
    assert "Costs:" in result
    assert "L0=" in result
    assert "L4=" in result

  def test_strict_mode_raises_on_budget_exceeded(self) -> None:
    """strict=True should raise when budget exceeded."""
    flight_plan = FlightPlan(budget=10)  # Very small budget
    renderer = ContextRenderer(flight_plan=flight_plan)

    with pytest.raises(ValueError, match="Budget exceeded"):
      renderer.render(
        [("big_file.py", "x" * 1000)],  # ~250 tokens
        strict=True,
      )

  def test_budget_warning_in_output(self) -> None:
    """Over budget should show warning in output."""
    flight_plan = FlightPlan(budget=10)
    renderer = ContextRenderer(flight_plan=flight_plan)
    result = renderer.render([("file.py", "x" * 100)])
    assert "OVER BUDGET" in result
