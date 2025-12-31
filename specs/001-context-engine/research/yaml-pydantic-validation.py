"""
Research: YAML Configuration Validation with Pydantic + PyYAML

This module demonstrates how to validate a "Flight Plan" YAML configuration
using Pydantic models. It covers:
1. Loading YAML into Pydantic models (yaml.safe_load + model_validate)
2. Nested Pydantic models for complex structures
3. Good error messages for validation failures
4. Optional fields with defaults
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

# =============================================================================
# Model Definitions
# =============================================================================


class PathWeight(BaseModel):
  """A path pattern with an associated weight for ranking."""

  pattern: str = Field(description="Glob pattern for matching files")
  weight: float = Field(gt=0, description="Weight multiplier (must be positive)")


class SymbolWeight(BaseModel):
  """A symbol name with an associated weight for ranking."""

  name: str = Field(min_length=1, description="Symbol name to boost")
  weight: float = Field(gt=0, description="Weight multiplier (must be positive)")


class Focus(BaseModel):
  """Focus configuration for boosting specific paths and symbols."""

  paths: list[PathWeight] = Field(default_factory=list)
  symbols: list[SymbolWeight] = Field(default_factory=list)


class SectionVerbosity(BaseModel):
  """Verbosity level for a specific section within a file."""

  pattern: str = Field(
    description="Pattern to match sections (e.g., 'API Reference/*')"
  )
  level: Annotated[int, Field(ge=0, le=5)] = Field(
    description="Verbosity level 0-5 (0=minimal, 5=maximum detail)"
  )


class VerbosityRule(BaseModel):
  """Verbosity configuration for files matching a pattern.

  Can specify either a simple level or section-specific levels.
  """

  pattern: str = Field(description="Glob pattern for matching files")
  level: Annotated[int, Field(ge=0, le=5)] | None = Field(
    default=None, description="Default verbosity level for the entire file"
  )
  sections: list[SectionVerbosity] | None = Field(
    default=None, description="Section-specific verbosity overrides"
  )

  @model_validator(mode="after")
  def validate_level_or_sections(self) -> VerbosityRule:
    """Ensure at least one of level or sections is provided."""
    if self.level is None and self.sections is None:
      raise ValueError("Either 'level' or 'sections' must be specified")
    return self


class CustomQuery(BaseModel):
  """Custom tree-sitter query for specific file patterns."""

  pattern: str = Field(description="Glob pattern for matching files")
  query: str = Field(min_length=1, description="Tree-sitter query string")


class FlightPlan(BaseModel):
  """Main configuration model for the Flight Plan.

  A Flight Plan configures how the context engine generates repository maps,
  including token budget, focus areas, verbosity levels, and custom queries.
  """

  budget: Annotated[int, Field(gt=0, le=1_000_000)] = Field(
    default=20000, description="Maximum token budget for the output"
  )
  focus: Focus | None = Field(
    default=None, description="Optional focus configuration for boosting"
  )
  verbosity: list[VerbosityRule] = Field(
    default_factory=list, description="Verbosity rules for different file patterns"
  )
  custom_queries: list[CustomQuery] = Field(
    default_factory=list, description="Custom tree-sitter queries"
  )

  model_config = {
    "extra": "forbid",  # Reject unknown fields for strict validation
  }


# =============================================================================
# Loading and Validation Functions
# =============================================================================


def load_flight_plan(yaml_content: str) -> FlightPlan:
  """Load and validate a Flight Plan from YAML content.

  Args:
      yaml_content: Raw YAML string

  Returns:
      Validated FlightPlan model

  Raises:
      yaml.YAMLError: If YAML syntax is invalid
      ValidationError: If the data doesn't match the schema
  """
  # Step 1: Parse YAML to dict
  data = yaml.safe_load(yaml_content)

  # Handle empty YAML (returns None)
  if data is None:
    data = {}

  # Step 2: Validate with Pydantic
  return FlightPlan.model_validate(data)


def load_flight_plan_from_file(path: Path | str) -> FlightPlan:
  """Load and validate a Flight Plan from a YAML file.

  Args:
      path: Path to the YAML file

  Returns:
      Validated FlightPlan model

  Raises:
      FileNotFoundError: If the file doesn't exist
      yaml.YAMLError: If YAML syntax is invalid
      ValidationError: If the data doesn't match the schema
  """
  path = Path(path)
  with path.open() as f:
    return load_flight_plan(f.read())


# =============================================================================
# Error Handling Patterns
# =============================================================================


def format_validation_errors(error: ValidationError) -> str:
  """Format Pydantic validation errors into human-readable messages.

  Args:
      error: The ValidationError from Pydantic

  Returns:
      Formatted error string with location and message for each error
  """
  lines = [f"Configuration validation failed with {error.error_count()} error(s):"]

  for err in error.errors():
    # Build the location path (e.g., "focus.paths.0.weight")
    loc = ".".join(str(part) for part in err["loc"])
    msg = err["msg"]
    error_type = err["type"]

    # Include the invalid input value for context
    input_val = err.get("input")
    if input_val is not None:
      input_repr = repr(input_val)
      if len(input_repr) > 50:
        input_repr = input_repr[:47] + "..."
      lines.append(f"  • {loc}: {msg} (got {input_repr}) [{error_type}]")
    else:
      lines.append(f"  • {loc}: {msg} [{error_type}]")

  return "\n".join(lines)


def safe_load_flight_plan(yaml_content: str) -> tuple[FlightPlan | None, str | None]:
  """Safely load a Flight Plan, returning errors as strings.

  This is useful for CLI tools that want to display friendly error messages.

  Args:
      yaml_content: Raw YAML string

  Returns:
      Tuple of (FlightPlan, None) on success, or (None, error_message) on failure
  """
  try:
    return load_flight_plan(yaml_content), None
  except yaml.YAMLError as e:
    # Handle YAML syntax errors
    if hasattr(e, "problem_mark"):
      mark = e.problem_mark
      return None, (
        f"YAML syntax error at line {mark.line + 1}, column {mark.column + 1}:\n"
        f"  {e.problem}"
      )
    return None, f"YAML syntax error: {e}"
  except ValidationError as e:
    return None, format_validation_errors(e)


# =============================================================================
# Examples and Tests
# =============================================================================

if __name__ == "__main__":
  # Example 1: Valid complete configuration
  valid_yaml = """
