# Quickstart: Navigator Agent Implementation

**Date**: December 31, 2025  
**Feature**: 002-navigator-agent

---

## Implementation Sequence

The implementation should proceed in this order to ensure each phase builds on tested foundations.

### Phase 1: State Models (Week 1)

**Goal**: Core Pydantic models for state management.

#### 1.1 State Module Setup

- Create `repo_map/navigator/__init__.py`
- Create `repo_map/navigator/state.py`
- Implement Pydantic models: `NavigatorState`, `BudgetConfig`, `DecisionLogEntry`, `MapMetadata`
- **Test**: Unit tests for model validation and serialization

```python
# Key implementation in state.py
from pydantic import BaseModel, Field
from repo_map.core.flight_plan import FlightPlan

class NavigatorState(BaseModel):
    user_task: str = Field(min_length=1)
    repo_path: str
    execution_mode: Literal["autonomous", "interactive"] = "autonomous"
    budget_config: BudgetConfig
    flight_plan: FlightPlan
    decision_log: list[DecisionLogEntry] = Field(default_factory=list)
    map_metadata: MapMetadata = Field(default_factory=MapMetadata)
    # ...
```

#### 1.2 Pricing Configuration

- Create `repo_map/navigator/pricing.py`
- Implement `ModelPricingRates` with preset configurations
- Add cost calculation functions
- **Test**: Unit tests for cost calculation accuracy

```python
# Key functions
def calculate_cost(input_tokens: int, output_tokens: int, pricing: ModelPricingRates) -> float
def get_pricing_for_model(model_name: str) -> ModelPricingRates
```

#### 1.3 State Helpers

- Implement `get_navigator_state(context)` and `update_navigator_state(context, state)`
- Handle dict ↔ Pydantic model conversion
- **Test**: Round-trip serialization tests

### Phase 2: Budget Plugin (Week 2)

**Goal**: Cost tracking and enforcement via ADK plugin.

#### 2.1 Plugin Implementation

- Create `repo_map/navigator/plugin.py`
- Implement `BudgetEnforcementPlugin` extending `BasePlugin`
- Implement `before_model_callback` for budget checking
- Implement `after_model_callback` for usage tracking
- **Test**: Unit tests with mock LlmRequest/LlmResponse

```python
# Key implementation
class BudgetEnforcementPlugin(BasePlugin):
    async def before_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> LlmResponse | None:
        # Check if budget exceeded, return mock response if so
        
    async def after_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_response: LlmResponse,
    ) -> LlmResponse | None:
        # Track actual token usage
```

#### 2.2 Budget Termination

- Implement mock `LlmResponse` for budget exceeded scenario
- Ensure clean termination with partial results
- **Test**: Budget enforcement integration tests

### Phase 3: Tools (Week 3)

**Goal**: Agent tools for flight plan updates and finalization.

#### 3.1 update_flight_plan Tool

- Create `repo_map/navigator/tools.py`
- Implement `update_flight_plan` function
- Wire to CLI subprocess execution
- Save map output to ArtifactService
- Parse map header for metadata
- **Test**: Unit tests with mock subprocess

```python
async def update_flight_plan(
    reasoning: str,
    updates: dict,
    tool_context: ToolContext,
) -> dict:
    # 1. Get current state
    # 2. Apply updates to flight plan
    # 3. Write temp YAML, run CLI
    # 4. Save output as artifact
    # 5. Update state with new metadata
    # 6. Log decision
```

#### 3.2 finalize_context Tool

- Implement `finalize_context` function
- Set completion flags in state
- Store reasoning summary
- **Test**: Unit tests for completion logic

#### 3.3 Tool Registration

- Create `FunctionTool` wrappers
- Define tool schemas for ADK
- **Test**: Tool invocation tests

### Phase 4: Agent & Instructions (Week 4)

**Goal**: LlmAgent with dynamic InstructionProvider.

#### 4.1 InstructionProvider

- Create `repo_map/navigator/agent.py`
- Implement async `navigator_instruction_provider(context)`
- Load state, artifact, build prompt dynamically
- **Test**: Prompt generation tests

```python
async def navigator_instruction_provider(context: ReadonlyContext) -> str:
    state = get_navigator_state(context)
    map_artifact = await context.load_artifact("current_map.txt")
    
    return f"""You are the Navigator Agent...
    
    ## User's Goal
    {state.user_task}
    
    ## Current Map
    {map_artifact.text if map_artifact else "(pending)"}
    
    ## Decision History
    {format_decision_log(state.decision_log)}
    """
```

#### 4.2 Agent Definition

- Create `LlmAgent` with tools and instruction provider
- Configure `include_contents='none'` (state-over-history)
- Register tools
- **Test**: Agent configuration tests

```python
from google.adk.agents import LlmAgent

navigator_agent = LlmAgent(
    name="Navigator",
    model="gemini-2.0-flash",
    instruction=navigator_instruction_provider,
    tools=[update_flight_plan_tool, finalize_context_tool],
)
```

