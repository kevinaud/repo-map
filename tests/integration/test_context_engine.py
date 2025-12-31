"""Integration tests for Context Engine multi-resolution rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from repo_map.core.flight_plan import FlightPlan, VerbosityRule
from repo_map.core.renderer import ContextRenderer
from repo_map.core.verbosity import VerbosityLevel
from repo_map.mapper import generate_repomap

if TYPE_CHECKING:
  from pathlib import Path


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
  """Create a sample repository for integration tests."""
  # Create src directory
  src = tmp_path / "src"
  src.mkdir()

  # Create Python files
  (src / "main.py").write_text('''"""Main entry point."""

class Application:
    """The main application class."""

    def __init__(self, config: dict) -> None:
        """Initialize with config."""
        self.config = config

    def run(self) -> None:
        """Run the application."""
        print("Running...")


def main():
    """Entry point function."""
    app = Application({"debug": True})
    app.run()
''')

  (src / "utils.py").write_text('''"""Utility functions."""

def helper(value: int) -> int:
    """Double a value."""
    return value * 2


def format_output(text: str) -> str:
    """Format text for output."""
    return f"Output: {text}"
''')

  # Create docs directory
  docs = tmp_path / "docs"
  docs.mkdir()

  (docs / "README.md").write_text("""# Project Documentation

## Getting Started

This is the getting started guide.

## API Reference

See the API documentation.

## Examples

