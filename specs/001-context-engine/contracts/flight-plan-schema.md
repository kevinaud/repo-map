# Flight Plan YAML Schema

Version: 1.0  
Feature: 001-context-engine

---

## Overview

The Flight Plan is a YAML configuration file that specifies how the Context Engine should render a repository map. It controls the token budget, focus boosting, verbosity levels, and custom queries.

## Schema

```yaml
# Flight Plan Schema v1.0

# Token budget (default: 20000)
budget: <positive integer>

# Focus boosting configuration (optional)
focus:
  # Boost specific file/directory paths
  paths:
    - pattern: <glob pattern>   # e.g., "src/core/**"
      weight: <float>           # default: 10.0, must be > 0
  
  # Boost specific symbol names
  symbols:
    - name: <string>            # e.g., "authenticate"
      weight: <float>           # default: 10.0, must be > 0

# Verbosity rules (applied in order, last match wins)
verbosity:
  # File-level verbosity
  - pattern: <glob pattern>     # e.g., "src/**/*.py"
    level: <0-4>                # 0=exclude, 1=path, 2=structure, 3=interface, 4=full
  
  # Section-level verbosity (for intra-file control)
  - pattern: <glob pattern>     # e.g., "docs/api.md"
    sections:
      - pattern: <glob pattern> # Matched against section/symbol names
        level: <0-4>

# Custom tree-sitter queries (optional, advanced)
custom_queries:
  - pattern: <glob pattern>     # e.g., "src/db/**/*.py"
    query: <scm query string>   # e.g., "(string) @sql"
```

## Verbosity Levels

| Level | Name | Rendered Content |
|-------|------|------------------|
| 0 | EXCLUDE | Nothing (file hidden) |
| 1 | EXISTENCE | File path only |
| 2 | STRUCTURE | Top-level definitions/headings |
| 3 | INTERFACE | Definitions + signatures + docstrings |
| 4 | IMPLEMENTATION | Full raw content |

## Examples

### Minimal

```yaml
budget: 10000
```

### Basic Verbosity Control

```yaml
budget: 15000
verbosity:
  - pattern: "src/**/*.py"
    level: 3  # Interface view of all source
  - pattern: "tests/**"
    level: 1  # Just file paths for tests
  - pattern: "**/*.md"
    level: 2  # Heading structure for docs
```

### Focus Boosting

```yaml
budget: 20000
focus:
  paths:
    - pattern: "src/core/**"
      weight: 10.0
    - pattern: "src/auth/**"
      weight: 5.0
  symbols:
    - name: "authenticate"
      weight: 15.0
    - name: "UserSession"
      weight: 10.0
verbosity:
  - pattern: "**/*.py"
    level: 3
```

### Intra-File Section Control

```yaml
budget: 8000
verbosity:
  # Full API reference, structure only for rest
  - pattern: "docs/README.md"
    sections:
      - pattern: "API Reference*"
        level: 4  # Full content
      - pattern: "Installation*"
        level: 3  # Summary only
      - pattern: "*"
        level: 0  # Hide everything else
  
  # Full implementation of auth class, interface for others
  - pattern: "src/auth.py"
    sections:
      - pattern: "UserAuth*"
        level: 4
      - pattern: "*"
        level: 2
```

### Custom Query (Advanced)

```yaml
budget: 5000
custom_queries:
  - pattern: "src/db/**/*.py"
    query: |
      (call
        function: (attribute
          attribute: (identifier) @method)
        arguments: (argument_list
          (string) @sql_query)
        (#match? @method "execute|query|raw"))
verbosity:
  - pattern: "src/db/**/*.py"
    level: 2  # Structure + custom SQL extraction
```

## Validation Rules

1. **budget**: Must be positive integer
2. **focus.paths[].pattern**: Non-empty glob pattern
3. **focus.paths[].weight**: Positive float (default: 10.0)
4. **focus.symbols[].name**: Non-empty string
5. **focus.symbols[].weight**: Positive float (default: 10.0)
6. **verbosity[].pattern**: Non-empty glob pattern
7. **verbosity[].level** OR **verbosity[].sections**: One must be specified
8. **verbosity[].sections[].pattern**: Non-empty glob pattern
9. **verbosity[].sections[].level**: Integer 0-4
10. **custom_queries[].query**: Valid tree-sitter .scm syntax
11. **Unknown fields**: Rejected (strict mode)

## Error Messages

| Error | Example Message |
|-------|-----------------|
| Missing required field | `verbosity.0: Either 'level' or 'sections' must be specified` |
| Invalid type | `budget: Input should be a valid integer` |
| Out of range | `verbosity.0.level: Input should be less than or equal to 4` |
| Empty string | `focus.paths.0.pattern: String should have at least 1 character` |
| Unknown field | `Extra inputs are not permitted: 'unknown_field'` |