### Phase 5: Runner & Execution (Week 5)

**Goal**: Runner setup with execution modes.

#### 5.1 Runner Setup

- Create `repo_map/navigator/runner.py`
- Configure `InMemorySessionService` and `InMemoryArtifactService`
- Create `Runner` with plugin
- **Test**: Runner initialization tests

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService

def create_navigator_runner(
    repo_path: Path,
    goal: str,
    budget: float,
    mode: Literal["autonomous", "interactive"],
) -> Runner:
    # Setup services
    # Initialize session with state
    # Return configured runner
```

#### 5.2 Autonomous Execution

- Implement `run_autonomous(runner, ...)` function
- Loop until completion or budget exceeded
- Yield progress events
- **Test**: E2E test with mock LLM

#### 5.3 Interactive Execution

- Implement `run_interactive_step(runner, ...)` function
- Build `TurnReport` from state
- Handle user input
- **Test**: Interactive flow tests

### Phase 6: CLI Integration (Week 6)

**Goal**: Wire navigator to CLI command.

#### 6.1 Navigate Command

- Add `navigate` subcommand to `repo_map/cli/app.py`
- Implement option parsing (goal, budget, mode, etc.)
- Wire to runner functions
- **Test**: CLI argument tests

```python
@app.command()
def navigate(
    path: Path,
    goal: Annotated[str, typer.Option("--goal", "-g")],
    tokens: int = 20000,
    cost_limit: float = 2.0,
    interactive: bool = False,
    # ...
):
    # Create runner
    # Execute in appropriate mode
    # Output results
```

#### 6.2 Output Formatting

- Implement progress display (Rich)
- Implement TurnReport rendering
- Handle output to file/clipboard
- **Test**: Output format tests

#### 6.3 Flight Plan Export

- Implement `--flight-plan` output
- Add metadata comments to YAML
- **Test**: YAML export tests

### Phase 7: Integration Testing (Week 7)

**Goal**: End-to-end validation.

#### 7.1 E2E Test Suite

- Create `tests/integration/test_navigator.py`
- Test against `tests/fixtures/sample-repo/`
- Mock LLM responses for determinism
- Verify output format and content

#### 7.2 Budget Enforcement Tests

- Test budget exceeded scenarios
- Verify partial results output
- Test cost accuracy

#### 7.3 Interactive Mode Tests

- Test turn report generation
- Test user input handling
- Test feedback incorporation

---

## Dependency Setup

```bash
# Add Google ADK dependency
uv add google-adk

# Verify installation
uv run python -c "from google.adk import Runner; print('ADK installed')"
```

## Environment Variables

```bash
# Required for Navigator to function
GOOGLE_API_KEY=<your-gemini-api-key>

# Optional: override default model
NAVIGATOR_MODEL=gemini-2.0-flash

# Optional: default cost limit
NAVIGATOR_DEFAULT_BUDGET=2.0
```

## Test Fixtures

### Mock LLM Response

```python
# In tests/conftest.py
@pytest.fixture
def mock_llm_response():
    """Mock LLM response for navigator tests."""
    return LlmResponse(
        content=Content(parts=[Part(text="""
            I've analyzed the repository. Based on the goal "understand auth",
            I'll increase verbosity on src/auth/.
            
            <tool_call>
            update_flight_plan({
                "reasoning": "Zooming in on auth directory",
                "updates": {"verbosity": [{"pattern": "src/auth/**", "level": 4}]}
            })
            </tool_call>
        """)]),
        usage_metadata=UsageMetadata(
            prompt_token_count=1000,
            candidates_token_count=200,
            total_token_count=1200,
        ),
    )
```

### Sample Navigation Session

```python
# Integration test example
def test_navigator_e2e(sample_repo, mock_llm):
    runner = create_navigator_runner(
        repo_path=sample_repo,
        goal="Understand the authentication system",
        budget=2.0,
        mode="autonomous",
    )
    
    output = run_autonomous(runner, user_id="test", session_id="test")
    
    assert output.context_string  # Has content
    assert output.flight_plan_yaml  # Has plan
    assert output.total_cost < 2.0  # Within budget
    assert "auth" in output.reasoning_summary.lower()  # Relevant reasoning
```

---

## Success Criteria Validation

| Criteria | Test Method |
|----------|-------------|
| SC-001: <5 min for 10k files | Performance test with large fixture |
| SC-002: Token budget ±5% | Assert map tokens within 5% of target |
| SC-003: Cost budget zero overruns | Budget plugin tests with edge cases |
| SC-004: 80% relevance | Manual review + heuristic checks |
| SC-005: 100% reproducibility | Run same plan twice, compare outputs |
| SC-006: Complete turn reports | Assert all fields present in interactive |
| SC-007: 50% token efficiency | Compare to full-history baseline |
