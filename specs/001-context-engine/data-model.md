# Data Model: Context Engine

**Date**: 2025-12-31  
**Feature**: 001-context-engine

---

## Entities

### VerbosityLevel (Enum)

Defines the detail level for rendering content.

| Value | Name | Description |
|-------|------|-------------|
| 0 | EXCLUDE | Hidden entirely from output |
| 1 | EXISTENCE | File/section path only |
| 2 | STRUCTURE | Top-level definitions/headings only |
| 3 | INTERFACE | Definitions + Signatures + Docstrings |
| 4 | IMPLEMENTATION | Full raw content |

### FileNode

Represents a file in the codebase with cost metadata.

| Attribute | Type | Description |
|-----------|------|-------------|
| path | str | Relative path from repository root |
| abs_path | str | Absolute path to file |
| language | str \| None | Detected language (e.g., "python", "markdown") |
| rank_score | float | PageRank score (0.0-1.0) |
| costs | dict[VerbosityLevel, int] | Token cost at each verbosity level |
| sections | list[Section] | Extracted sections (for intra-file control) |

### Section

Represents a section within a file (code symbol or markdown heading).

| Attribute | Type | Description |
|-----------|------|-------------|
| name | str | Section identifier (function name, heading text) |
| kind | str | Type: "class", "function", "heading", etc. |
| line_start | int | Starting line number (1-indexed) |
| line_end | int | Ending line number (1-indexed) |
| level | int | Nesting level (0=top, 1=nested, etc. or heading level 1-6) |
| costs | dict[VerbosityLevel, int] | Token cost at each verbosity level |
| signature | str \| None | Function/method signature (for code) |
| docstring | str \| None | Associated docstring/summary |

### Symbol

Represents a code definition for focus boosting.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | str | Symbol identifier |
| kind | str | Type: "def", "class", "function", "method" |
| file_path | str | File containing this symbol |
| line | int | Line number of definition |

### FlightPlan

Complete configuration for a rendering request.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| budget | int | 20000 | Token budget limit |
| focus | Focus \| None | None | Focus boosting configuration |
| verbosity | list[VerbosityRule] | [] | Verbosity rules (pattern → level) |
| custom_queries | list[CustomQuery] | [] | Custom tree-sitter queries |

### Focus

Configuration for symbol/path boosting.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| paths | list[PathBoost] | [] | File/directory patterns to boost |
| symbols | list[SymbolBoost] | [] | Symbol names to boost |

### PathBoost

A file/directory path with boost weight.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| pattern | str | (required) | Glob pattern for paths |
| weight | float | 10.0 | Boost multiplier (must be >0) |

### SymbolBoost

A symbol name with boost weight.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| name | str | (required) | Symbol name to boost |
| weight | float | 10.0 | Boost multiplier (must be >0) |

### VerbosityRule

Maps a file pattern to a verbosity level.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| pattern | str | (required) | Glob pattern for file paths |
| level | VerbosityLevel \| None | None | File-level verbosity |
| sections | list[SectionVerbosity] \| None | None | Section-level rules |

**Constraint**: Either `level` or `sections` must be specified.

### SectionVerbosity

Verbosity rule for a section within a file.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| pattern | str | (required) | Glob pattern for section names |
| level | VerbosityLevel | (required) | Verbosity level for matches |

### CustomQuery

Custom tree-sitter query for specific paths.

| Attribute | Type | Description |
|-----------|------|-------------|
| pattern | str | Glob pattern for file paths |
| query | str | Tree-sitter query in .scm format |

### CostManifest

Metadata structure for cost prediction.

| Attribute | Type | Description |
|-----------|------|-------------|
| files | dict[str, dict[VerbosityLevel, int]] | Per-file costs at each level |
| total | dict[VerbosityLevel, int] | Aggregate costs at each level |
| budget | int | Configured budget |
| actual | int | Actual tokens used |
| overrun | int | Amount over budget (0 if under) |

---

## Relationships

```
FlightPlan
├── Focus
│   ├── PathBoost[]
│   └── SymbolBoost[]
├── VerbosityRule[]
│   └── SectionVerbosity[]
└── CustomQuery[]

FileNode
├── Section[] (children)
└── costs: {Level → tokens}

CostManifest
├── files: {path → {Level → tokens}}
└── total: {Level → tokens}
```

---

## State Transitions

### Rendering Pipeline

```
Input                    Processing               Output
─────                    ──────────               ──────

FlightPlan ──┐
             ├──► RepoMap.analyze() ──► FileNode[]
Files ───────┘       │
                     ▼
              PageRank + Boosting
                     │
                     ▼
              ContextRenderer.render()
                     │
                     ├──► Rendered content (stdout)
                     └──► CostManifest (metadata)
```

### File Processing States

```
DISCOVERED → PARSED → RANKED → RENDERED
    │          │        │          │
    │          │        │          └─ Content at requested verbosity
    │          │        └─ PageRank score assigned
    │          └─ AST extracted, sections identified
    └─ File path known, basic metadata
```

---

## Validation Rules

### FlightPlan

1. `budget` must be > 0
2. `verbosity` rules: each must have either `level` OR `sections`, not both/neither
3. `custom_queries`: query must be valid .scm syntax
4. Unknown fields are rejected (`extra="forbid"`)

### VerbosityRule

1. `pattern` must be non-empty
2. If `sections` specified, each section rule must have valid `level`
3. Section patterns match against tree-sitter symbol names

### Focus

1. `paths[].pattern` must be valid glob
2. `paths[].weight` must be > 0
3. `symbols[].name` must be non-empty
4. `symbols[].weight` must be > 0
