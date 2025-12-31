"""Unit tests for verbosity-aware tag extraction."""

from __future__ import annotations

import pytest

from repo_map.core.tags import get_scm_fname, get_tags_from_code
from repo_map.core.verbosity import VerbosityLevel


class TestGetScmFname:
  """Tests for get_scm_fname function."""

  def test_default_returns_tags_scm(self) -> None:
    """Without verbosity, should return the default tags.scm file."""
    path = get_scm_fname("python")
    assert path is not None
    assert path.name == "tags.scm"
    assert "python" in str(path)

  def test_structure_returns_structure_scm(self) -> None:
    """With STRUCTURE verbosity, should return structure.scm."""
    path = get_scm_fname("python", VerbosityLevel.STRUCTURE)
    assert path is not None
    assert path.name == "structure.scm"
    assert "python" in str(path)

  def test_interface_returns_interface_scm(self) -> None:
    """With INTERFACE verbosity, should return interface.scm."""
    path = get_scm_fname("python", VerbosityLevel.INTERFACE)
    assert path is not None
    assert path.name == "interface.scm"
    assert "python" in str(path)

  def test_structure_fallback_to_tags(self) -> None:
    """If no structure query exists, return None (no fallback for unsupported langs)."""
    # Languages without per-verbosity queries should return None
    path = get_scm_fname("c", VerbosityLevel.STRUCTURE)
    # No fallback since we removed legacy files
    assert path is None

  def test_unknown_language_returns_none(self) -> None:
    """Unknown language should return None."""
    path = get_scm_fname("unknownlang123")
    assert path is None

  def test_exclude_level_returns_default(self) -> None:
    """EXCLUDE level should use default tags query."""
    path = get_scm_fname("python", VerbosityLevel.EXCLUDE)
    assert path is not None
    assert path.name == "tags.scm"

  def test_existence_level_returns_default(self) -> None:
    """EXISTENCE level should use default tags query."""
    path = get_scm_fname("python", VerbosityLevel.EXISTENCE)
    assert path is not None
    assert path.name == "tags.scm"

  def test_implementation_level_returns_default(self) -> None:
    """IMPLEMENTATION level should use default tags query."""
    path = get_scm_fname("python", VerbosityLevel.IMPLEMENTATION)
    assert path is not None
    assert path.name == "tags.scm"


class TestGetTagsFromCodeVerbosity:
  """Tests for get_tags_from_code with verbosity parameter."""

  @pytest.fixture
  def sample_python_code(self) -> str:
    """Sample Python code with class and function."""
    return '''
class Calculator:
    """A simple calculator class."""

    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    def subtract(self, a: int, b: int) -> int:
        """Subtract b from a."""
        return a - b


def main():
    """Main function."""
    calc = Calculator()
    print(calc.add(1, 2))
'''

  def test_default_verbosity_extracts_defs_and_refs(
    self, sample_python_code: str
  ) -> None:
    """Without verbosity, should extract both definitions and references."""
    tags = list(get_tags_from_code("/tmp/test.py", "test.py", sample_python_code))
    assert len(tags) > 0
    kinds = {tag.kind for tag in tags}
    assert "def" in kinds

  def test_structure_verbosity_extracts_names(self, sample_python_code: str) -> None:
    """STRUCTURE level should extract definition names."""
    tags = list(
      get_tags_from_code(
        "/tmp/test.py",
        "test.py",
        sample_python_code,
        verbosity=VerbosityLevel.STRUCTURE,
      )
    )
    assert len(tags) > 0
    names = {tag.name for tag in tags if tag.kind == "def"}
    assert "Calculator" in names
    assert "add" in names
    assert "main" in names

  def test_interface_verbosity_extracts_names(self, sample_python_code: str) -> None:
    """INTERFACE level should extract definition names."""
    tags = list(
      get_tags_from_code(
        "/tmp/test.py",
        "test.py",
        sample_python_code,
        verbosity=VerbosityLevel.INTERFACE,
      )
    )
    assert len(tags) > 0
    names = {tag.name for tag in tags if tag.kind == "def"}
    assert "Calculator" in names
    assert "add" in names

  def test_empty_code_returns_no_tags(self) -> None:
    """Empty code should return no tags."""
    tags = list(
      get_tags_from_code(
        "/tmp/test.py",
        "test.py",
        "",
        verbosity=VerbosityLevel.STRUCTURE,
      )
    )
    assert len(tags) == 0

  def test_unknown_extension_returns_no_tags(self) -> None:
    """Unknown file extension should return no tags."""
    tags = list(
      get_tags_from_code(
        "/tmp/test.xyz",
        "test.xyz",
        "some content",
        verbosity=VerbosityLevel.STRUCTURE,
      )
    )
    assert len(tags) == 0
