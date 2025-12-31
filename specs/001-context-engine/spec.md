# Feature Specification: Context Engine - Multi-Resolution Rendering

**Feature Branch**: `001-context-engine`  
**Created**: 2025-12-31  
**Status**: Draft  
**Input**: User description: "Build the repo-map ecosystem - a toolchain to solve the Context Bottleneck in AI-assisted development with multi-resolution rendering and token budget management"

---

## Problem Statement

For complex, high-level tasks like system architecture or large-scale refactoring, LLMs fail because they lack the right context. Giving them file names provides too little information; giving them full source code creates too much noise and exceeds token limits.

The solution is a two-layer architecture:
- **Layer 1 (The Engine)**: A deterministic rendering tool that accepts a strict Token Budget and precise rendering instructions
- **Layer 2 (The Navigator)**: An intelligent agent that iteratively explores the codebase, using the Engine to "zoom in/out" on components

**This specification focuses on Layer 1 (The Engine) to support Layer 2.**

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Multi-Resolution Rendering (Priority: P1)

As a Navigator agent, I want to request different verbosity levels for different parts of the codebase so that I can fit the most relevant context within my token budget.

**Why this priority**: This is the core capability that enables the "zoom in/zoom out" paradigm. Without multi-resolution rendering, the engine cannot serve the Navigator's primary use case.

**Independent Test**: Can be fully tested by providing a codebase and verbosity instructions, then verifying the output matches the requested detail levels and stays within budget.

**Acceptance Scenarios**:

1. **Given** a codebase with source files, **When** I request Level 4 (full content) for `src/core/` and Level 1 (path only) for `tests/`, **Then** the output shows full source for core files and only file paths for test files
2. **Given** a codebase with mixed file types, **When** I request Level 3 (interface) for Python files, **Then** the output shows function/class definitions with signatures and docstrings, but not implementation bodies
3. **Given** a token budget of 5000 tokens, **When** verbosity instructions would exceed that budget, **Then** the lowest-ranked files are automatically truncated to enforce the limit

---

### User Story 2 - Cost Prediction for Budget Planning (Priority: P1)

As a Navigator agent, I want to know the token cost of each file at every verbosity level so that I can mathematically plan my context window without trial and error.

**Why this priority**: The Navigator cannot make intelligent zoom decisions without knowing the "price" of each option. This enables the core tradeoff calculations (e.g., "drop tests to Level 1 to afford Level 4 on core").

**Independent Test**: Can be fully tested by requesting metadata for a set of files and verifying accurate token counts are returned for all 5 verbosity levels per file.

**Acceptance Scenarios**:

1. **Given** a source file, **When** I request cost metadata, **Then** I receive token estimates for Levels 0-4 for that file
2. **Given** a directory, **When** I request aggregate cost metadata, **Then** I receive summed token estimates for all files at each verbosity level
3. **Given** the cost metadata, **When** I calculate "current budget minus Level 1 costs plus Level 3 costs", **Then** the result accurately predicts the actual output size

---

### User Story 3 - Markdown Documentation Rendering (Priority: P1)

As a Navigator agent, I want to include markdown documentation in my context window with the same multi-resolution control as source code so that I can provide the LLM with relevant documentation alongside code.

**Why this priority**: Documentation (READMEs, architecture docs, API guides) is critical context for understanding codebases. Without robust markdown support, the Navigator cannot provide complete context.

**Independent Test**: Can be fully tested by providing markdown files and verifying correct rendering at each verbosity level with proper section extraction.

**Acceptance Scenarios**:

1. **Given** a markdown file with multiple sections, **When** I request Level 2 (structure), **Then** I see the heading hierarchy (H1, H2, H3) without body content
2. **Given** a markdown file, **When** I request Level 3 (interface), **Then** I see headings plus first paragraph/summary of each section
3. **Given** a markdown file, **When** I request Level 4 (full), **Then** I see the complete content including code blocks and lists

---

### User Story 4 - Intra-File Section Control (Priority: P2)

As a Navigator agent, I want to specify different verbosity levels for different sections within a single file so that I can extract exactly the portions I need from long documents.

**Why this priority**: Long documentation files and large source files contain mixed relevance content. Section-level control enables precise extraction without wasting tokens on irrelevant sections within relevant files.

**Independent Test**: Can be fully tested by specifying section-level verbosity for a file and verifying only the requested sections appear at the requested detail levels.

**Acceptance Scenarios**:

1. **Given** a markdown file with sections "Overview", "Installation", "API Reference", **When** I request Level 4 for "API Reference" and Level 0 for others, **Then** only the API Reference content appears in full
2. **Given** a source file with multiple classes, **When** I request Level 4 for class `UserAuth` and Level 2 for other classes, **Then** I see full implementation of UserAuth and only definitions for others
3. **Given** a markdown file, **When** I request "H1-H3 headings only" for one section, **Then** I see nested heading structure without body content for that section

