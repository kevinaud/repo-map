"""Unit tests for markdown section extraction and rendering."""

from __future__ import annotations

import pytest

from repo_map.core.renderer import ContextRenderer
from repo_map.core.tags import get_tags_from_code
from repo_map.core.verbosity import VerbosityLevel


class TestMarkdownSectionExtraction:
  """Tests for extracting sections from markdown files."""

  @pytest.fixture
  def sample_markdown(self) -> str:
    """Sample markdown document."""
    return """# Project Title

This is the introduction paragraph describing the project.

## Installation

To install the project, run:

```bash
pip install myproject
```

### Prerequisites

- Python 3.10+
- Git

## Usage

Here's how to use the project:

```python
from myproject import main
main()
```

## API Reference

### Functions

#### get_data(id)

Retrieves data by ID.

#### process(data)

Processes the data.

## License

MIT License.
"""

  def test_extract_headings(self, sample_markdown: str) -> None:
    """Should extract all heading levels."""
    tags = list(get_tags_from_code("/tmp/doc.md", "doc.md", sample_markdown))
    defs = [t for t in tags if t.kind == "def"]

    # Should have all headings
    names = {t.name for t in defs}
    assert "Project Title" in names
    assert "Installation" in names
    assert "Prerequisites" in names
    assert "Usage" in names
    assert "API Reference" in names
    assert "Functions" in names
    assert "License" in names

  def test_extract_heading_line_numbers(self, sample_markdown: str) -> None:
    """Headings should have correct line numbers."""
    tags = list(get_tags_from_code("/tmp/doc.md", "doc.md", sample_markdown))
    defs = {t.name: t.line for t in tags if t.kind == "def"}

    # Line numbers are 0-indexed
    assert defs["Project Title"] == 0
    assert defs["Installation"] == 4
    assert defs["Usage"] == 17

  def test_structure_verbosity_extracts_headings(self, sample_markdown: str) -> None:
    """STRUCTURE verbosity should extract heading names."""
    tags = list(
      get_tags_from_code(
        "/tmp/doc.md", "doc.md", sample_markdown, VerbosityLevel.STRUCTURE
      )
    )
    defs = [t for t in tags if t.kind == "def"]

    # Should have headings
    assert len(defs) > 0
    names = {t.name for t in defs}
    assert "Project Title" in names or "Installation" in names


class TestMarkdownRendering:
  """Tests for rendering markdown at different verbosity levels."""

  @pytest.fixture
  def sample_markdown(self) -> str:
    """Sample markdown document."""
    return """# Getting Started

Welcome to the project documentation.

## Installation

Run pip install to get started.

## Configuration

Edit the config file.
"""

  def test_exclude_returns_empty(self, sample_markdown: str) -> None:
    """EXCLUDE should return empty content."""
    renderer = ContextRenderer()
    result = renderer.render_file_at_level(
      "readme.md", sample_markdown, VerbosityLevel.EXCLUDE
    )
    assert result == ""

  def test_existence_returns_empty(self, sample_markdown: str) -> None:
    """EXISTENCE should return empty (path handled externally)."""
    renderer = ContextRenderer()
    result = renderer.render_file_at_level(
      "readme.md", sample_markdown, VerbosityLevel.EXISTENCE
    )
    assert result == ""

  def test_implementation_returns_full_content(self, sample_markdown: str) -> None:
    """IMPLEMENTATION should return full markdown."""
    renderer = ContextRenderer()
    result = renderer.render_file_at_level(
      "readme.md", sample_markdown, VerbosityLevel.IMPLEMENTATION
    )
    assert result == sample_markdown

  def test_structure_extracts_headings(self, sample_markdown: str) -> None:
    """STRUCTURE should extract heading lines."""
    renderer = ContextRenderer()
    result = renderer.render_file_at_level(
      "readme.md", sample_markdown, VerbosityLevel.STRUCTURE
    )
    # Should contain heading lines
    assert "# Getting Started" in result or "Getting Started" in result
    # Should not contain full paragraph content
    assert "Welcome to the project documentation." not in result


class TestMarkdownCostCalculation:
  """Tests for markdown file cost calculations."""

  def test_costs_vary_by_level(self) -> None:
    """Different verbosity levels should have different costs."""
    renderer = ContextRenderer()
    markdown = """# Title

Long paragraph with lots of content here that should make
the implementation level much larger than structure level.

## Section

More content that adds to the total.
"""
    costs = renderer.calculate_file_costs("doc.md", markdown)

    # EXCLUDE should be zero
    assert costs[VerbosityLevel.EXCLUDE] == 0

    # EXISTENCE should be small (just path)
    assert costs[VerbosityLevel.EXISTENCE] < 10

    # IMPLEMENTATION should be largest
    assert costs[VerbosityLevel.IMPLEMENTATION] > costs[VerbosityLevel.STRUCTURE]
