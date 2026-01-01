# Unit Testing ADK-Based Code

This document establishes our testing philosophy and patterns for code built on the Google Agent Development Kit (ADK). These practices are derived from studying ADK's own test suite and are designed to produce **reliable, maintainable tests** that catch real bugs.

> **Note:** For integration tests with real LLMs, see [integration_testing.md](integration_testing.md).
> Import unit test helpers from `tests/adk_helpers.py`, NOT from `tests/integration/helpers.py`.

---

## Philosophy: Almost Never Mock

Our core testing principle is **almost never mock ADK components**. ADK provides in-memory implementations of all core services specifically designed for testing. Use them.

### Why This Matters

Mocking ADK internals creates **brittle tests** that:

1. **Test implementation, not behavior** — Mocks encode assumptions about how ADK works internally. When ADK evolves, mocked tests pass while real code breaks.

2. **Miss integration bugs** — Real `InMemorySessionService` handles state serialization, session lookup, and error cases. A `MagicMock` returns whatever you tell it to.

3. **Create maintenance burden** — Every ADK upgrade requires auditing mock setups to ensure they still reflect reality.

### The Two Things You Should Mock

| Mock This | Why |
|-----------|-----|
| **LLM calls** | External API, slow, costly, non-deterministic. Use `FakeLlm` (see below). |
| **External APIs/subprocesses** | Network calls, file system operations outside test fixtures. |

### The Things You Should NOT Mock

| Don't Mock This | Use This Instead |
|-----------------|------------------|
| `SessionService` | `InMemorySessionService` |
| `ArtifactService` | `InMemoryArtifactService` |
| `MemoryService` | `InMemoryMemoryService` |
| `ToolContext` | Create real one from `InvocationContext` |
| `CallbackContext` | Create real one from `InvocationContext` |
| `ReadonlyContext` | Create real one from `InvocationContext` |
| `InvocationContext` | Build with in-memory services |
| `Session` | Create via `InMemorySessionService.create_session()` |
| State dict access | Use real session state |

---

## ADK In-Memory Services

ADK provides production-quality in-memory implementations. Import them directly:

```python
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
```

These are **not test doubles** — they're fully functional implementations suitable for:
- Unit tests
- Local development
- Lightweight deployments

### Service Characteristics

| Service | Storage | Thread-Safe | Persistence |
|---------|---------|-------------|-------------|
| `InMemorySessionService` | Dict | Yes | No |
| `InMemoryArtifactService` | Dict | Yes | No |
| `InMemoryMemoryService` | Keyword search | Yes | No |

---

## Reusable Test Utilities

We provide shared utilities in `tests/adk_helpers.py` to reduce boilerplate.

### FakeLlm — Mock LLM Responses

`FakeLlm` lets you script deterministic LLM responses for testing:

```python
from tests.adk_helpers import FakeLlm
from google.genai import types

# Simple text responses
fake_llm = FakeLlm.with_responses([
    "First response",
    "Second response",
])

# Function calls
fake_llm = FakeLlm.with_responses([
    types.Part.from_function_call(name="my_tool", args={"x": 1}),
    "Response after tool execution",
])

# Mixed responses
fake_llm = FakeLlm.with_responses([
    "Text response",
    types.Part.from_function_call(name="tool_a", args={}),
    types.Part.from_function_call(name="tool_b", args={"key": "value"}),
    "Final response",
])
```

#### Inspecting LLM Requests

`FakeLlm` records all requests for assertions:

```python
fake_llm = FakeLlm.with_responses(["response"])
# ... run agent ...

# Verify what was sent to the LLM
assert len(fake_llm.requests) == 1
request = fake_llm.requests[0]
assert "expected text" in request.contents[-1].parts[0].text
```

### Context Factories

Create properly-typed ADK contexts without boilerplate:

