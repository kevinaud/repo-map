# Integration Testing ADK-Based Code

This document establishes patterns for **integration testing** code built on the Google Agent Development Kit (ADK). These practices are derived from studying ADK's own test suite and complement our [unit testing guide](unit_testing.md).

---

## Philosophy: Integration vs Unit Tests

| Aspect | Unit Tests | Integration Tests |
|--------|-----------|-------------------|
| **LLM** | `FakeLlm` (scripted responses) | Real LLM (`gemini-2.5-flash`) |
| **Speed** | Fast (milliseconds) | Slow (seconds per call) |
| **Cost** | Free | Real API costs |
| **Determinism** | Deterministic | Non-deterministic (use `num_runs`) |
| **Purpose** | Test logic, state, callbacks | Test end-to-end agent behavior |
| **Run frequency** | Every commit | Gated (CI or explicit flag) |

### When to Write Integration Tests

Write integration tests when you need to verify:

1. **Agent behavior with real LLM reasoning** — Does the agent correctly interpret user intent and select appropriate tools?
2. **Multi-turn conversation flows** — Does context persist correctly across turns?
3. **Tool orchestration** — Does the agent call tools in the right order with valid arguments?
4. **Sub-agent delegation** — Does the routing agent correctly hand off to sub-agents?
5. **End-to-end user scenarios** — Does the complete flow work as expected?

### When to Prefer Unit Tests

Use unit tests (with `FakeLlm`) for:

- Testing tool implementations in isolation
- Verifying state transformations
- Testing callback/plugin logic
- Validating instruction generation
- Testing error handling paths

---

## Running Integration Tests

Integration tests are **skipped by default** to avoid accidental API costs and slow CI runs.

```bash
# Run only unit tests (default)
make test-unit

# Run integration tests explicitly
pytest tests/integration/ --run-integration

# Run all tests including integration
pytest --run-integration
```

### Environment Setup

Create a `.env` file in the project root or `tests/integration/` directory:

```bash
# Required for Google AI backend
GOOGLE_API_KEY=your_api_key_here

# Optional: For Vertex AI backend
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_CLOUD_LOCATION=us-central1

# Optional: Control which backend to test
# Values: GOOGLE_AI_ONLY, VERTEX_ONLY, BOTH (default: GOOGLE_AI_ONLY)
TEST_BACKEND=GOOGLE_AI_ONLY
```

**Important:** Never commit API keys. Add `.env` to `.gitignore`.

---

## The AgentEvaluator Pattern

ADK provides `AgentEvaluator` for evaluation-based integration testing. This is the **recommended approach** for testing agent behavior with real LLMs.

### Basic Usage

```python
from google.adk.evaluation.agent_evaluator import AgentEvaluator
import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_handles_simple_query():
    """Test agent responds correctly to basic queries."""
    await AgentEvaluator.evaluate(
        agent_module="my_project.agents.my_agent",
        eval_dataset_file_path_or_dir="tests/integration/eval_data/simple_query.test.json",
        num_runs=4,  # Multiple runs to handle LLM variance
    )
```

### Test Dataset Format (`.test.json`)

Create evaluation datasets in JSON format:

```json
[
  {
    "query": "What's the weather in Seattle?",
    "expected_tool_use": [
      {
        "tool_name": "get_weather",
        "tool_input": {"location": "Seattle"}
      }
    ]
  },
  {
    "query": "Turn on the living room lights",
    "expected_tool_use": [
      {
        "tool_name": "control_lights",
        "tool_input": {"room": "living room", "state": "on"}
      }
    ]
  }
]
```

### Evaluation Configuration (`test_config.json`)

Place a `test_config.json` in the same directory as your test files to configure evaluation criteria:

```json
{
  "criteria": {
    "tool_trajectory_avg_score": 0.8
  }
}
```

Available metrics:

