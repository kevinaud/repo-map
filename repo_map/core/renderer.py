"""
Context renderer for multi-resolution code rendering.

Renders files at different verbosity levels based on FlightPlan rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from repo_map.core.cost import CostManifest, estimate_tokens
from repo_map.core.verbosity import VerbosityLevel

if TYPE_CHECKING:
  from repo_map.core.flight_plan import (
    FlightPlan,
    SectionVerbosity,
    VerbosityRule,
  )


@dataclass
class FileNode:
  """Represents a file with its rendering metadata."""

  path: str
  rel_path: str
  verbosity: VerbosityLevel
  content: str = ""
  costs: dict[VerbosityLevel, int] = field(default_factory=dict)


@dataclass
class Section:
  """Represents a section within a file (class, function, markdown heading)."""

  name: str
  start_line: int
  end_line: int
  content: str
  verbosity: VerbosityLevel


class ContextRenderer:
  """
  Renders repository context at varying verbosity levels.

  Uses FlightPlan rules to determine verbosity for each file and section,
  then renders content at the appropriate detail level.
  """

  def __init__(
    self,
    flight_plan: FlightPlan | None = None,
    default_verbosity: VerbosityLevel = VerbosityLevel.STRUCTURE,
  ) -> None:
    """
    Initialize the context renderer.

    Args:
        flight_plan: Optional flight plan with verbosity rules
        default_verbosity: Default verbosity level when no rules match
    """
    self.flight_plan = flight_plan
    self.default_verbosity = default_verbosity
    self.cost_manifest = CostManifest(
      budget=flight_plan.budget if flight_plan else 20000
    )

  def get_verbosity_for_path(self, file_path: str) -> VerbosityLevel:
    """
    Get the verbosity level for a file path.

    Matches the path against FlightPlan verbosity rules (last match wins).

    Args:
        file_path: Relative path to the file

    Returns:
        Verbosity level for the file
    """
    if self.flight_plan:
      return self.flight_plan.get_verbosity_for_path(file_path)
    return self.default_verbosity

  def get_section_verbosity(
    self,
    section_name: str,
    section_rules: list[SectionVerbosity] | None,
    file_verbosity: VerbosityLevel,
  ) -> VerbosityLevel:
    """
    Get the verbosity level for a section within a file.

    Args:
        section_name: Name of the section (class name, function name, heading)
        section_rules: List of section verbosity rules from FlightPlan
        file_verbosity: Default verbosity from the file-level rule

    Returns:
        Verbosity level for the section
    """
    if not section_rules:
      return file_verbosity

    level = file_verbosity
    for rule in section_rules:
      if fnmatch(section_name, rule.pattern):
        level = rule.verbosity_level
    return level

  def render_file_at_level(
    self,
    file_path: str,
    content: str,
    verbosity: VerbosityLevel,
  ) -> str:
    """
    Render file content at the specified verbosity level.

    Args:
        file_path: Path to the file (for language detection)
        content: Full file content
        verbosity: Verbosity level for rendering

    Returns:
        Rendered content at the specified verbosity level
    """
    if verbosity == VerbosityLevel.EXCLUDE:
      return ""

    if verbosity == VerbosityLevel.EXISTENCE:
      # Level 1: Just the path (handled externally, return empty)
      return ""

    if verbosity == VerbosityLevel.IMPLEMENTATION:
      # Level 4: Full content
      return content

    # Level 2 (STRUCTURE) or Level 3 (INTERFACE)
    # Use tree-sitter to extract at appropriate level
    return self._render_with_treesitter(file_path, content, verbosity)

  def _render_with_treesitter(
    self,
    file_path: str,
    content: str,
    verbosity: VerbosityLevel,
  ) -> str:
    """
    Render content using tree-sitter queries at the given verbosity level.

    Args:
        file_path: Path to the file
        content: Full file content
        verbosity: STRUCTURE or INTERFACE level

    Returns:
        Rendered content with definitions extracted
    """
    from grep_ast import filename_to_lang  # type: ignore[reportMissingTypeStubs]

    from repo_map.core.tags import get_tags_from_code

    lang = filename_to_lang(file_path)
    if not lang:
      # No parser available, fall back to full content for unknown languages
      return content

    # Get tags at the specified verbosity level
    rel_fname = Path(file_path).name
    tags = list(get_tags_from_code(file_path, rel_fname, content, verbosity))

    if not tags:
      # No tags extracted, return empty for structure/interface
      return ""

    # Build output from tags
    lines = content.splitlines()
    output_lines: list[str] = []
    seen_lines: set[int] = set()

    for tag in tags:
      is_def = tag.kind == "def"
      is_new = tag.line not in seen_lines
      is_valid = 0 <= tag.line < len(lines)
      if is_def and is_new and is_valid:
        output_lines.append(lines[tag.line])
        seen_lines.add(tag.line)

    return "\n".join(output_lines)

  def calculate_file_costs(
    self,
    file_path: str,
    content: str,
  ) -> dict[VerbosityLevel, int]:
    """
    Calculate token costs for a file at all verbosity levels.

    Args:
        file_path: Path to the file
        content: Full file content

    Returns:
        Dictionary mapping verbosity levels to token costs
    """
    costs: dict[VerbosityLevel, int] = {}

    # Level 0: EXCLUDE - 0 tokens
    costs[VerbosityLevel.EXCLUDE] = 0

    # Level 1: EXISTENCE - just the path
    rel_path = Path(file_path).name
    costs[VerbosityLevel.EXISTENCE] = estimate_tokens(rel_path)

    # Level 2: STRUCTURE
    structure_content = self.render_file_at_level(
      file_path, content, VerbosityLevel.STRUCTURE
    )
    costs[VerbosityLevel.STRUCTURE] = estimate_tokens(structure_content)

    # Level 3: INTERFACE
    interface_content = self.render_file_at_level(
      file_path, content, VerbosityLevel.INTERFACE
    )
    costs[VerbosityLevel.INTERFACE] = estimate_tokens(interface_content)

    # Level 4: IMPLEMENTATION
    costs[VerbosityLevel.IMPLEMENTATION] = estimate_tokens(content)

    return costs

  def render(
    self,
    files: list[tuple[str, str]],
    show_costs: bool = False,
    strict: bool = False,
  ) -> str:
    """
    Render multiple files according to FlightPlan rules.

    Args:
        files: List of (file_path, content) tuples
        show_costs: Whether to include cost annotations
        strict: Whether to enforce budget strictly (raise error if exceeded)

    Returns:
        Rendered output string

    Raises:
        ValueError: If strict=True and budget is exceeded
    """
    output_parts: list[str] = []
    total_tokens = 0
    budget = self.flight_plan.budget if self.flight_plan else 20000

    for file_path, content in files:
      verbosity = self.get_verbosity_for_path(file_path)

      if verbosity == VerbosityLevel.EXCLUDE:
        continue

      # Render at appropriate level
      rendered = self.render_file_at_level(file_path, content, verbosity)

      # Calculate cost
      tokens = estimate_tokens(rendered) if rendered else estimate_tokens(file_path)

      # Check budget in strict mode
      if strict and total_tokens + tokens > budget:
        msg = (
          f"Budget exceeded: {total_tokens + tokens} tokens "
          f"(budget: {budget}). Stopped at {file_path}"
        )
        raise ValueError(msg)

      total_tokens += tokens

      # Build output for this file
      file_output = f"## {file_path}\n"

      if show_costs:
        costs = self.calculate_file_costs(file_path, content)
        file_output += (
          f"# Costs: L0={costs[VerbosityLevel.EXCLUDE]}, "
          f"L1={costs[VerbosityLevel.EXISTENCE]}, "
          f"L2={costs[VerbosityLevel.STRUCTURE]}, "
          f"L3={costs[VerbosityLevel.INTERFACE]}, "
          f"L4={costs[VerbosityLevel.IMPLEMENTATION]} tokens\n"
        )

      if verbosity == VerbosityLevel.EXISTENCE:
        file_output += f"# [path only - {tokens} tokens]\n"
      elif rendered:
        file_output += f"```\n{rendered}\n```\n"

      output_parts.append(file_output)

    # Add budget summary
    summary = f"\n# Total: {total_tokens}/{budget} tokens"
    if total_tokens > budget:
      summary += " ⚠️ OVER BUDGET"
    output_parts.append(summary)

    return "\n".join(output_parts)


def match_verbosity_rules(
  file_path: str,
  rules: list[VerbosityRule],
  default: VerbosityLevel = VerbosityLevel.STRUCTURE,
) -> tuple[VerbosityLevel, list[SectionVerbosity] | None]:
  """
  Find the verbosity level and section rules for a file path.

  Last matching rule wins.

  Args:
      file_path: Relative path to match
      rules: List of verbosity rules to check
      default: Default verbosity if no rules match

  Returns:
      Tuple of (verbosity_level, section_rules)
  """
  level = default
  sections: list[SectionVerbosity] | None = None

  for rule in rules:
    spec = PathSpec.from_lines(GitWildMatchPattern, [rule.pattern])
    if spec.match_file(file_path):
      if rule.verbosity_level is not None:
        level = rule.verbosity_level
      if rule.sections is not None:
        sections = rule.sections

  return level, sections
