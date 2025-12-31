"""Unit tests for FlightPlan validation and loading."""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

if TYPE_CHECKING:
  from pathlib import Path

from repo_map.core.flight_plan import (
  FlightPlan,
  SectionVerbosity,
  VerbosityRule,
  format_validation_errors,
)
from repo_map.core.verbosity import VerbosityLevel


class TestVerbosityLevel:
  """Test VerbosityLevel enum."""

  def test_values(self):
    """Test verbosity level values."""
    assert VerbosityLevel.EXCLUDE == 0
    assert VerbosityLevel.EXISTENCE == 1
    assert VerbosityLevel.STRUCTURE == 2
    assert VerbosityLevel.INTERFACE == 3
    assert VerbosityLevel.IMPLEMENTATION == 4

  def test_from_int(self):
    """Test creating VerbosityLevel from integer."""
    assert VerbosityLevel.from_int(0) == VerbosityLevel.EXCLUDE
    assert VerbosityLevel.from_int(4) == VerbosityLevel.IMPLEMENTATION

  def test_from_int_invalid(self):
    """Test from_int with invalid values."""
    with pytest.raises(ValueError, match="must be 0-4"):
      VerbosityLevel.from_int(-1)
    with pytest.raises(ValueError, match="must be 0-4"):
      VerbosityLevel.from_int(5)


class TestFlightPlanBasic:
  """Test basic FlightPlan functionality."""

  def test_default_values(self):
    """Test FlightPlan default values."""
    plan = FlightPlan(budget=20000)
    assert plan.budget == 20000
    assert plan.focus is None
    assert plan.verbosity == []
    assert plan.custom_queries == []

  def test_from_yaml_minimal(self):
    """Test loading minimal YAML."""
    yaml = "budget: 5000"
    plan = FlightPlan.from_yaml(yaml)
    assert plan.budget == 5000

  def test_from_yaml_empty(self):
    """Test loading empty YAML uses defaults."""
    plan = FlightPlan.from_yaml("")
    assert plan.budget == 20000

  def test_from_yaml_with_focus(self):
    """Test loading YAML with focus configuration."""
    yaml = dedent("""
      budget: 10000
      focus:
        paths:
          - pattern: "src/core/**"
            weight: 10.0
        symbols:
          - name: "authenticate"
            weight: 15.0
    """)
    plan = FlightPlan.from_yaml(yaml)
    assert plan.budget == 10000
    assert plan.focus is not None
    assert len(plan.focus.paths) == 1
    assert plan.focus.paths[0].pattern == "src/core/**"
    assert len(plan.focus.symbols) == 1
    assert plan.focus.symbols[0].name == "authenticate"

  def test_from_yaml_with_verbosity(self):
    """Test loading YAML with verbosity rules."""
    yaml = dedent("""
      budget: 15000
      verbosity:
        - pattern: "src/**/*.py"
          level: 3
        - pattern: "tests/**"
          level: 1
    """)
    plan = FlightPlan.from_yaml(yaml)
    assert len(plan.verbosity) == 2
    assert plan.verbosity[0].pattern == "src/**/*.py"
    assert plan.verbosity[0].level == 3
    assert plan.verbosity[1].level == 1


class TestFlightPlanValidation:
  """Test FlightPlan validation errors."""

  def test_invalid_budget_zero(self):
    """Test that budget=0 is rejected."""
    with pytest.raises(ValidationError) as exc:
      FlightPlan.from_yaml("budget: 0")
    assert "budget" in str(exc.value)

  def test_invalid_budget_negative(self):
    """Test that negative budget is rejected."""
    with pytest.raises(ValidationError):
      FlightPlan.from_yaml("budget: -100")

  def test_invalid_yaml_syntax(self):
    """Test that invalid YAML syntax raises ValueError."""
    with pytest.raises(ValueError, match="Invalid YAML"):
      FlightPlan.from_yaml("budget: [invalid")

  def test_extra_fields_rejected(self):
    """Test that unknown fields are rejected."""
    with pytest.raises(ValidationError) as exc:
      FlightPlan.from_yaml("unknown_field: value")
    assert "Extra inputs" in str(exc.value)

  def test_verbosity_rule_needs_level_or_sections(self):
    """Test VerbosityRule requires level or sections."""
    yaml = dedent("""
      verbosity:
        - pattern: "src/**"
    """)
    with pytest.raises(ValidationError) as exc:
      FlightPlan.from_yaml(yaml)
    assert "Either 'level' or 'sections' must be specified" in str(exc.value)

  def test_verbosity_rule_cannot_have_both(self):
    """Test VerbosityRule cannot have both level and sections."""
    yaml = dedent("""
      verbosity:
        - pattern: "src/**"
          level: 3
          sections:
            - pattern: "*"
              level: 2
    """)
    with pytest.raises(ValidationError) as exc:
      FlightPlan.from_yaml(yaml)
    assert "Cannot specify both" in str(exc.value)

  def test_verbosity_level_range(self):
    """Test verbosity level must be 0-4."""
    yaml = dedent("""
      verbosity:
        - pattern: "src/**"
          level: 5
    """)
    with pytest.raises(ValidationError):
      FlightPlan.from_yaml(yaml)

  def test_empty_pattern_rejected(self):
    """Test that empty pattern is rejected."""
    yaml = dedent("""
      verbosity:
        - pattern: ""
          level: 3
    """)
    with pytest.raises(ValidationError) as exc:
      FlightPlan.from_yaml(yaml)
    assert "String should have at least 1 character" in str(exc.value)

  def test_path_boost_zero_weight(self):
    """Test that zero weight is rejected."""
    yaml = dedent("""
      focus:
        paths:
          - pattern: "src/**"
            weight: 0
    """)
    with pytest.raises(ValidationError):
      FlightPlan.from_yaml(yaml)


