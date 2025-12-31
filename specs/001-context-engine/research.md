# Research: Context Engine Implementation

**Date**: 2025-12-31  
**Feature**: 001-context-engine

---

## 1. NetworkX PageRank Personalization

### Decision
Use the `personalization` parameter in `nx.pagerank()` to implement Focus boosting.

### Rationale
The personalization vector biases where the "random surfer" teleports, which compounds over iterations. This provides meaningful prioritization while still allowing graph structure to influence results.

### Key Implementation Details

```python
def pagerank_with_boosts(
    G: nx.DiGraph,
    focus_boosts: dict[str, float] | None = None,
    default_weight: float = 1.0,
    alpha: float = 0.85,
) -> dict[str, float]:
    """Run PageRank with optional node boosting."""
    if not focus_boosts:
        return nx.pagerank(G, alpha=alpha, weight="weight")
    
    # CRITICAL: Include ALL nodes with at least default weight
    # Nodes not in dict get weight 0 — they can only receive rank via links
    personalization = {node: default_weight for node in G.nodes()}
    for path, boost in focus_boosts.items():
        if path in personalization:
            personalization[path] = default_weight * boost
    
    return nx.pagerank(
        G, 
        alpha=alpha, 
        personalization=personalization,
        dangling=personalization,  # Match teleportation behavior for sink nodes
        weight="weight"
    )
```

### Recommended Boost Values

| Scenario | Multiplier | Use Case |
|----------|------------|----------|
| Default | 1.0 | Non-boosted nodes |
| Subtle focus | 5.0 | Gentle preference |
| **Strong focus** | **10.0** | **Recommended default** |
| Dominant focus | 50-100 | Near-exclusive priority |

### Pitfalls to Avoid

1. **Omitting nodes** - Always include all graph nodes with at least 1.0 weight
2. **Zero vector** - Validate boosted paths exist in graph before calling pagerank
3. **Extreme boosts (1000x+)** - Ignores graph structure; keep ≤100x

### Alternatives Considered

- Post-ranking multiplier: Rejected because it doesn't leverage graph relationships
- Custom algorithm: Rejected (unnecessary complexity, NetworkX is battle-tested)

---

## 2. Tree-Sitter Query Patterns for Multi-Resolution Extraction

### Decision
Capture individual AST components (names, parameters, docstrings) rather than whole nodes, then reconstruct in code.

### Rationale
Tree-sitter queries capture whole nodes — you cannot exclude children (like function bodies) in the query itself. Capturing components gives fine-grained control.

### Python Queries

**Level 2 (Structure) - Definitions Only:**
```scheme
; python-structure.scm
; Class definitions
(class_definition
  name: (identifier) @name.definition.class) @definition.class

; Function definitions  
(function_definition
  name: (identifier) @name.definition.function) @definition.function

; Top-level assignments (constants)
(module
  (expression_statement
    (assignment
      left: (identifier) @name.definition.constant))) @definition.constant
```

**Level 3 (Interface) - Definitions + Signatures + Docstrings:**
```scheme
; python-interface.scm
; Class with docstring
(class_definition
  name: (identifier) @name.definition.class
  body: (block
    .
    (expression_statement
      (string) @docstring.class)?)) @definition.class

; Function with full signature and docstring
(function_definition
  name: (identifier) @name.definition.function
  parameters: (parameters) @signature.parameters
  return_type: (type)? @signature.return_type
  body: (block
    .
    (expression_statement
      (string) @docstring.function)?)) @definition.function

; Decorated definitions
(decorated_definition
  (decorator)+ @decorator
  definition: (function_definition
    name: (identifier) @name.definition.function)) @definition.decorated
```

### Markdown Queries

**Level 2 (Structure) - Headings Only:**
```scheme
; markdown-structure.scm
(atx_heading
  (atx_h1_marker)
  heading_content: (_) @name.definition.h1) @definition.heading

(atx_heading
  (atx_h2_marker)
  heading_content: (_) @name.definition.h2) @definition.heading

; ... h3-h6 similar
```

**Level 3 (Interface) - Headings + First Paragraph:**
```scheme
; markdown-interface.scm
; Use section nodes to capture heading + first paragraph
(section
  (atx_heading) @heading
  .
  (paragraph)? @summary)
```

### Limitations & Workarounds

| Limitation | Workaround |
|------------|------------|
| Can't exclude node children in query | Capture whole node, extract range in code |
| Sibling relationships need anchoring | Use `.` operator for "first child" |
| Language-specific docstring formats | Per-language post-processing |
| Query complexity varies by language | Start with Python/Markdown, extend incrementally |

### Implementation Strategy

1. **Level 1**: File path only (no query needed)
2. **Level 2**: Load `{lang}-structure.scm`, capture only definition names
3. **Level 3**: Load `{lang}-interface.scm`, reconstruct from captured components
4. **Level 4**: Raw file read (no query needed)

---

## 3. Pydantic + PyYAML Configuration Validation

### Decision
Use Pydantic models with `model_validate()` for strict YAML schema validation.