```python
from tests.adk_helpers import (
    create_invocation_context,
    create_tool_context,
    create_callback_context,
    create_readonly_context,
)

# Basic usage
ctx = await create_invocation_context(agent)

# With initial state
ctx = await create_invocation_context(
    agent,
    state={"my_key": "my_value"},
)

# With pre-saved artifacts
ctx = await create_invocation_context(
    agent,
    artifacts={"report.txt": "Report content here"},
)

# Get specialized contexts
tool_ctx = await create_tool_context(agent, state={...})
callback_ctx = await create_callback_context(agent, state={...})
readonly_ctx = await create_readonly_context(agent, state={...})
```

---

## Rules of Thumb

### 1. Test the Contract, Not the Implementation

**Bad:** Assert that `session_service.update_session` was called with specific args.

**Good:** Assert that after your code runs, `session.state["key"]` has the expected value.

### 2. Create Real Objects, Configure Them for Testing

```python
# ❌ Bad: Mock the agent
agent = MagicMock(spec=LlmAgent)
agent.name = "test"

# ✅ Good: Create real agent with fake LLM
agent = LlmAgent(
    name="test_agent",
    model=FakeLlm.with_responses(["response"]),
    tools=[my_tool],
)
```

### 3. Use `model_construct` Sparingly

Pydantic's `model_construct` bypasses validation. Use it **only** when:
- Testing error handling for invalid states
- Testing code paths that don't depend on validated fields

```python
# ✅ Acceptable: Testing display logic that doesn't need valid repo_path
state = NavigatorState.model_construct(
    user_task="test",
    repo_path="/nonexistent",  # Would fail validation
    # ...
)

# ❌ Bad: Using model_construct to avoid fixing test setup
state = NavigatorState.model_construct(...)  # "validation is annoying"
```

### 4. Prefer Fixtures Over Inline Setup

```python
# ❌ Bad: Repeated setup in each test
async def test_one():
    session_service = InMemorySessionService()
    session = await session_service.create_session(...)
    # ...

async def test_two():
    session_service = InMemorySessionService()
    session = await session_service.create_session(...)
    # ...

# ✅ Good: Shared fixture
@pytest.fixture
async def invocation_context():
    return await create_invocation_context(my_agent)

async def test_one(invocation_context):
    # Use directly

async def test_two(invocation_context):
    # Use directly
```

### 5. Test Tools in Isolation, Then in Context

```python
# Step 1: Test tool logic directly
async def test_my_tool_updates_state():
    ctx = await create_tool_context(agent, state={"count": 0})
    result = await my_tool_impl(ctx, increment=5)
    assert ctx.state["count"] == 5

# Step 2: Test tool works when called by agent
async def test_agent_uses_tool():
    fake_llm = FakeLlm.with_responses([
        types.Part.from_function_call(name="my_tool", args={"increment": 5}),
        "Incremented by 5",
    ])
    # ... run agent, verify state changed
```

### 6. Verify LLM Requests, Not Just Responses

The prompt sent to the LLM is as important as handling the response:

```python
async def test_instruction_includes_budget():
    fake_llm = FakeLlm.with_responses(["done"])
    agent = create_navigator_agent(model=fake_llm)
    
    ctx = await create_invocation_context(
        agent,
        state={"budget_remaining": 100},
    )
    # ... run agent ...
    
    # Verify the instruction included budget info
    request = fake_llm.requests[0]
    system_instruction = request.config.system_instruction
    assert "100" in system_instruction
    assert "budget" in system_instruction.lower()
```

---

## Code Recipes

### Testing a FunctionTool That Modifies State

```python
import pytest
from google.adk.tools import ToolContext
from tests.adk_helpers import create_tool_context

from repo_map.navigator.tools import refine_map  # Your tool


@pytest.fixture
def sample_agent():
    """Create agent for tool context (tools need an agent reference)."""
    from google.adk.agents import LlmAgent
    from tests.adk_helpers import FakeLlm
    
    return LlmAgent(
        name="test_agent",
        model=FakeLlm.with_responses([]),
    )


@pytest.mark.asyncio
async def test_refine_map_updates_state(sample_agent, tmp_path):
    """Tool should log decision to state."""
    # Arrange
    initial_state = {
        "navigator_state": {
            "decision_log": [],
            "repo_path": str(tmp_path),
        }
    }
    ctx = await create_tool_context(sample_agent, state=initial_state)
    
    # Act
    result = await refine_map(
        ctx,
        reasoning="Testing focus on auth module",
        config_changes={"focus_files": ["src/auth.py"]},
    )
    
    # Assert
    state = ctx.state["navigator_state"]
    assert len(state["decision_log"]) == 1
    assert state["decision_log"][0]["reasoning"] == "Testing focus on auth module"
```

