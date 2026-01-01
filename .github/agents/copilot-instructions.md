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
<!-- MANUAL ADDITIONS END -->