| Metric | Description | Threshold Range |
|--------|-------------|-----------------|
| `tool_trajectory_avg_score` | Accuracy of tool calls vs expected | 0.0 - 1.0 |
| `response_match_score` | Semantic similarity to reference | 0.0 - 1.0 |
| `response_evaluation_score` | General response quality | 0.0 - 1.0 |

### Testing Sub-Agents

For multi-agent systems, test specific sub-agents:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_booking_sub_agent():
    """Test the booking sub-agent in isolation."""
    await AgentEvaluator.evaluate(
        agent_module="my_project.agents.travel_agent",
        eval_dataset_file_path_or_dir="tests/integration/eval_data/booking.test.json",
        agent_name="booking_agent",  # Test specific sub-agent
        num_runs=4,
    )
```

### Installing AgentEvaluator Dependencies

`AgentEvaluator` requires additional dependencies:

```bash
pip install "google-cloud-aiplatform[evaluation]"
```

---

## The IntegrationRunner Pattern

For more control over integration tests, use `IntegrationRunner` — a wrapper around ADK's `Runner` that simplifies session management and event collection.

### Basic Usage

```python
from tests.integration.helpers import IntegrationRunner
import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_turn_conversation():
    """Test agent handles multi-turn conversation."""
    runner = await IntegrationRunner.create("my_project.agents.my_agent")
    
    # First turn
    events = await runner.run("Hello, I need help booking a flight")
    assert_agent_says_contains("flight", events=events)
    
    # Second turn (same session)
    events = await runner.run("I want to go to Seattle")
    assert_agent_says_contains("Seattle", events=events)
    
    # Verify state persisted
    assert runner.session.state.get("destination") == "Seattle"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fresh_session():
    """Test with a fresh session."""
    runner = await IntegrationRunner.create("my_project.agents.my_agent")
    
    await runner.run("Set my name to Alice")
    
    # Start fresh session
    runner.new_session()
    
    events = await runner.run("What's my name?")
    # Agent shouldn't know the name in a new session
    assert_agent_says_not_contains("Alice", events=events)
```

### Loading Agent from Fixture

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_from_fixture():
    """Test agent defined in fixture directory."""
    runner = await IntegrationRunner.from_fixture("my_test_agent")
    events = await runner.run("Hello")
    assert len(events) > 0
```

---

## Fixture Organization

Organize integration test fixtures consistently:

```
tests/
├── integration/
│   ├── conftest.py              # Integration-specific fixtures
│   ├── .env                     # API keys (gitignored)
│   ├── test_my_agent.py         # Test files
│   ├── fixture/                 # Test agent definitions
│   │   ├── my_test_agent/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py         # Exports root_agent
│   │   │   ├── simple.test.json # Eval dataset
│   │   │   └── test_config.json # Eval criteria
│   │   └── another_agent/
│   │       └── ...
│   └── eval_data/               # Shared eval datasets
│       ├── common_queries.test.json
│       └── edge_cases.test.json
└── unit/
    └── ...
```

### Fixture Agent Convention

Each fixture agent should export a `root_agent`:

```python
# tests/integration/fixture/my_test_agent/agent.py
from google.adk.agents import LlmAgent

from my_project.tools import my_tool


root_agent = LlmAgent(
    name="my_test_agent",
    model="gemini-2.5-flash",  # Use fast model for tests
    instruction="You are a helpful assistant.",
    tools=[my_tool],
)
```

---

## Assertion Helpers

Use these helpers for readable integration test assertions:

```python
from tests.integration.helpers import (
    assert_agent_says_contains,
    assert_agent_says_not_contains,
    assert_tool_was_called,
    assert_tool_was_not_called,
    get_tool_calls,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_assertions(runner):
    events = await runner.run("Book a flight to Seattle")
    
    # Check agent response contains expected text
    assert_agent_says_contains("Seattle", events=events)
    assert_agent_says_contains("flight", events=events)
    
    # Check tool usage
    assert_tool_was_called("search_flights", events=events)
    assert_tool_was_not_called("book_hotel", events=events)
    
    # Get tool calls for detailed assertions
    tool_calls = get_tool_calls(events)
    assert tool_calls[0].name == "search_flights"
    assert tool_calls[0].args["destination"] == "Seattle"
```

