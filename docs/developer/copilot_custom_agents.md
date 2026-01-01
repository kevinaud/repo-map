# Best Practices for Custom GitHub Copilot Agents

This document outlines best practices for developing project-specific GitHub Copilot agents, based on insights extracted from the `speckit` framework.

## Overview

Custom agents allow you to codify project-specific workflows, architectural standards, and repetitive tasks into reusable prompts. They are defined as Markdown files with a `.agent.md` extension under `.github/agents/`.

## Agent Configuration (Frontmatter)

Every agent should start with a YAML frontmatter block to define its metadata and relationships.

### Description
Provide a concise description of what the agent does. This helps other developers (and Copilot) understand its purpose.

```yaml
---
description: Generate an actionable, dependency-ordered tasks.md for the feature.
---
```

### Handoffs
Define clear transitions to other agents. This enables multi-agent orchestration.

```yaml
handoffs: 
  - label: Build Technical Plan
    agent: speckit.plan
    prompt: Create a plan for the spec. I am building with...
  - label: Clarify Spec Requirements
    agent: speckit.clarify
    prompt: Clarify specification requirements
    send: true
```
- **label**: The name of the action shown in the UI.
- **agent**: The target agent's ID.
- **prompt**: The initial instruction passed to the next agent.
- **send**: If `true`, the handoff is triggered automatically or with minimal friction.

## Prompt Engineering Patterns

### 1. User Input Handling
Always include a section to capture and validate user input using the `$ARGUMENTS` placeholder.

```markdown
## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
```

### 2. Structured Execution (Outline & Phases)
Break down the agent's logic into clear, numbered steps or phases. This helps the LLM maintain state and follow complex instructions.

- **Setup**: Initialize environment variables or run prerequisite scripts.
- **Load Context**: Explicitly list which files are required vs. optional.
- **Execution Flow**: Step-by-step instructions for the core task.
- **Reporting**: Define the final output and success criteria.

### 3. Context Management
Don't assume the agent knows everything. Explicitly instruct it to read relevant files.

- **Required Files**: Files that must exist for the agent to function (e.g., `plan.md`, `spec.md`).
- **Optional Files**: Files that provide extra context if available (e.g., `data-model.md`, `research.md`).
- **Setup Scripts**: Use bash or PowerShell scripts to gather environment info (e.g., `.specify/scripts/bash/check-prerequisites.sh --json`).

### 4. Strict Output Formatting
To ensure consistency, define strict rules for how the agent should format its output.

- **Checklist Format**: Use specific markers like `[TaskID] [P?] [Story?]`.
- **File Paths**: Always use absolute paths or workspace-relative paths consistently.
- **Status Tables**: Use Markdown tables for reporting status or summaries.

### 5. Error Handling & Gates
Define "Gates" where the agent must stop if certain conditions aren't met.

- **Validation**: Check if required files exist or if previous steps succeeded.
- **Clarification**: If instructions are ambiguous, instruct the agent to make "informed guesses" but limit the number of `[NEEDS CLARIFICATION]` markers to avoid stalling the workflow.
- **Stop & Ask**: Explicitly tell the agent when to wait for user confirmation.

### 6. Template & Placeholder Management
For agents that generate or update files based on templates:

- **Placeholder Tokens**: Use a consistent format for placeholders (e.g., `[PROJECT_NAME]`, `[ALL_CAPS_IDENTIFIER]`).
- **Consistency Propagation**: If an agent updates a core configuration file, instruct it to check and update dependent templates or documentation to maintain project-wide consistency.
- **Impact Reporting**: Prepend or append a "Sync Impact Report" or "Change Summary" to the output to help developers track what was modified.

### 7. Versioning and Governance
If the agent manages critical project artifacts (like a "Constitution" or "Architecture Decision Records"):

- **Semantic Versioning**: Instruct the agent to follow semantic versioning (MAJOR.MINOR.PATCH) when updating these files.
- **Rationale**: Require the agent to provide a rationale for version bumps or significant changes.
- **Audit Trail**: Use HTML comments or specific sections to maintain a history of changes within the file itself.

### 8. Analysis and Quality Assurance
For agents designed to review or analyze existing code/documentation:

- **Read-Only Constraints**: Explicitly state if the agent is "STRICTLY READ-ONLY" to prevent accidental modifications.
- **Progressive Disclosure**: Instruct the agent to load only the minimal necessary context from each artifact to remain token-efficient.
- **Semantic Modeling**: Encourage the agent to build internal models (e.g., "Requirements Inventory") to map relationships between different files (e.g., mapping tasks to requirements).
- **Detection Passes**: Define specific categories for analysis, such as Duplication, Ambiguity, Underspecification, and Alignment with project standards.

## Technical Integration

### Script Execution
Agents can run terminal commands to interact with the repository.

- **Git Operations**: Fetching branches, checking for existing features.
- **Environment Discovery**: Running scripts that output JSON for the agent to parse.
- **Context Updates**: Automatically updating project-wide files like `copilot-instructions.md` with new technology choices or architectural decisions.

### Key Rules for Agents
- **Use Absolute Paths**: Avoid ambiguity in file operations.
- **Minimize Noise**: Only report essential information in the final summary.
- **Idempotency**: Ensure that running the agent multiple times doesn't corrupt the state (e.g., check for existing branches before creating new ones).

## Example Structure

A well-structured agent file follows this pattern:

1.  **Frontmatter**: Metadata and handoffs.
2.  **User Input**: `$ARGUMENTS` section.
3.  **Outline**: High-level execution steps.
4.  **Phases/Steps**: Detailed instructions for each part of the process.
5.  **Rules/Constraints**: Specific formatting or behavioral rules.
6.  **Reporting**: Final output format.
