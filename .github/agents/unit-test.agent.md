````chatagent
---
description: Generate or improve unit tests following project best practices for ADK-based code with classical testing style.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Create high-quality unit tests that follow the project's testing philosophy: **almost never mock ADK components**, use real in-memory services, and test behavior through public interfaces. Tests must adhere to the classical testing style defined in `docs/developer/unit_testing.md` and the constitution's principles.

## Operating Constraints

- **File Modifications**: May create/update test files in `tests/unit/`
- **Token Efficiency**: Load only necessary source code context
- **Quality First**: All generated tests must pass `make test-unit`
- **Constitution Compliance**: Follow Principle III (Testing Strategy) and Principle IV (Clean Modern Python)

## Execution Steps

### 1. Setup & Context Loading

**Required Files**:
- `docs/developer/unit_testing.md` — Testing patterns and anti-patterns
- `tests/adk_helpers.py` — Available test utilities (`FakeLlm`, context factories)
- `tests/conftest.py` — Existing fixtures

**Optional Files**:
- `.specify/memory/constitution.md` — Project principles (if clarification needed)
- Existing unit tests in `tests/unit/` — For style consistency

**Source Code**: Load the module(s) to be tested based on user input.

Before proceeding:
1. Read `docs/developer/unit_testing.md` to internalize ALL testing patterns
2. Read `tests/adk_helpers.py` to understand available utilities
3. Identify the source file(s) to test from user input
4. Check for existing tests to understand project style

### 2. Analyze Code Under Test

For each module/function/class to test:

1. **Identify Public Interface**: What functions/methods should users call?
2. **Map Dependencies**:
   - ADK services → Use in-memory implementations
   - LLM calls → Use `FakeLlm`
   - External APIs/subprocess → Mock these (the ONLY things to mock)
   - File system → Use `tmp_path` fixture
3. **Determine Test Categories**:
   - State mutations (session state changes)
   - Artifact operations (save/load)
   - Callback behavior (before/after model)
   - Validation logic (Pydantic models)
   - Error handling paths

### 3. Generate Tests

Apply these patterns from `unit_testing.md`:

#### For FunctionTools That Modify State
```python
@pytest.mark.asyncio
async def test_<tool>_updates_state(sample_agent, tmp_path):
    """Tool should <expected behavior>."""
    # Arrange
    initial_state = {
        "navigator_state": {
            # ... minimal required state
        }
    }
    ctx = await create_tool_context(sample_agent, state=initial_state)
    
    # Act
    result = await <tool_function>(ctx, <args>)
    
    # Assert on STATE, not mock calls
    assert ctx.state["navigator_state"]["<key>"] == <expected>
```

#### For FunctionTools That Save Artifacts
```python
@pytest.mark.asyncio
async def test_<tool>_saves_artifact(sample_agent, tmp_path):
    """Tool should save <artifact description>."""
    ctx = await create_tool_context(sample_agent, state={...})
    
    # Act (mock subprocess if calling external CLI)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="...")
        result = await <tool_function>(ctx, ...)
    
    # Assert artifact exists
    artifact_service = ctx._invocation_context.artifact_service
    artifacts = await artifact_service.list_artifact_keys(...)
    assert "<artifact_name>" in artifacts
```

#### For Plugin Callbacks
```python
@pytest.mark.asyncio
async def test_plugin_<behavior>(sample_agent):
    """Plugin should <expected behavior>."""
    state = {...}
    ctx = await create_callback_context(sample_agent, state=state)
    plugin = <PluginClass>()
    
    request = LlmRequest(model="...", contents=[])
    
    # Act
    response = plugin.before_model_callback(ctx, request)
    
    # Assert
    assert response is None  # or check response content
```

#### For Dynamic Instructions
```python
@pytest.mark.asyncio
async def test_instruction_includes_<element>(sample_agent):
    """Instruction should include <element>."""
    state = {...}
    ctx = await create_readonly_context(sample_agent, state=state)
    
    instruction = await <instruction_function>(ctx)
    
    assert "<expected_content>" in instruction
```

#### For Pydantic Model Validation
```python
def test_<model>_validates_<field>():
    """<Model> should reject invalid <field>."""
    with pytest.raises(ValidationError) as exc_info:
        <Model>(<field>=<invalid_value>, ...)
    
    assert "<field>" in str(exc_info.value)
```

### 4. Apply Quality Checks

Before finalizing, verify each test:

| Check | Description |
|-------|-------------|
| ✅ No ADK mocks | Uses `InMemorySessionService`, `InMemoryArtifactService`, etc. |
| ✅ `FakeLlm` for LLM | All LLM responses use `FakeLlm.with_responses([...])` |
| ✅ Tests behavior | Asserts on outcomes (state values, artifacts), NOT mock calls |
| ✅ Real contexts | Uses `create_tool_context`, `create_callback_context`, etc. |
| ✅ Type hints | Test functions have proper signatures |
| ✅ 2-space indent | Follows project style |
| ✅ Descriptive names | `test_<unit>_<expected_behavior>` pattern |
| ✅ Docstrings | Each test has a one-line docstring |

### 5. Write Test File

**File Path**: `tests/unit/test_<module_name>.py`

**Structure**:
```python
"""Unit tests for repo_map.<module>."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch  # Only for external APIs

# ADK imports
from google.adk.agents import LlmAgent
from google.genai import types

# Test utilities
from tests.adk_helpers import (
    FakeLlm,
    create_tool_context,
    create_callback_context,
    create_readonly_context,
)

# Module under test
from repo_map.<module> import <functions_to_test>


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_agent():
    """Create agent for context creation."""
    return LlmAgent(
        name="test_agent",
        model=FakeLlm.with_responses([]),
    )


# ============================================================================
# <Category> Tests
# ============================================================================

class Test<Category>:
    """Tests for <category description>."""

    @pytest.mark.asyncio
    async def test_<specific_behavior>(self, sample_agent, tmp_path):
        """<One-line description>."""
        # Arrange
        ...
        
        # Act
        ...
        
        # Assert
        ...
```

### 6. Validate & Report

1. **Run the tests**: `make test-unit` or target specific file
2. **Check for errors**: `make quality` to verify type hints and style
3. **Report summary**:
   - Number of tests created
   - Test categories covered
   - Any areas needing additional coverage

## Rules & Constraints

### MUST Follow (from unit_testing.md)

1. **Almost Never Mock ADK Components**
   - ✅ Use: `InMemorySessionService`, `InMemoryArtifactService`, `InMemoryMemoryService`
   - ✅ Use: `FakeLlm` for LLM responses
   - ✅ Use: Real `ToolContext`, `CallbackContext`, `ReadonlyContext` via factories
   - ❌ Never: `MagicMock(spec=SessionService)`, `MagicMock(spec=ToolContext)`

2. **Mock Only Two Things**
   - LLM calls → `FakeLlm`
   - External APIs/subprocesses → `unittest.mock.patch`

3. **Test Outcomes, Not Implementation**
   - ❌ Bad: `session_service.update_session.assert_called_once_with(...)`
   - ✅ Good: `assert ctx.state["key"] == expected_value`

4. **Create Real Objects**
   - ❌ Bad: `agent = MagicMock(spec=LlmAgent)`
   - ✅ Good: `agent = LlmAgent(name="test", model=FakeLlm.with_responses([]))`

5. **Use `model_construct` Sparingly**
   - Only for testing error handling of invalid states
   - Never to "avoid fixing test setup"

6. **Verify LLM Requests**
   - Check `fake_llm.requests` to verify prompts include expected content

### MUST Follow (from constitution.md)

1. **Classical Testing Style**: Real dependencies unless they cause unacceptable overhead
2. **Test Behavior Through Public Interfaces**: Not implementation details
3. **Full Type Hints**: All test functions properly annotated
4. **2-Space Indentation**: Project standard
5. **`from __future__ import annotations`**: Required in all files

### Anti-Patterns to AVOID

| Anti-Pattern | Why It's Bad | Correct Approach |
|--------------|--------------|------------------|
| Mocking `SessionService` | Hides real session lifecycle behavior | Use `InMemorySessionService` |
| `MagicMock` for contexts | Loses type safety, accepts typos | Use `create_tool_context()` |
| Patching ADK internals | Couples test to ADK implementation | Mock at boundary with `FakeLlm` |
| `model_construct` abuse | Hides validation bugs | Use `tmp_path` for real paths |
| Assert on mock calls | Tests implementation, not behavior | Assert on state/artifacts |

## Output Format

After generating tests, provide:

1. **File created/modified**: Path to test file
2. **Test summary table**:
   | Test Name | Category | What It Validates |
   |-----------|----------|-------------------|
   | `test_...` | State | ... |
3. **Coverage notes**: Any untested paths or edge cases identified
4. **Run command**: `make test-unit` or specific pytest command

````
