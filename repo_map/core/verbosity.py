"""Verbosity level enum for multi-resolution rendering."""

from __future__ import annotations

from enum import IntEnum


class VerbosityLevel(IntEnum):
  """Defines the detail level for rendering content.

  The verbosity levels control how much information is shown for each
  file or section:

  - EXCLUDE (0): Hidden entirely from output
  - EXISTENCE (1): File/section path only
  - STRUCTURE (2): Top-level definitions/headings only
  - INTERFACE (3): Definitions + Signatures + Docstrings
  - IMPLEMENTATION (4): Full raw content
  """

  EXCLUDE = 0
  EXISTENCE = 1
  STRUCTURE = 2
  INTERFACE = 3
  IMPLEMENTATION = 4

  @classmethod
  def from_int(cls, value: int) -> VerbosityLevel:
    """Create VerbosityLevel from integer value.

    Args:
        value: Integer 0-4

    Returns:
        Corresponding VerbosityLevel

    Raises:
        ValueError: If value is not 0-4
    """
    if not 0 <= value <= 4:
      raise ValueError(f"Verbosity level must be 0-4, got {value}")
    return cls(value)