class TestFlightPlanVerbosityMatching:
  """Test verbosity rule matching."""

  def test_get_verbosity_for_path_no_rules(self):
    """Test default verbosity when no rules match."""
    plan = FlightPlan(budget=10000)
    level = plan.get_verbosity_for_path("src/main.py")
    assert level == VerbosityLevel.IMPLEMENTATION

  def test_get_verbosity_for_path_single_match(self):
    """Test verbosity with single matching rule."""
    plan = FlightPlan(
      budget=10000, verbosity=[VerbosityRule(pattern="src/**/*.py", level=3)]
    )
    level = plan.get_verbosity_for_path("src/core/auth.py")
    assert level == VerbosityLevel.INTERFACE

  def test_get_verbosity_for_path_last_match_wins(self):
    """Test that last matching rule wins."""
    plan = FlightPlan(
      budget=10000,
      verbosity=[
        VerbosityRule(pattern="**/*.py", level=2),
        VerbosityRule(pattern="src/**", level=4),
      ],
    )
    # Both match, but src/** is last
    level = plan.get_verbosity_for_path("src/main.py")
    assert level == VerbosityLevel.IMPLEMENTATION

  def test_get_verbosity_for_path_no_match(self):
    """Test default when no rule matches."""
    plan = FlightPlan(
      budget=10000, verbosity=[VerbosityRule(pattern="tests/**", level=1)]
    )
    level = plan.get_verbosity_for_path("src/main.py")
    assert level == VerbosityLevel.IMPLEMENTATION

  def test_get_section_rules_for_path(self):
    """Test getting section-level rules."""
    plan = FlightPlan(
      budget=10000,
      verbosity=[
        VerbosityRule(
          pattern="docs/api.md",
          sections=[
            SectionVerbosity(pattern="API*", level=4),
            SectionVerbosity(pattern="*", level=2),
          ],
        )
      ],
    )
    rules = plan.get_section_rules_for_path("docs/api.md")
    assert rules is not None
    assert len(rules) == 2

  def test_get_section_rules_returns_none(self):
    """Test that section rules return None when only level specified."""
    plan = FlightPlan(
      budget=10000, verbosity=[VerbosityRule(pattern="src/**", level=3)]
    )
    rules = plan.get_section_rules_for_path("src/main.py")
    assert rules is None


class TestFlightPlanFileLoading:
  """Test loading FlightPlan from files."""

  def test_from_yaml_file(self, tmp_path: Path):
    """Test loading from file."""
    config_file = tmp_path / "flight-plan.yaml"
    config_file.write_text("budget: 8000")

    plan = FlightPlan.from_yaml_file(config_file)
    assert plan.budget == 8000

  def test_from_yaml_file_not_found(self, tmp_path: Path):
    """Test FileNotFoundError when file missing."""
    with pytest.raises(FileNotFoundError):
      FlightPlan.from_yaml_file(tmp_path / "missing.yaml")


class TestFormatValidationErrors:
  """Test error formatting helper."""

  def test_format_single_error(self):
    """Test formatting a single error."""
    errors = [{"loc": ("budget",), "msg": "Input should be greater than 0"}]
    result = format_validation_errors(errors)
    assert "budget" in result
    assert "greater than 0" in result

  def test_format_nested_error(self):
    """Test formatting nested location error."""
    errors = [{"loc": ("verbosity", 0, "level"), "msg": "Invalid value"}]
    result = format_validation_errors(errors)
    assert "verbosity.0.level" in result


class TestToYaml:
  """Test FlightPlan serialization."""

  def test_to_yaml_minimal(self):
    """Test serializing minimal plan."""
    plan = FlightPlan(budget=5000)
    yaml = plan.to_yaml()
    assert "budget: 5000" in yaml

  def test_to_yaml_roundtrip(self):
    """Test roundtrip YAML serialization."""
    original = FlightPlan(
      budget=10000,
      verbosity=[VerbosityRule(pattern="src/**", level=3)],
    )
    yaml = original.to_yaml()
    restored = FlightPlan.from_yaml(yaml)
    assert restored.budget == original.budget
    assert len(restored.verbosity) == len(original.verbosity)