budget: 20000
focus:
  paths:
    - pattern: "src/core/*"
      weight: 10.0
  symbols:
    - name: "authenticate"
      weight: 5.0
verbosity:
  - pattern: "src/**/*.py"
    level: 3
  - pattern: "tests/**"
    level: 1
  - pattern: "docs/api.md"
    sections:
      - pattern: "API Reference/*"
        level: 4
      - pattern: "*"
        level: 0
custom_queries:
  - pattern: "src/db/*.py"
    query: "(string) @sql"
"""

  print("=" * 60)
  print("Example 1: Valid complete configuration")
  print("=" * 60)

  plan, error = safe_load_flight_plan(valid_yaml)
  if plan:
    print("✓ Loaded successfully!")
    print(f"  Budget: {plan.budget}")
    print(f"  Focus paths: {len(plan.focus.paths) if plan.focus else 0}")
    print(f"  Focus symbols: {len(plan.focus.symbols) if plan.focus else 0}")
    print(f"  Verbosity rules: {len(plan.verbosity)}")
    print(f"  Custom queries: {len(plan.custom_queries)}")
  else:
    print(f"✗ Error: {error}")

  # Example 2: Minimal configuration (uses defaults)
  minimal_yaml = """
budget: 5000
"""

  print("\n" + "=" * 60)
  print("Example 2: Minimal configuration (uses defaults)")
  print("=" * 60)

  plan, error = safe_load_flight_plan(minimal_yaml)
  if plan:
    print("✓ Loaded successfully!")
    print(f"  Budget: {plan.budget}")
    print(f"  Focus: {plan.focus}")
    print(f"  Verbosity rules: {plan.verbosity}")
  else:
    print(f"✗ Error: {error}")

  # Example 3: Empty configuration (all defaults)
  empty_yaml = ""

  print("\n" + "=" * 60)
  print("Example 3: Empty configuration (all defaults)")
  print("=" * 60)

  plan, error = safe_load_flight_plan(empty_yaml)
  if plan:
    print("✓ Loaded successfully with defaults!")
    print(f"  Budget: {plan.budget}")
  else:
    print(f"✗ Error: {error}")

  # Example 4: Invalid - negative weight
  invalid_weight = """