---

### User Story 5 - Symbol Boosting for Focused Analysis (Priority: P2)

As a Navigator agent, I want to boost specific symbols or paths in the ranking algorithm so that the PageRank prioritization reflects my current investigation focus.

**Why this priority**: The default PageRank identifies generally "central" files, but the Navigator often needs to prioritize specific areas relevant to the current task. Boosting enables steering without overriding the entire ranking.

**Independent Test**: Can be fully tested by providing focus symbols, running ranking, and verifying boosted items appear higher than they would with default ranking.

**Acceptance Scenarios**:

1. **Given** a codebase where `utils.py` ranks low by default, **When** I add `utils.py` to Focus Paths, **Then** it appears in the top tier of results
2. **Given** a function `authenticate()` in a large file, **When** I add it to Focus Symbols, **Then** files referencing or defining `authenticate` rank higher
3. **Given** multiple Focus items, **When** I assign different boost weights, **Then** higher-weighted items influence ranking proportionally more

---

### User Story 6 - YAML Configuration for Complex Queries (Priority: P2)

As a Navigator agent, I want to express complex rendering instructions in a YAML configuration file so that I can specify detailed requirements without command-line complexity.

**Why this priority**: Complex queries with per-file verbosity, section selections, and custom queries cannot be practically expressed via CLI flags. YAML enables the Navigator to construct sophisticated "flight plans."

**Independent Test**: Can be fully tested by providing a YAML config and verifying the output matches all specified requirements.

**Acceptance Scenarios**:

1. **Given** a YAML file specifying token budget, focus list, and verbosity map, **When** I run the CLI with this config, **Then** output reflects all settings
2. **Given** a YAML file with section-level verbosity for specific files, **When** processed, **Then** intra-file sections are rendered at their specified levels
3. **Given** conflicting settings (CLI flag vs YAML), **When** processed, **Then** CLI flags take precedence over YAML defaults

---

### User Story 7 - Custom Tree-sitter Queries (Priority: P3)

As a power user, I want to inject custom Tree-sitter queries for specific paths so that I can extract domain-specific patterns (e.g., "show me only SQL strings in these Python files").

**Why this priority**: Enables advanced use cases beyond standard verbosity levels. Lower priority because standard levels cover most needs.

**Independent Test**: Can be fully tested by providing a custom query and verifying only matching AST nodes are extracted.

**Acceptance Scenarios**:

1. **Given** a custom query targeting string literals containing "SELECT", **When** applied to Python files, **Then** only SQL query strings are extracted
2. **Given** a custom query for "TODO comments", **When** applied, **Then** only TODO/FIXME comments are extracted from matched files
3. **Given** an invalid custom query, **When** processed, **Then** a clear error message identifies the syntax problem

---

### Edge Cases

- What happens when a file has no AST parser available? → Fall back to full text or line-based truncation
- How does the system handle binary files? → Exclude automatically, show only path at Level 1
- What happens when section markers are ambiguous in markdown? → Use closest heading hierarchy interpretation
- How does intra-file selection work for minified/single-line files? → Graceful degradation to file-level verbosity
- What happens when Focus Symbols don't exist in the codebase? → Warn but continue with remaining valid symbols
- How are circular dependencies handled in boosted ranking? → Standard PageRank damping factor prevents infinite loops

---

## Requirements *(mandatory)*

### Functional Requirements

#### Analysis & Graphing (Existing + Enhanced)

- **FR-001**: System MUST scan directories respecting `.gitignore` and user-provided glob patterns *(implemented)*
- **FR-002**: System MUST extract definitions and references via AST parsing for source code *(implemented)*
- **FR-003**: System MUST extract heading structure and sections from markdown files
- **FR-004**: System MUST build a dependency graph including both code references and documentation links
- **FR-005**: System MUST use PageRank algorithm to identify central files *(implemented)*
- **FR-006**: System MUST accept "Focus Symbols" list to artificially boost specific symbol nodes before ranking
- **FR-007**: System MUST accept "Focus Paths" list to artificially boost specific file/directory nodes before ranking
- **FR-008**: System MUST allow configurable boost weights for Focus items

#### Multi-Resolution Rendering

- **FR-009**: System MUST support 5 explicit verbosity levels for files:
  - Level 0 (Exclude): Hidden entirely from output
  - Level 1 (Existence): File path only
  - Level 2 (Structure): Top-level definitions/headings only
  - Level 3 (Interface): Definitions + Signatures + Docstrings/Summaries
  - Level 4 (Implementation): Full raw content
- **FR-010**: System MUST apply verbosity levels via glob pattern matching (e.g., `src/db/*: Level 4`)
- **FR-011**: System MUST support intra-file section selection using glob patterns matched against tree-sitter symbol tags
- **FR-012**: Intra-file glob patterns MUST work uniformly for both source code symbols (classes, functions) and markdown headings
- **FR-013**: System MUST allow different verbosity levels for different sections within the same file
- **FR-014**: System MUST dynamically load appropriate extraction logic based on requested verbosity level