### Rationale
Pydantic provides type coercion, validation constraints, and clear error messages. PyYAML handles parsing; Pydantic handles validation.

### Complete Schema Implementation

```python
from __future__ import annotations

from enum import IntEnum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class VerbosityLevel(IntEnum):
    """Verbosity levels for rendering."""
    EXCLUDE = 0
    EXISTENCE = 1
    STRUCTURE = 2
    INTERFACE = 3
    IMPLEMENTATION = 4


class PathBoost(BaseModel):
    """A file/directory path with boost weight."""
    pattern: str = Field(min_length=1, description="Glob pattern for paths")
    weight: float = Field(default=10.0, gt=0, description="Boost multiplier")


class SymbolBoost(BaseModel):
    """A symbol name with boost weight."""
    name: str = Field(min_length=1, description="Symbol name to boost")
    weight: float = Field(default=10.0, gt=0, description="Boost multiplier")


class Focus(BaseModel):
    """Focus configuration for boosting."""
    paths: list[PathBoost] = Field(default_factory=list)
    symbols: list[SymbolBoost] = Field(default_factory=list)


class SectionVerbosity(BaseModel):
    """Verbosity rule for a section within a file."""
    pattern: str = Field(min_length=1, description="Glob pattern for section names")
    level: VerbosityLevel = Field(description="Verbosity level for matching sections")


class VerbosityRule(BaseModel):
    """Verbosity rule for files matching a pattern."""
    pattern: str = Field(min_length=1, description="Glob pattern for file paths")
    level: VerbosityLevel | None = Field(default=None, description="File-level verbosity")
    sections: list[SectionVerbosity] | None = Field(default=None, description="Section-level rules")

    @model_validator(mode="after")
    def validate_level_or_sections(self) -> VerbosityRule:
        if self.level is None and self.sections is None:
            raise ValueError("Either 'level' or 'sections' must be specified")
        return self


class CustomQuery(BaseModel):
    """Custom tree-sitter query for specific paths."""
    pattern: str = Field(min_length=1, description="Glob pattern for file paths")
    query: str = Field(min_length=1, description="Tree-sitter query in .scm format")


class FlightPlan(BaseModel):
    """Complete configuration for a rendering request."""
    budget: int = Field(default=20000, gt=0, description="Token budget limit")
    focus: Focus | None = Field(default=None, description="Focus boosting configuration")
    verbosity: list[VerbosityRule] = Field(default_factory=list)
    custom_queries: list[CustomQuery] = Field(default_factory=list)

    model_config = {"extra": "forbid"}  # Reject unknown fields
```

### Loading Pattern

```python
import yaml
from pydantic import ValidationError

def load_flight_plan(yaml_path: Path) -> FlightPlan:
    """Load and validate a flight plan from YAML."""
    try:
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        return FlightPlan.model_validate(data or {})
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML syntax: {e}") from e
    except ValidationError as e:
        errors = "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors())
        raise ConfigError(f"Invalid configuration: {errors}") from e
```

### Error Handling

| Error Type | Cause | Message Example |
|------------|-------|-----------------|
| `yaml.YAMLError` | YAML syntax | "line 5, column 3: expected ':'" |
| `ValidationError` | Schema mismatch | "budget: Input should be > 0" |
| Missing field | Required field absent | "verbosity.0: Either 'level' or 'sections' must be specified" |

---

## 4. Glob Pattern Matching

### Decision
Use `pathspec` library (already in dependencies) for file path matching; extend for symbol matching.

### Rationale
`pathspec` is already used in `mapper.py` for gitignore-style patterns. Same library can handle verbosity rule patterns.

### Implementation

```python
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

def match_verbosity_level(
    file_path: str,
    rules: list[VerbosityRule],
    default: VerbosityLevel = VerbosityLevel.STRUCTURE,
) -> VerbosityLevel:
    """Find the verbosity level for a file path (last match wins)."""
    level = default
    for rule in rules:
        spec = PathSpec.from_lines(GitWildMatchPattern, [rule.pattern])
        if spec.match_file(file_path):
            level = rule.level
    return level
```

### Symbol Matching (Intra-file)

For section/symbol matching within files, use `fnmatch`:

```python
from fnmatch import fnmatch

def match_section_level(
    symbol_name: str,
    section_rules: list[SectionVerbosity] | None,
    default: VerbosityLevel,
) -> VerbosityLevel:
    """Find verbosity level for a symbol within a file."""
    if not section_rules:
        return default
    level = default
    for rule in section_rules:
        if fnmatch(symbol_name, rule.pattern):
            level = rule.level
    return level
```

---

## Summary of Decisions

| Area | Decision | Key Insight |
|------|----------|-------------|
| PageRank boosting | Use `personalization` parameter | Include ALL nodes with default weight |
| Tree-sitter queries | Capture components, reconstruct | Can't exclude children in query |
| YAML validation | Pydantic `model_validate()` | `extra="forbid"` for strict mode |
| Glob matching | `pathspec` for files, `fnmatch` for symbols | Last match wins for verbosity |