---

## Handling LLM Non-Determinism

LLM responses vary between runs. Use these strategies:

### 1. Multiple Runs with AgentEvaluator

```python
await AgentEvaluator.evaluate(
    agent_module="my_project.agents.my_agent",
    eval_dataset_file_path_or_dir="tests/integration/eval_data/test.test.json",
    num_runs=4,  # Run each eval case 4 times, average scores
)
```

### 2. Fuzzy Assertions

```python
# Instead of exact match
assert response == "The weather in Seattle is sunny"

# Use containment checks
assert_agent_says_contains("Seattle", events=events)
assert_agent_says_contains("weather", events=events)
```

### 3. Semantic Assertions (via Metrics)

Configure `response_match_score` in `test_config.json` with appropriate threshold:

```json
{
  "criteria": {
    "response_match_score": 0.7
  }
}
```

### 4. Tool-Based Assertions

Tool calls are more deterministic than natural language:

```python
# More reliable than checking exact text
tool_calls = get_tool_calls(events)
assert any(tc.name == "get_weather" for tc in tool_calls)
```

---

## Cost Management

Integration tests incur real API costs. Follow these practices:

### 1. Use Fast, Cheap Models

```python
# Default to gemini-2.5-flash for tests
root_agent = LlmAgent(
    name="test_agent",
    model="gemini-2.5-flash",  # Fast and cost-effective
    ...
)
```

### 2. Minimize Test Dataset Size

Keep eval datasets focused:

```json
[
  {"query": "Core functionality test 1", ...},
  {"query": "Core functionality test 2", ...}
]
```

### 3. Gate Integration Tests

Only run on explicit request:

```bash
# CI should NOT run integration tests by default
pytest tests/unit/

# Run integration tests only for releases or explicit triggers
pytest --run-integration
```

### 4. Track Costs in CI

Log token usage in CI for monitoring:

```python
@pytest.fixture(autouse=True)
def log_token_usage(request):
    yield
    # Log usage after each test for cost tracking
    if hasattr(request.node, "integration_tokens"):
        print(f"Tokens used: {request.node.integration_tokens}")
```

---

## Code Recipes

### Testing a Complete User Flow

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_booking_flow():
    """Test end-to-end flight booking flow."""
    runner = await IntegrationRunner.create("my_project.agents.travel_agent")
    
    # Step 1: Initiate booking
    events = await runner.run("I want to book a flight to Seattle next Monday")
    assert_agent_says_contains("Seattle", events=events)
    assert_tool_was_called("search_flights", events=events)
    
    # Step 2: Select flight
    events = await runner.run("I'll take the morning flight")
    assert_tool_was_called("select_flight", events=events)
    
    # Step 3: Confirm booking
    events = await runner.run("Yes, confirm the booking")
    assert_tool_was_called("confirm_booking", events=events)
    assert_agent_says_contains("confirmed", events=events)
    
    # Verify final state
    assert runner.session.state.get("booking_confirmed") is True
```

### Testing Error Recovery

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_handles_api_error_gracefully():
    """Test agent recovers from API errors."""
    runner = await IntegrationRunner.create(
        "my_project.agents.travel_agent",
        # Inject a tool that fails
        tool_overrides={"search_flights": mock_failing_tool},
    )
    
    events = await runner.run("Search for flights to Seattle")
    
    # Agent should communicate the error gracefully
    assert_agent_says_contains("sorry", events=events, case_insensitive=True)
    assert_agent_says_not_contains("exception", events=events, case_insensitive=True)
```