focus:
  paths:
    - pattern: "src/*"
      weight: -5.0
"""

  print("\n" + "=" * 60)
  print("Example 4: Invalid - negative weight")
  print("=" * 60)

  plan, error = safe_load_flight_plan(invalid_weight)
  if error:
    print(f"✗ Expected error:\n{error}")

  # Example 5: Invalid - missing required field in nested model
  missing_field = """
verbosity:
  - pattern: "src/**"
"""

  print("\n" + "=" * 60)
  print("Example 5: Invalid - missing level or sections")
  print("=" * 60)

  plan, error = safe_load_flight_plan(missing_field)
  if error:
    print(f"✗ Expected error:\n{error}")

  # Example 6: Invalid - unknown field (extra="forbid")
  unknown_field = """
budget: 10000
unknown_option: true
"""

  print("\n" + "=" * 60)
  print("Example 6: Invalid - unknown field")
  print("=" * 60)

  plan, error = safe_load_flight_plan(unknown_field)
  if error:
    print(f"✗ Expected error:\n{error}")

  # Example 7: YAML syntax error
  bad_yaml = """
budget: 10000
focus:
  paths:
    - pattern: "src/*"
  weight: 5.0
    bad_indent: oops
"""

  print("\n" + "=" * 60)
  print("Example 7: YAML syntax error")
  print("=" * 60)

  plan, error = safe_load_flight_plan(bad_yaml)
  if error:
    print(f"✗ Expected error:\n{error}")

  # Example 8: Invalid - budget too large
  budget_too_large = """
budget: 2000000
"""

  print("\n" + "=" * 60)
  print("Example 8: Invalid - budget exceeds maximum")
  print("=" * 60)

  plan, error = safe_load_flight_plan(budget_too_large)
  if error:
    print(f"✗ Expected error:\n{error}")

  # Example 9: Type coercion - string to int
  type_coercion = """
budget: "15000"
"""

  print("\n" + "=" * 60)
  print("Example 9: Type coercion - string to int")
  print("=" * 60)

  plan, error = safe_load_flight_plan(type_coercion)
  if plan:
    print(
      f"✓ Pydantic coerced '15000' to int: {plan.budget} (type: {type(plan.budget).__name__})"
    )
  else:
    print(f"✗ Error: {error}")

  # Summary of key patterns
  print("\n" + "=" * 60)
  print("KEY PATTERNS SUMMARY")
  print("=" * 60)
  print("""
1. LOADING YAML INTO PYDANTIC:
   data = yaml.safe_load(yaml_content)
   model = MyModel.model_validate(data)

2. NESTED MODELS:
   - Define separate BaseModel classes for each nested structure
   - Use list[NestedModel] for arrays of objects
   - Use NestedModel | None for optional nested objects

3. OPTIONAL FIELDS WITH DEFAULTS:
   - field: Type = Field(default=default_value)
   - field: Type | None = Field(default=None)
   - field: list[Type] = Field(default_factory=list)

4. VALIDATION CONSTRAINTS:
   - Field(gt=0) for positive numbers
   - Field(ge=0, le=5) for ranges
   - Field(min_length=1) for non-empty strings
   - Annotated[int, Field(ge=0)] for constrained types

5. CUSTOM VALIDATION:
   @field_validator('field_name', mode='after')
   @classmethod
   def validate_field(cls, value, info):
       # Access other fields via info.data
       return value

6. ERROR HANDLING:
   - Catch yaml.YAMLError for YAML syntax errors
   - Catch ValidationError for schema validation errors
   - Use error.errors() for structured error data
   - Access error['loc'], error['msg'], error['type']

7. STRICT MODE:
   model_config = {"extra": "forbid"}  # Reject unknown fields
""")