### Testing a FunctionTool That Saves Artifacts

```python
@pytest.mark.asyncio
async def test_refine_map_saves_artifact(sample_agent, tmp_path):
    """Tool should save generated map as artifact."""
    # Arrange
    initial_state = {
        "navigator_state": {
            "decision_log": [],
            "repo_path": str(tmp_path),
        }
    }
    ctx = await create_tool_context(sample_agent, state=initial_state)
    
    # Act (with mocked subprocess for the CLI call)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Generated map content\nTokens: 1000\nFiles: 5",
        )
        result = await refine_map(ctx, reasoning="test", config_changes={})
    
    # Assert artifact was saved
    artifact_service = ctx._invocation_context.artifact_service
    artifacts = await artifact_service.list_artifact_keys(
        app_name=ctx._invocation_context.session.app_name,
        user_id=ctx._invocation_context.session.user_id,
        session_id=ctx._invocation_context.session.id,
    )
    assert "current_map.txt" in artifacts
```

### Testing a Plugin's before_model_callback

```python
import pytest
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest
from tests.adk_helpers import create_callback_context

from repo_map.navigator.plugin import NavigatorPlugin


@pytest.mark.asyncio
async def test_plugin_blocks_over_budget(sample_agent):
    """Plugin should return error response when budget exceeded."""
    # Arrange: State shows budget exhausted
    state = {
        "navigator_state": {
            "budget_config": {"max_cost_usd": 1.0},
            "cost_tracking": {"total_spent_usd": 1.5},  # Over budget
        }
    }
    ctx = await create_callback_context(sample_agent, state=state)
    plugin = NavigatorPlugin()
    
    request = LlmRequest(
        model="gemini-2.0-flash",
        contents=[],
    )
    
    # Act
    response = plugin.before_model_callback(ctx, request)
    
    # Assert: Plugin short-circuits with error
    assert response is not None
    assert "BUDGET_EXCEEDED" in response.content.parts[0].text


@pytest.mark.asyncio
async def test_plugin_allows_under_budget(sample_agent):
    """Plugin should return None (allow request) when under budget."""
    # Arrange: State shows budget available
    state = {
        "navigator_state": {
            "budget_config": {"max_cost_usd": 10.0},
            "cost_tracking": {"total_spent_usd": 1.0},
        }
    }
    ctx = await create_callback_context(sample_agent, state=state)
    plugin = NavigatorPlugin()
    
    request = LlmRequest(model="gemini-2.0-flash", contents=[])
    
    # Act
    response = plugin.before_model_callback(ctx, request)
    
    # Assert: Plugin allows request to proceed
    assert response is None
```

### Testing a Plugin's after_model_callback

```python
@pytest.mark.asyncio
async def test_plugin_tracks_usage(sample_agent):
    """Plugin should update cost tracking from response usage metadata."""
    from google.adk.models import LlmResponse
    from google.genai import types
    
    # Arrange
    state = {
        "navigator_state": {
            "cost_tracking": {"total_spent_usd": 0.0, "total_tokens": 0},
        }
    }
    ctx = await create_callback_context(sample_agent, state=state)
    plugin = NavigatorPlugin()
    
    response = LlmResponse(
        content=types.Content(role="model", parts=[types.Part(text="Hello")]),
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=100,
            candidates_token_count=50,
            total_token_count=150,
        ),
    )
    
    # Act
    plugin.after_model_callback(ctx, response)
    
    # Assert: Cost tracking updated
    tracking = ctx.state["navigator_state"]["cost_tracking"]
    assert tracking["total_tokens"] == 150
    assert tracking["total_spent_usd"] > 0
```