Some example code here.
""")

  # Create tests directory
  tests = tmp_path / "tests"
  tests.mkdir()

  (tests / "test_main.py").write_text('''"""Tests for main module."""

import pytest


def test_app_init():
    """Test application initialization."""
    pass


def test_app_run():
    """Test application run."""
    pass
''')

  return tmp_path


@pytest.mark.integration
class TestVerbosityLevels:
  """Integration tests for verbosity level rendering (US1)."""

  def test_exclude_level_omits_files(self, sample_repo: Path) -> None:
    """Files with EXCLUDE verbosity should not appear in output."""
    # NOTE: Last matching rule wins, so tests/** must come AFTER **/*.py
    flight_plan = FlightPlan(
      budget=10000,
      verbosity=[
        VerbosityRule(pattern="**/*.py", level=2),  # STRUCTURE
        VerbosityRule(pattern="tests/**", level=0),  # EXCLUDE tests (last wins)
      ],
    )

    result = generate_repomap(
      root_dir=sample_repo,
      flight_plan=flight_plan,
    )

    assert result is not None
    # Tests directory should be excluded
    assert "test_main.py" not in result.content
    # Src files should be included
    assert "main.py" in result.content

  def test_existence_level_shows_path_only(self, sample_repo: Path) -> None:
    """Files with EXISTENCE verbosity should show path only."""
    flight_plan = FlightPlan(
      budget=10000,
      verbosity=[
        VerbosityRule(pattern="docs/**", level=1),  # EXISTENCE
      ],
    )

    result = generate_repomap(
      root_dir=sample_repo,
      flight_plan=flight_plan,
    )

    assert result is not None
    assert "README.md" in result.content
    assert "path only" in result.content

  def test_structure_level_extracts_definitions(self, sample_repo: Path) -> None:
    """Files with STRUCTURE verbosity should show definition names."""
    flight_plan = FlightPlan(
      budget=10000,
      verbosity=[
        VerbosityRule(pattern="**/*.py", level=2),  # STRUCTURE
      ],
    )

    result = generate_repomap(
      root_dir=sample_repo,
      flight_plan=flight_plan,
    )

    assert result is not None
    # Should contain class/function definitions
    assert "Application" in result.content or "class" in result.content

  def test_implementation_level_shows_full_content(self, sample_repo: Path) -> None:
    """Files with IMPLEMENTATION verbosity should show full content."""
    flight_plan = FlightPlan(
      budget=10000,
      verbosity=[
        VerbosityRule(pattern="src/utils.py", level=4),  # IMPLEMENTATION
      ],
    )

    result = generate_repomap(
      root_dir=sample_repo,
      flight_plan=flight_plan,
    )

    assert result is not None
    # Should contain full implementation
    assert "return value * 2" in result.content

  def test_multiple_verbosity_rules(self, sample_repo: Path) -> None:
    """Multiple verbosity rules should work correctly."""
    flight_plan = FlightPlan(
      budget=10000,
      verbosity=[
        VerbosityRule(pattern="**/*.py", level=2),  # STRUCTURE default
        VerbosityRule(pattern="src/main.py", level=4),  # IMPLEMENTATION
        VerbosityRule(pattern="tests/**", level=0),  # EXCLUDE tests
      ],
    )

    result = generate_repomap(
      root_dir=sample_repo,
      flight_plan=flight_plan,
    )

    assert result is not None
    # main.py should have full content
    assert "Running..." in result.content
    # tests should be excluded
    assert "test_app_init" not in result.content


@pytest.mark.integration
class TestMarkdownVerbosity:
  """Integration tests for markdown verbosity levels (US3)."""

  def test_markdown_structure_level(self, sample_repo: Path) -> None:
    """STRUCTURE level should show heading outline."""
    flight_plan = FlightPlan(
      budget=10000,
      verbosity=[
        VerbosityRule(pattern="**/*.md", level=2),  # STRUCTURE
      ],
    )

    result = generate_repomap(
      root_dir=sample_repo,
      flight_plan=flight_plan,
    )

    assert result is not None
    # Should contain markdown file
    assert "README.md" in result.content

  def test_markdown_implementation_level(self, sample_repo: Path) -> None:
    """IMPLEMENTATION level should show full markdown content."""
    flight_plan = FlightPlan(
      budget=10000,
      verbosity=[
        VerbosityRule(pattern="**/*.md", level=4),  # IMPLEMENTATION
      ],
    )

    result = generate_repomap(
      root_dir=sample_repo,
      flight_plan=flight_plan,
    )

    assert result is not None
    # Should contain full content including paragraph text
    assert "Getting Started" in result.content
    assert "getting started guide" in result.content

  def test_markdown_exclude_level(self, sample_repo: Path) -> None:
    """EXCLUDE level should omit markdown files."""
    flight_plan = FlightPlan(
      budget=10000,
      verbosity=[
        VerbosityRule(pattern="**/*.md", level=0),  # EXCLUDE
        VerbosityRule(pattern="**/*.py", level=2),
      ],
    )

    result = generate_repomap(
      root_dir=sample_repo,
      flight_plan=flight_plan,
    )

    assert result is not None
    # README.md heading should not appear
    assert "Project Documentation" not in result.content


@pytest.mark.integration
class TestCostPrediction:
  """Integration tests for cost prediction (US2)."""

  def test_show_costs_includes_annotations(self, sample_repo: Path) -> None:
    """--show-costs should include cost annotations."""
    flight_plan = FlightPlan(
      budget=10000,
      verbosity=[
        VerbosityRule(pattern="**/*.py", level=2),
      ],
    )

    result = generate_repomap(
      root_dir=sample_repo,
      flight_plan=flight_plan,
      show_costs=True,
    )

    assert result is not None
    assert "Costs:" in result.content
    assert "L0=" in result.content
    assert "L4=" in result.content

  def test_budget_warning_when_exceeded(self, sample_repo: Path) -> None:
    """Output should warn when budget is exceeded."""
    flight_plan = FlightPlan(
      budget=50,  # Very small budget
      verbosity=[
        VerbosityRule(pattern="**/*.py", level=4),  # Full content
      ],
    )

    result = generate_repomap(
      root_dir=sample_repo,
      flight_plan=flight_plan,
    )

    assert result is not None
    assert "OVER BUDGET" in result.content

  def test_strict_mode_raises_on_budget_exceeded(self, sample_repo: Path) -> None:
    """strict=True should raise error when budget exceeded."""
    flight_plan = FlightPlan(
      budget=10,  # Very small budget
      verbosity=[
        VerbosityRule(pattern="**/*.py", level=4),
      ],
    )

    with pytest.raises(ValueError, match="Budget exceeded"):
      generate_repomap(
        root_dir=sample_repo,
        flight_plan=flight_plan,
        strict=True,
      )

  def test_budget_summary_in_output(self, sample_repo: Path) -> None:
    """Output should include budget summary."""
    flight_plan = FlightPlan(
      budget=10000,
      verbosity=[
        VerbosityRule(pattern="**/*.py", level=2),
      ],
    )

    result = generate_repomap(
      root_dir=sample_repo,
      flight_plan=flight_plan,
    )

    assert result is not None
    assert "Total:" in result.content
    assert "/10000" in result.content


@pytest.mark.integration
class TestContextRendererDirectly:
  """Integration tests for ContextRenderer class."""

  def test_render_multiple_files(self) -> None:
    """ContextRenderer should render multiple files correctly."""
    flight_plan = FlightPlan(
      budget=5000,
      verbosity=[
        VerbosityRule(pattern="*.py", level=2),
        VerbosityRule(pattern="*.md", level=3),
      ],
    )

    renderer = ContextRenderer(flight_plan=flight_plan)

    files = [
      ("app.py", "class Foo:\n  pass\n"),
      ("readme.md", "# Title\n\nSome content.\n"),
    ]

    result = renderer.render(files)

    assert "app.py" in result
    assert "readme.md" in result
    assert "Total:" in result

  def test_verbosity_hierarchy(self) -> None:
    """Later rules should override earlier rules."""
    # NOTE: Last matching rule wins
    flight_plan = FlightPlan(
      budget=5000,
      verbosity=[
        VerbosityRule(pattern="*", level=1),  # Root files EXISTENCE
        VerbosityRule(pattern="src/**", level=4),  # Src IMPLEMENTATION
      ],
    )

    renderer = ContextRenderer(flight_plan=flight_plan)

    # File in src should get IMPLEMENTATION
    level = renderer.get_verbosity_for_path("src/main.py")
    assert level == VerbosityLevel.IMPLEMENTATION

    # File in root should get EXISTENCE (only matches first rule)
    level = renderer.get_verbosity_for_path("config.py")
    assert level == VerbosityLevel.EXISTENCE
