````chatagent
---
description: Create a new project-specific GitHub Copilot agent following documented best practices, which can be found at docs/developer/copilot_custom_agents.md
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Guide the user through creating a well-structured, project-specific GitHub Copilot agent that follows the documented best practices in `docs/developer/copilot_custom_agents.md`.

## Execution Steps

### 1. Clarify Agent Purpose

If `$ARGUMENTS` is empty or vague, ask up to THREE targeted questions:

| Question | Purpose |
|----------|---------|
| What task should this agent automate? | Define the core workflow |
| Is this agent read-only (analysis) or does it modify files? | Determine operating constraints |
| Should this agent hand off to other agents when done? | Plan orchestration |

Skip questions if answers are evident from `$ARGUMENTS`.

### 2. Gather Requirements

From user input, extract:
- **Agent Name**: Short, descriptive identifier (e.g., `code-review`, `api-docs`, `test-gen`)
- **Description**: One-line summary for the frontmatter
- **Operating Mode**: Read-only analysis OR file modification
- **Input Files**: Required vs. optional context files
- **Output**: What the agent produces (files, reports, summaries)
- **Handoffs**: Other agents this should connect to (if any)

### 3. Generate Agent Structure

Create the agent file at `.github/agents/{agent-name}.agent.md` using this template:

```markdown
````chatagent
---
description: {one-line description of what the agent does}
handoffs:                          # OPTIONAL - remove if no handoffs needed
  - label: {Action Label}
    agent: {target.agent}
    prompt: {initial instruction for target agent}
    send: true                     # OPTIONAL - auto-trigger handoff
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

{2-3 sentence description of the agent's purpose and expected outcome}

## Operating Constraints

{Define behavioral boundaries, e.g.:}
- **STRICTLY READ-ONLY**: Do not modify any files. Output analysis only.
- **File Modifications**: May create/update files in {specific directories}.
- **Token Efficiency**: Load only necessary context; summarize large files.

## Execution Steps

### 1. Setup & Context Loading

- **Required Files**: {list files that MUST exist}
- **Optional Files**: {list files that provide additional context if present}
- Validate prerequisites exist before proceeding.
- Use absolute paths for all file operations.

### 2. Core Workflow

{Numbered steps describing the main logic}

1. {Step 1}
2. {Step 2}
3. {Step 3}

### 3. Output Generation

{Define the exact output format}

- **File Path**: {where to write output, if applicable}
- **Format**: {Markdown table, checklist, prose, etc.}
- **Validation**: {any post-generation checks}

### 4. Reporting

Summarize execution:
- {Key metric 1}
- {Key metric 2}
- {Any follow-up actions needed}

## Rules & Constraints

- {Rule 1: e.g., "Use absolute paths for all file references"}
- {Rule 2: e.g., "Limit output to 50 findings; summarize overflow"}
- {Rule 3: e.g., "Mark ambiguous items with [NEEDS CLARIFICATION]"}

````
```

### 4. Customize for Use Case

Based on the agent's purpose, include relevant patterns:

| Agent Type | Include These Patterns |
|------------|------------------------|
| **Analysis/Review** | Read-only constraint, semantic modeling, detection passes, severity levels |
| **Code Generation** | File path validation, idempotency checks, format rules |
| **Documentation** | Template placeholders, consistency propagation, version tracking |
| **Orchestration** | Handoffs, prerequisite gates, phased execution |
| **Checklist/Validation** | Numbered items (CHK001), pass/fail criteria, coverage mapping |

### 5. Validate Agent Quality

Before finalizing, verify the agent includes:

- [ ] Clear `description` in frontmatter
- [ ] `$ARGUMENTS` handling section
- [ ] Explicit operating constraints (read-only vs. modification)
- [ ] Required vs. optional context files listed
- [ ] Numbered execution steps
- [ ] Defined output format
- [ ] Error handling / gate conditions
- [ ] Rules section for edge cases

### 6. Write and Report

1. Write the agent file to `.github/agents/{agent-name}.agent.md`
2. Output a summary:
   - Agent name and file path
   - Description
   - Key capabilities
   - Suggested test invocation: `@workspace /agent-name {test input}`

## Rules & Constraints

- **Naming Convention**: Use lowercase kebab-case for agent names (e.g., `code-review`, `api-docs`)
- **File Location**: All agents MUST be created in `.github/agents/`
- **Extension**: Agent files MUST use `.agent.md` extension
- **Frontmatter**: MUST start with ````chatagent and include `---` delimited YAML
- **No Hallucination**: Only include patterns relevant to the user's stated purpose
- **Idempotency**: Check if agent file already exists; ask before overwriting

## Examples

**Example 1: Analysis Agent**
```
User: Create an agent that reviews PR descriptions for completeness
Agent Name: pr-review
Operating Mode: Read-only
Output: Markdown report with findings
```

**Example 2: Generation Agent**
```
User: Create an agent that generates API documentation from code
Agent Name: api-docs
Operating Mode: File modification (creates docs/)
Output: OpenAPI spec + Markdown docs
Handoffs: None
```

**Example 3: Orchestration Agent**
```
User: Create an agent that runs our full release checklist
Agent Name: release-gate
Operating Mode: Read-only analysis, then handoff
Output: Pass/fail summary
Handoffs: deploy.agent if all checks pass
```

````