### Testing a Dynamic Instruction Provider

```python
import pytest
from google.adk.agents.readonly_context import ReadonlyContext
from tests.adk_helpers import create_readonly_context

from repo_map.navigator.agent import get_navigator_instruction


@pytest.mark.asyncio
async def test_instruction_includes_user_task(sample_agent):
    """Instruction should include the user's original task."""
    state = {
        "navigator_state": {
            "user_task": "Find authentication bugs",
            "decision_log": [],
        }
    }
    ctx = await create_readonly_context(sample_agent, state=state)
    
    instruction = await get_navigator_instruction(ctx)
    
    assert "Find authentication bugs" in instruction


@pytest.mark.asyncio
async def test_instruction_includes_budget_status(sample_agent):
    """Instruction should show remaining budget."""
    state = {
        "navigator_state": {
            "user_task": "test",
            "budget_config": {"max_cost_usd": 10.0},
            "cost_tracking": {"total_spent_usd": 3.0},
            "decision_log": [],
        }
    }
    ctx = await create_readonly_context(sample_agent, state=state)
    
    instruction = await get_navigator_instruction(ctx)
    
    # Should indicate ~70% budget remaining or $7 remaining
    assert "7" in instruction or "70%" in instruction


@pytest.mark.asyncio
async def test_instruction_includes_decision_history(sample_agent):
    """Instruction should summarize recent decisions."""
    state = {
        "navigator_state": {
            "user_task": "test",
            "decision_log": [
                {"step": 1, "reasoning": "Focused on auth module"},
                {"step": 2, "reasoning": "Expanded to include tests"},
            ],
        }
    }
    ctx = await create_readonly_context(sample_agent, state=state)
    
    instruction = await get_navigator_instruction(ctx)
    
    assert "auth module" in instruction
    assert "tests" in instruction
```

### Testing Artifact Loading in Instructions

```python
@pytest.mark.asyncio
async def test_instruction_loads_current_map(sample_agent):
    """Instruction should include the current map artifact."""
    state = {"navigator_state": {"user_task": "test", "decision_log": []}}
    
    ctx = await create_readonly_context(
        sample_agent,
        state=state,
        artifacts={"current_map.txt": "src/auth.py\n  class AuthManager\n"},
    )
    
    instruction = await get_navigator_instruction(ctx)
    
    assert "AuthManager" in instruction


@pytest.mark.asyncio
async def test_instruction_handles_missing_map(sample_agent):
    """Instruction should handle missing map artifact gracefully."""
    state = {"navigator_state": {"user_task": "test", "decision_log": []}}
    
    # No artifacts provided
    ctx = await create_readonly_context(sample_agent, state=state)
    
    instruction = await get_navigator_instruction(ctx)
    
    # Should not crash, should indicate no map yet
    assert instruction is not None
    assert "no map" in instruction.lower() or "not yet" in instruction.lower()
```

### Testing State Model Validation

```python
import pytest
from pydantic import ValidationError

from repo_map.navigator.state import NavigatorState, BudgetConfig


def test_state_requires_user_task():
    """State must have non-empty user_task."""
    with pytest.raises(ValidationError) as exc_info:
        NavigatorState(
            user_task="",  # Empty
            repo_path="/valid/path",
        )
    
    assert "user_task" in str(exc_info.value)


def test_budget_config_validates_bounds():
    """Budget config should reject invalid values."""
    with pytest.raises(ValidationError):
        BudgetConfig(max_cost_usd=-1.0)  # Negative not allowed
    
    with pytest.raises(ValidationError):
        BudgetConfig(max_iterations=0)  # Must be positive


def test_state_roundtrip_serialization(tmp_path):
    """State should survive JSON roundtrip through session."""
    from repo_map.navigator.state import get_state_from_context, save_state_to_context
    
    original = NavigatorState(
        user_task="Find bugs",
        repo_path=str(tmp_path),
        decision_log=[
            {"step": 1, "reasoning": "test", "timestamp": "2024-01-01T00:00:00Z"}
        ],
    )
    
    # Simulate session state storage
    session_state = {"navigator_state": original.model_dump(mode="json")}
    
    # Reconstruct
    reconstructed = NavigatorState.model_validate(session_state["navigator_state"])
    
    assert reconstructed.user_task == original.user_task
    assert len(reconstructed.decision_log) == 1
```