#### Budget Management & Cost Prediction

- **FR-015**: System MUST accept a global token budget limit
- **FR-016**: System MUST calculate and expose token cost estimates for every file at all 5 verbosity levels
- **FR-017**: System MUST calculate and expose token cost estimates for intra-file sections where applicable
- **FR-018**: System MUST provide aggregate cost summaries for directories/glob patterns
- **FR-019**: By default, System MUST render all requested content even if exceeding budget, appending a prominent warning showing the overrun amount
- **FR-020**: System MUST support a `--strict` flag that rejects requests exceeding the token budget with an error (for final output use)
- **FR-021**: System MUST report actual token count vs budget in output (when budget is specified)

#### Configuration & Control

- **FR-022**: System MUST accept a YAML configuration file ("flight plan") containing:
  - Global token budget
  - Focus symbols/paths with optional weights
  - Verbosity level map (glob pattern → level)
  - Intra-file section specifications
  - Custom Tree-sitter queries for specific paths
- **FR-023**: System MUST validate YAML configuration and report clear errors for invalid syntax/semantics
- **FR-024**: System MUST allow CLI flags to override YAML settings
- **FR-025**: System MUST support custom Tree-sitter queries for extracting domain-specific patterns (valid .scm syntax)

#### Output Composition

- **FR-026**: System MUST produce deterministic output for identical inputs
- **FR-027**: System MUST support optional inline cost annotations per file in succinct format (e.g., `# file.py [L1:50 L2:120 L3:340 L4:890]`)
- **FR-028**: System MUST provide a flag to enable/disable cost annotations in output (disabled by default for final renders)
- **FR-029**: System MUST clearly delineate file boundaries and verbosity levels in output
- **FR-030**: System MUST output valid, parseable format suitable for LLM consumption

### Key Entities

- **File Node**: Represents a file in the codebase; attributes include path, language/type, token costs at each level, current rank score
- **Symbol**: Represents a code definition (function, class, variable); attributes include name, kind, location, signature, docstring
- **Section**: Represents a document section (markdown heading or code block); attributes include heading/name, level, line range, token cost
- **Verbosity Instruction**: Maps a pattern (glob or section path) to a verbosity level (0-4)
- **Flight Plan**: Complete configuration document containing budget, focus items, verbosity map, and custom queries
- **Cost Manifest**: Metadata structure containing token costs for all files/sections at all verbosity levels

---

## Assumptions

- Token estimation uses the existing heuristic of `len(text) // 4` characters per token (can be refined later)
- Markdown headings are extracted as tree-sitter symbol tags, enabling unified glob-based section addressing
- Intra-file section boundaries are determined by tree-sitter symbol spans (works for both code and markdown)
- The Navigator (Layer 2) is responsible for constructing valid YAML configurations; the Engine validates but does not auto-correct
- Focus boosting modifies the PageRank personalization vector rather than post-ranking reordering
- Custom Tree-sitter queries are provided in standard `.scm` syntax

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Navigator can request and receive accurate context within ±5% of specified token budget
- **SC-002**: Cost prediction metadata enables Navigator to plan context windows with <10% estimation error
- **SC-003**: Multi-resolution output for a 10,000-file repository generates in under 30 seconds
- **SC-004**: 100% of markdown files with standard heading structure are correctly parsed into sections
- **SC-005**: Intra-file section selection reduces token usage by 50%+ compared to file-level selection for long documents
- **SC-006**: Focus boosting measurably increases rank of targeted symbols (top 20% → top 5% tier)
- **SC-007**: YAML flight plans with 50+ verbosity rules are processed without performance degradation
- **SC-008**: Output is deterministic: identical inputs produce byte-identical outputs across runs

---

## Clarifications

### Session 2025-12-31

- Q: What format should cost metadata use in output? → A: Succinct inline comments (e.g., `# file.py [L1:50 L2:120 L3:340 L4:890]`) to minimize token overhead
- Q: Should cost metadata always be included? → A: No, provide a toggle flag to enable/disable since final output doesn't need it
- Q: How should budget overruns be handled? → A: Default: render fully with prominent warning showing overrun amount; `--strict` flag rejects if exceeded (for final output)
- Q: How should intra-file sections be addressed? → A: Glob patterns matched against tree-sitter symbol tags (unified for both code symbols and markdown headings)

---

## Out of Scope

- Layer 2 (Navigator Agent) implementation - this spec covers only the Engine
- IDE/editor integrations
- Real-time file watching or incremental updates
- Multi-language support beyond currently supported Tree-sitter languages
- Semantic understanding of code (e.g., "find all authentication-related functions")
- Git history or blame integration