### Testing with Initial State

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_preexisting_context():
    """Test agent uses existing session state."""
    runner = await IntegrationRunner.create(
        "my_project.agents.travel_agent",
        initial_state={
            "user_preferences": {"seat": "window", "class": "economy"},
            "frequent_flyer_id": "FF123456",
        },
    )
    
    events = await runner.run("Book my usual seat on the next flight to Seattle")
    
    # Agent should use preferences from state
    tool_calls = get_tool_calls(events)
    booking_call = next(tc for tc in tool_calls if tc.name == "book_flight")
    assert booking_call.args["seat_preference"] == "window"
```

### Testing Callback Behavior in Real Flow

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_budget_plugin_stops_expensive_queries():
    """Test budget plugin blocks requests when over budget."""
    runner = await IntegrationRunner.create(
        "my_project.agents.travel_agent",
        initial_state={
            "budget_config": {"max_cost_usd": 0.01},
            "cost_tracking": {"total_spent_usd": 0.02},  # Already over
        },
        plugins=[BudgetPlugin()],
    )
    
    events = await runner.run("Search for flights")
    
    # Plugin should have blocked the request
    assert_agent_says_contains("budget", events=events, case_insensitive=True)
```

---

## Anti-Patterns to Avoid

### ❌ Testing Exact LLM Output

```python
# BAD: LLM output varies between runs
assert response.text == "I found 3 flights to Seattle. The cheapest is $299."
```

**Fix:** Use containment checks or semantic similarity metrics.

### ❌ Running Integration Tests in CI by Default

```yaml
# BAD: Every PR runs expensive tests
test:
  script: pytest  # Runs everything including integration
```

**Fix:** Explicitly exclude integration tests:

```yaml
test:
  script: pytest tests/unit/

integration_test:
  script: pytest --run-integration
  when: manual  # Or on specific triggers
```

### ❌ Large Eval Datasets for Routine Tests

```python
# BAD: 100 test cases × 4 runs × API cost = expensive
await AgentEvaluator.evaluate(
    ...,
    eval_dataset_file_path_or_dir="tests/integration/all_500_cases/",
    num_runs=4,
)
```

**Fix:** Keep routine test datasets small (5-10 cases). Use large datasets for release validation only.

### ❌ Hardcoding API Keys

```python
# BAD: Committed to version control
GOOGLE_API_KEY = "AIza..."
```

**Fix:** Use environment variables and `.env` files (gitignored).

### ❌ No Timeout for LLM Calls

```python
# BAD: Test hangs indefinitely if LLM is slow
events = await runner.run("Complex query")
```

**Fix:** Set appropriate timeouts:

```python
events = await asyncio.wait_for(
    runner.run("Complex query"),
    timeout=60.0,  # 60 second timeout
)
```

---

## Debugging Integration Tests

### Verbose Event Logging

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_debugging(runner):
    events = await runner.run("Hello")
    
    # Print all events for debugging
    for event in events:
        print(f"Author: {event.author}")
        if event.content:
            for part in event.content.parts:
                if part.text:
                    print(f"  Text: {part.text}")
                if part.function_call:
                    print(f"  Tool: {part.function_call.name}({part.function_call.args})")
```

### Inspecting Session State

```python
# After running the agent
print(f"Session state: {runner.session.state}")
print(f"Session ID: {runner.session.id}")
```

### Using pytest's `-s` Flag

```bash
# Show print output during tests
pytest tests/integration/test_my_agent.py -s --run-integration
```

---

## Summary

1. **Use `AgentEvaluator` for evaluation-based testing** — structured, repeatable, handles variance
2. **Use `IntegrationRunner` for flow-based testing** — multi-turn, state inspection, more control
3. **Default to `gemini-2.5-flash`** — fast and cost-effective for tests
4. **Gate integration tests** — don't run by default, require `--run-integration`
5. **Use fuzzy assertions** — `assert_agent_says_contains`, tool call checks
6. **Handle non-determinism** — multiple runs, semantic matching, tool-based assertions
7. **Keep eval datasets small** — 5-10 cases for routine tests
8. **Never commit API keys** — use `.env` files, environment variables
