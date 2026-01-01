# Contract: CLI Navigate Interface

**Date**: December 31, 2025  
**Feature**: 002-navigator-agent

---

## Overview

The `navigate` command provides an intelligent exploration interface that uses the Navigator agent to automatically discover and construct optimal context windows.

## Command Signature

```bash
repo-map navigate <path> --goal <goal> [options]
```

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `path` | Path | Yes | Root directory to explore |

## Options

### Required Options

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--goal` | `-g` | str | The user's task or goal description |

### Budget Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--tokens` | `-t` | int | 20000 | Maximum token budget for context |
| `--cost-limit` | `-$` | float | 2.0 | Maximum USD to spend on exploration |
| `--model` | `-m` | str | gemini-2.0-flash | LLM model for Navigator agent |

### Execution Mode Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--interactive` | flag | False | Run in interactive step-by-step mode |
| `--max-iterations` | int | 20 | Maximum exploration iterations |

### Output Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | Path | None | Write final context to file |
| `--flight-plan` | `-f` | Path | None | Save final FlightPlan YAML |
| `--copy` | `-c` | flag | False | Copy final context to clipboard |
| `--quiet` | `-q` | flag | False | Suppress progress output |
| `--verbose` | `-v` | flag | False | Show detailed agent reasoning (includes full Turn Reports in interactive mode) |

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success - context generated (includes partial results from budget exhaustion) |
| 1 | Budget exhausted with zero useful output |
| 2 | Invalid configuration |
| 3 | Repository not found |
| 4 | Agent error |
| 5 | User cancelled (interactive mode) |

## Examples

### Basic Usage

```bash
# Autonomous exploration with default settings
repo-map navigate . --goal "Understand the authentication system"

# With custom token budget
repo-map navigate /path/to/repo -g "Refactor the API layer" -t 30000

# With cost limit
repo-map navigate . -g "Debug payment processing" --cost-limit 1.0
```

### Interactive Mode

```bash
# Step-by-step exploration
repo-map navigate . -g "Add caching to database queries" --interactive

# Interactive with verbose reasoning
repo-map navigate . -g "Fix memory leak" --interactive --verbose
```

### Output Options

```bash
# Save context to file
repo-map navigate . -g "Review security" -o context.md

# Save both context and flight plan
repo-map navigate . -g "Optimize queries" -o context.md -f plan.yaml

# Copy to clipboard
repo-map navigate . -g "Add logging" --copy
```

## Output Formats

### Standard Output (Autonomous Mode)

```
Navigator: Exploring repository for "Understand the authentication system"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Initial scan (satellite view)
  → Found 342 files, 85,000 estimated tokens
  
Step 2: Zooming in on src/auth/, src/middleware/
  → Increased verbosity: 12 files to L4
  → Current: 15,200 tokens (76% of budget)
  
Step 3: Zooming out on tests/, docs/
  → Decreased verbosity: 45 files to L1
  → Current: 12,800 tokens (64% of budget)
  
Step 4: Finalizing context
  → Final: 12,800 tokens | 47 files | $0.0024 spent

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reasoning Summary:
Focused on authentication-related code in src/auth/ and middleware/.
Included JWT handling, session management, and OAuth providers.
Excluded test files and documentation to maximize code visibility.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Context output follows or written to file]
```

### Interactive Mode Output

```
Navigator: Interactive exploration for "Understand the authentication system"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────────────────────────┐
│ TURN REPORT - Step 2                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ Cost this turn:    $0.0012                                              │
│ Total cost:        $0.0024 / $2.00 (0.1%)                               │
│ Map size:          15,200 tokens (76% of 20,000)                        │
│ Files included:    47                                                    │
│                                                                         │
│ Focus areas:                                                            │
│   • src/auth/ (L4 - full implementation)                                │
│   • src/middleware/auth.py (L4 - full implementation)                   │
│                                                                         │
│ Last action: Increased verbosity on auth-related files                  │
│                                                                         │
│ Reasoning: "The user wants to understand authentication.                │
│ I've zoomed in on src/auth/ which contains JWT handling,                │
│ session management, and the main auth middleware."                      │
└─────────────────────────────────────────────────────────────────────────┘

Continue exploration? [y/N/feedback]: 
```

### Final Output Structure

When `--output` is specified, the file contains:

```markdown
# Repository Context: [repo-name]

**Goal**: Understand the authentication system  
**Generated**: 2025-12-31T10:45:00Z  
**Tokens**: 12,800 | **Files**: 47 | **Cost**: $0.0024

## Reasoning Summary

Focused on authentication-related code in src/auth/ and middleware/.
Included JWT handling, session management, and OAuth providers.
Excluded test files and documentation to maximize code visibility.

---

## Repository Map

[rendered context map content]
```

When `--flight-plan` is specified:

```yaml
# Generated by Navigator Agent
# Goal: Understand the authentication system
# Generated: 2025-12-31T10:45:00Z
budget: 20000
focus:
  paths:
    - pattern: "src/auth/**"
      weight: 10.0
verbosity:
  - pattern: "src/auth/**"
    level: 4
  - pattern: "src/middleware/auth.py"
    level: 4
  - pattern: "tests/**"
    level: 1
  - pattern: "docs/**"
    level: 0
```
