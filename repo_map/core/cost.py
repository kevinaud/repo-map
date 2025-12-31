"""Cost estimation utilities for token budget management.

This module provides functions for estimating token costs at different
verbosity levels.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from repo_map.core.verbosity import VerbosityLevel

if TYPE_CHECKING:
  from collections.abc import Mapping


def estimate_tokens(text: str) -> int:
  """Estimate token count using character-based heuristic.

  Uses a simple approximation of ~4 characters per token on average.
  This is consistent with the existing implementation in RepoMap.

  Args:
      text: Text content to estimate tokens for

  Returns:
      Estimated token count
  """
  return len(text) // 4


def calculate_file_costs(
  content: str,
  structure_content: str | None = None,
  interface_content: str | None = None,
) -> dict[VerbosityLevel, int]:
  """Calculate token costs for a file at all verbosity levels.

  Args:
      content: Full file content (Level 4)
      structure_content: Structure-only content (Level 2), optional
      interface_content: Interface content (Level 3), optional

  Returns:
      Dict mapping VerbosityLevel to token cost
  """
  # Level 4: Full content
  l4_tokens = estimate_tokens(content)

  # Level 3: Interface (signatures + docstrings)
  # If not provided, estimate as ~40% of full content
  if interface_content is not None:
    l3_tokens = estimate_tokens(interface_content)
  else:
    l3_tokens = int(l4_tokens * 0.4)

  # Level 2: Structure (definitions only)
  # If not provided, estimate as ~15% of full content
  if structure_content is not None:
    l2_tokens = estimate_tokens(structure_content)
  else:
    l2_tokens = int(l4_tokens * 0.15)

  # Level 1: Existence (path only)
  # Approximate: "path/to/file.py\n" is small, estimate ~5 tokens
  l1_tokens = 5

  # Level 0: Exclude (nothing rendered)
  l0_tokens = 0

  return {
    VerbosityLevel.EXCLUDE: l0_tokens,
    VerbosityLevel.EXISTENCE: l1_tokens,
    VerbosityLevel.STRUCTURE: l2_tokens,
    VerbosityLevel.INTERFACE: l3_tokens,
    VerbosityLevel.IMPLEMENTATION: l4_tokens,
  }


def format_cost_annotation(
  path: str,
  costs: Mapping[VerbosityLevel, int],
) -> str:
  """Format cost annotation for a file header.

  Args:
      path: File path
      costs: Dict of verbosity level to token cost

  Returns:
      Formatted annotation string like:
      "# path/file.py [L1:5 L2:50 L3:120 L4:340]"
  """
  l1 = costs.get(VerbosityLevel.EXISTENCE, 0)
  l2 = costs.get(VerbosityLevel.STRUCTURE, 0)
  l3 = costs.get(VerbosityLevel.INTERFACE, 0)
  l4 = costs.get(VerbosityLevel.IMPLEMENTATION, 0)

  return f"# {path} [L1:{l1} L2:{l2} L3:{l3} L4:{l4}]"


def format_budget_warning(budget: int, actual: int) -> str:
  """Format a budget overrun warning message.

  Args:
      budget: Configured token budget
      actual: Actual tokens used

  Returns:
      Warning message string
  """
  overrun = actual - budget
  return f"# ⚠️ BUDGET EXCEEDED: {actual} tokens (budget: {budget}, +{overrun})"


class CostManifest:
  """Tracks costs across multiple files for budget management."""

  def __init__(self, budget: int):
    """Initialize cost manifest.

    Args:
        budget: Token budget limit
    """
    self.budget = budget
    self.files: dict[str, dict[VerbosityLevel, int]] = {}
    self._actual: int = 0

  def add_file(
    self,
    path: str,
    costs: dict[VerbosityLevel, int],
    rendered_level: VerbosityLevel,
  ) -> None:
    """Add a file's costs to the manifest.

    Args:
        path: Relative file path
        costs: Token costs at each verbosity level
        rendered_level: The level at which this file was rendered
    """
    self.files[path] = costs
    self._actual += costs.get(rendered_level, 0)

  @property
  def actual(self) -> int:
    """Total tokens actually used."""
    return self._actual

  @property
  def overrun(self) -> int:
    """Amount over budget (0 if under)."""
    return max(0, self._actual - self.budget)

  @property
  def is_over_budget(self) -> bool:
    """Check if actual usage exceeds budget."""
    return self._actual > self.budget

  def total_at_level(self, level: VerbosityLevel) -> int:
    """Calculate total tokens if all files were at given level.

    Args:
        level: Verbosity level to calculate for

    Returns:
        Total token count
    """
    return sum(costs.get(level, 0) for costs in self.files.values())

  def get_top_contributors(self, n: int = 5) -> list[tuple[str, int]]:
    """Get the files contributing most to the actual token count.

    Args:
        n: Number of top contributors to return

    Returns:
        List of (path, tokens) tuples, sorted by tokens descending
    """
    contributors: list[tuple[str, int]] = []
    for path, costs in self.files.items():
      # Use the max cost as a proxy (actual rendered level tracked separately)
      max_cost = max(costs.values())
      contributors.append((path, max_cost))

    return sorted(contributors, key=lambda x: x[1], reverse=True)[:n]