---

## Anti-Patterns to Avoid

### ❌ Mocking Session Service

```python
# BAD: Mocks hide real behavior
session_service = MagicMock(spec=BaseSessionService)
session_service.get_session.return_value = MagicMock(state={"key": "value"})
```

**Why it's bad:** `InMemorySessionService` is already simple. Mocking it means you're not testing how your code interacts with real session lifecycle (create, get, update).

**Fix:** Use `InMemorySessionService` directly.

### ❌ Using MagicMock for Typed Contexts

```python
# BAD: Loses type safety, tests pass with wrong usage
ctx = MagicMock()
ctx.state = {"key": "value"}
await my_tool(ctx)
```

**Why it's bad:** `MagicMock` accepts any attribute access. If your code calls `ctx.statte` (typo), the mock happily returns another mock instead of failing.

**Fix:** Create real `ToolContext` via `create_tool_context()`.

### ❌ Patching Internal ADK Methods

```python
# BAD: Couples test to ADK implementation
with patch.object(LlmAgent, "_generate_content"):
    ...
```

**Why it's bad:** ADK's internal method names and signatures can change. Your test now depends on ADK internals, not your code.

**Fix:** Mock at the boundary — use `FakeLlm` which implements the public `BaseLlm` interface.

### ❌ Skipping Validation to Avoid Test Setup

```python
# BAD: Hides bugs that validation would catch
state = NavigatorState.model_construct(
    repo_path="/does/not/exist",  # Validation would fail
)
```

**Why it's bad:** If your production code receives invalid state, Pydantic catches it. Tests that bypass validation don't verify this protection works.

**Fix:** Use `tmp_path` fixture to create real directories, or test the validation failure explicitly.

### ❌ Asserting on Mock Calls Instead of Outcomes

```python
# BAD: Tests implementation, not behavior
session_service.update_session.assert_called_once_with(...)
```

**Why it's bad:** Implementation can change while behavior stays correct. Maybe ADK batches updates, or uses a different method name in the future.

**Fix:** Assert on observable outcomes — check `session.state` contains expected values.

---

## File Organization

```
tests/
├── conftest.py           # Pytest fixtures (uses adk_helpers)
├── adk_helpers.py        # FakeLlm, context factories, utilities
├── unit/
│   ├── test_*.py         # Unit tests using patterns above
└── integration/
    └── test_*.py         # Integration tests (see separate guide)
```

### conftest.py Example

```python
import pytest
from tests.adk_helpers import FakeLlm, create_invocation_context


@pytest.fixture
def fake_llm():
    """Fresh FakeLlm for each test."""
    return FakeLlm.with_responses(["Default response"])


@pytest.fixture
def sample_agent(fake_llm):
    """Minimal agent for context creation."""
    from google.adk.agents import LlmAgent
    return LlmAgent(name="test_agent", model=fake_llm)


@pytest.fixture
async def invocation_context(sample_agent):
    """Ready-to-use invocation context."""
    return await create_invocation_context(sample_agent)
```

---

## Summary

1. **Use in-memory services** — `InMemorySessionService`, `InMemoryArtifactService`, `InMemoryMemoryService`
2. **Mock only LLM calls** — Use `FakeLlm` from `tests/adk_helpers.py`
3. **Create real contexts** — Use factory functions, not `MagicMock`
4. **Test outcomes, not calls** — Assert on state changes, not method invocations
5. **Leverage fixtures** — Reduce boilerplate, improve consistency
