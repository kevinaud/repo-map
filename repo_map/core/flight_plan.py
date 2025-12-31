"""Flight Plan configuration models for context engine.

This module provides Pydantic models for validating and loading
YAML "flight plan" configurations that control multi-resolution
rendering.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from repo_map.core.verbosity import VerbosityLevel


class PathBoost(BaseModel):
  """A file/directory path pattern with boost weight for PageRank."""

  model_config = ConfigDict(extra="forbid")

  pattern: Annotated[str, Field(min_length=1, description="Glob pattern for paths")]
  weight: Annotated[
    float, Field(default=10.0, gt=0, description="Boost multiplier (must be > 0)")
  ]


class SymbolBoost(BaseModel):
  """A symbol name with boost weight for PageRank."""

  model_config = ConfigDict(extra="forbid")

  name: Annotated[str, Field(min_length=1, description="Symbol name to boost")]
  weight: Annotated[
    float, Field(default=10.0, gt=0, description="Boost multiplier (must be > 0)")
  ]


class Focus(BaseModel):
  """Configuration for symbol/path boosting in PageRank."""

  model_config = ConfigDict(extra="forbid")

  paths: list[PathBoost] = Field(
    default_factory=list, description="File/directory patterns to boost"
  )
  symbols: list[SymbolBoost] = Field(
    default_factory=list, description="Symbol names to boost"
  )


class SectionVerbosity(BaseModel):
  """Verbosity rule for a section within a file."""

  model_config = ConfigDict(extra="forbid")

  pattern: Annotated[
    str, Field(min_length=1, description="Glob pattern for section names")
  ]
  level: Annotated[int, Field(ge=0, le=4, description="Verbosity level 0-4")]

  @property
  def verbosity_level(self) -> VerbosityLevel:
    """Get the level as VerbosityLevel enum."""
    return VerbosityLevel(self.level)


class VerbosityRule(BaseModel):
  """Maps a file pattern to a verbosity level.

  Either `level` or `sections` must be specified, but not both.
  """

  model_config = ConfigDict(extra="forbid")

  pattern: Annotated[str, Field(min_length=1, description="Glob pattern")]
  level: Annotated[int | None, Field(default=None, ge=0, le=4)] = None
  sections: list[SectionVerbosity] | None = None

  @model_validator(mode="after")
  def check_level_or_sections(self) -> VerbosityRule:
    """Validate that exactly one of level or sections is specified."""
    if self.level is None and self.sections is None:
      raise ValueError("Either 'level' or 'sections' must be specified")
    if self.level is not None and self.sections is not None:
      raise ValueError("Cannot specify both 'level' and 'sections'")
    return self

  @property
  def verbosity_level(self) -> VerbosityLevel | None:
    """Get the file-level verbosity if set."""
    if self.level is not None:
      return VerbosityLevel(self.level)
    return None


class CustomQuery(BaseModel):
  """Custom tree-sitter query for specific paths."""

  model_config = ConfigDict(extra="forbid")

  pattern: Annotated[str, Field(min_length=1, description="Glob pattern")]
  query: Annotated[str, Field(min_length=1, description="Tree-sitter .scm query")]


class FlightPlan(BaseModel):
  """Complete configuration for a rendering request.

  The FlightPlan specifies:
  - Token budget
  - Focus boosting for PageRank
  - Verbosity rules (pattern → level)
  - Custom tree-sitter queries
  """

  model_config = ConfigDict(extra="forbid")

  budget: Annotated[int, Field(default=20000, gt=0, description="Token budget limit")]
  focus: Focus | None = None
  verbosity: list[VerbosityRule] = Field(
    default_factory=list, description="Verbosity rules (pattern → level)"
  )
  custom_queries: list[CustomQuery] = Field(
    default_factory=list, description="Custom tree-sitter queries"
  )

  @classmethod
  def from_yaml(cls, yaml_content: str) -> FlightPlan:
    """Parse and validate a flight plan from YAML string.

    Args:
        yaml_content: YAML configuration string

    Returns:
        Validated FlightPlan instance

    Raises:
        ValueError: If YAML is invalid or doesn't match schema
    """
    try:
      data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
      raise ValueError(f"Invalid YAML syntax: {e}") from e

    if data is None:
      data = {}

    return cls.model_validate(data)

  @classmethod
  def from_yaml_file(cls, path: Path | str) -> FlightPlan:
    """Load and validate a flight plan from a YAML file.

    Args:
        path: Path to the YAML configuration file

    Returns:
        Validated FlightPlan instance

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If YAML is invalid or doesn't match schema
    """
    path = Path(path)
    if not path.exists():
      raise FileNotFoundError(f"Flight plan not found: {path}")

    yaml_content = path.read_text(encoding="utf-8")
    return cls.from_yaml(yaml_content)

  def get_verbosity_for_path(self, rel_path: str) -> VerbosityLevel:
    """Get the verbosity level for a file path.

    Applies verbosity rules in order, last match wins.

    Args:
        rel_path: Relative path to match

    Returns:
        VerbosityLevel for the path (IMPLEMENTATION if no rule matches)
    """
    import fnmatch

    level = VerbosityLevel.IMPLEMENTATION  # Default to full content

    for rule in self.verbosity:
      if fnmatch.fnmatch(rel_path, rule.pattern) and rule.level is not None:
        level = VerbosityLevel(rule.level)
      # If sections are specified, file-level is IMPLEMENTATION
      # Section-level verbosity is handled separately

    return level

  def get_section_rules_for_path(self, rel_path: str) -> list[SectionVerbosity] | None:
    """Get section-level verbosity rules for a file path.

    Args:
        rel_path: Relative path to match

    Returns:
        List of section rules if any apply, None otherwise
    """
    import fnmatch

    for rule in self.verbosity:
      if fnmatch.fnmatch(rel_path, rule.pattern) and rule.sections is not None:
        return rule.sections

    return None

  def to_yaml(self) -> str:
    """Serialize the flight plan to YAML string.

    Returns:
        YAML representation of the flight plan
    """
    data = self.model_dump(exclude_none=True, exclude_defaults=True)
    return yaml.safe_dump(data, default_flow_style=False, sort_keys=False)


def load_flight_plan(path: Path | str | None) -> FlightPlan | None:
  """Load a flight plan from file, returning None if path is None.

  Args:
      path: Path to YAML file, or None

  Returns:
      FlightPlan if path provided, None otherwise
  """
  if path is None:
    return None
  return FlightPlan.from_yaml_file(path)


def format_validation_errors(errors: list[Any]) -> str:
  """Format Pydantic validation errors for user-friendly display.

  Args:
      errors: List of error dictionaries from ValidationError

  Returns:
      Formatted error message string
  """
  lines = ["Invalid flight plan configuration:", ""]
  for error in errors:
    loc = ".".join(str(x) for x in error["loc"])
    msg = error["msg"]
    lines.append(f"  - {loc}: {msg}")
  return "\n".join(lines)
