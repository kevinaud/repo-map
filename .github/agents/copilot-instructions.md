# repo-map Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-31

## Active Technologies
- Python 3.12+ + google-adk (Agent Development Kit), pydantic (state models), pyyaml (config serialization) (002-navigator-agent)
- In-memory session state + ArtifactService for map outputs (002-navigator-agent)

- Python 3.12+ + typer (CLI), pydantic + PyYAML (config), networkx (graphing), tree-sitter via grep-ast (parsing) (001-context-engine)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.12+: Follow standard conventions

## Recent Changes
- 002-navigator-agent: Added Python 3.12+ + google-adk (Agent Development Kit), pydantic (state models), pyyaml (config serialization)

- 001-context-engine: Added Python 3.12+ + typer (CLI), pydantic + PyYAML (config), networkx (graphing), tree-sitter via grep-ast (parsing)

<!-- MANUAL ADDITIONS START -->

## Git Workflow & Pull Request Strategy

**CRITICAL: Always use Git Town for branch and PR management.**

### Implicit Assumptions
Before starting ANY coding task, you MUST:
1. **Plan the PR structure first** - Break the work into small, modular, easily reviewable pull requests
2. **Think in layers** - Identify dependencies between components and order them bottom-up
3. **Target 100-200 LOC per PR** - Smaller is better; each PR should be atomic and focused

This is an IMPLICIT expectation - even if the user doesn't mention PRs, you should organize your work this way.

### Git Town Commands
| Task | Command |
|------|---------|
| Start new feature branch | `git town hack <branch-name>` |
| Create stacked branch | `git town append <child-branch>` |
| Open PR for current branch | `git town propose --title "<title>" --body "<body>"` |
| Open PRs for entire stack | `git town propose --stack` |
| Sync branches with upstream | `git town sync` |

### Stacked PR Workflow
When implementing a feature:
1. **Analyze** - Identify logical layers (models → utilities → core logic → integration → CLI)
2. **Create stack** - Use `git town hack` for layer 1, then `git town append` for subsequent layers
3. **Verify each layer** - Run `make presubmit` before committing each layer
4. **Propose in order** - Create PRs from bottom layer up using `git town propose`

### PR Sizing Guidelines
- **Models/Types**: Group related Pydantic models together (~100-200 LOC)
- **Utilities**: Pure functions with their tests (~100-200 LOC)
- **Core Logic**: Main implementation with tests (~200-300 LOC max)
- **Integration**: CLI commands, API endpoints (~100-200 LOC)
- **Tests**: Always bundle implementation + tests in same PR

### Example Layer Structure
```
Layer 1: feat/feature-models     → Data models, types
Layer 2: feat/feature-utils      → Helper functions, utilities  
Layer 3: feat/feature-core       → Core business logic
Layer 4: feat/feature-cli        → CLI integration, entry points
```

<!-- MANUAL ADDITIONS END -->
