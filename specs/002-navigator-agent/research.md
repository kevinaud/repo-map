# Research: Navigator Agent Implementation

**Date**: December 31, 2025  
**Feature**: 002-navigator-agent

---

## 1. Google ADK State Management

### Decision
Store `NavigatorState` as a dict in `session.state`, deserialize to Pydantic model on access.

### Rationale
ADK's `session.state` is a dict-like `State` object. Pydantic models serialize to dicts naturally via `model_dump()`. The `InstructionProvider` receives `ReadonlyContext` with access to `context.state`, enabling reconstruction of the full typed model on each iteration.

### Key Implementation Details

```python
from pydantic import BaseModel
from google.adk.agents.readonly_context import ReadonlyContext

class NavigatorState(BaseModel):
    user_task: str
    execution_mode: Literal["autonomous", "interactive"]
    budget_config: BudgetConfig
    flight_plan: FlightPlan
    decision_log: list[DecisionLogEntry]
    map_metadata: MapMetadata

def get_navigator_state(context: ReadonlyContext) -> NavigatorState:
    """Deserialize NavigatorState from session.state."""
    state_dict = dict(context.state)  # Copy to avoid mutation
    return NavigatorState.model_validate(state_dict.get("navigator", {}))

def update_navigator_state(tool_context: ToolContext, state: NavigatorState) -> None:
    """Serialize and update NavigatorState in session.state."""
    tool_context.state["navigator"] = state.model_dump()
```

### Pitfalls to Avoid

1. **Direct mutation** - Always use `model_copy(update=...)` for immutable updates
2. **Missing keys** - Initialize full state at session creation, not incrementally
3. **Type coercion** - Pydantic handles this, but validate early

### Alternatives Considered

- Custom state class extending ADK State: Rejected (unnecessary coupling)
- Storing Pydantic model directly: Rejected (ADK expects dict-like state)

---

## 2. ADK Plugin Callbacks for Budget Enforcement

### Decision
Use `before_model_callback` to check budget and optionally return mock `LlmResponse` to terminate; use `after_model_callback` to track actual token usage.

### Rationale
Plugins provide lifecycle hooks without modifying agent/tool code. The `before_model_callback` can return an `LlmResponse` to short-circuit the LLM call entirely, enabling budget enforcement before spending tokens.

### Key Implementation Details

```python
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai.types import Content, Part

class BudgetEnforcementPlugin(BasePlugin):
    """Plugin to enforce cost budget limits."""

    def __init__(self) -> None:
        super().__init__(name="budget_enforcement")

    async def before_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> LlmResponse | None:
        """Check budget before LLM call; return mock response if exceeded."""
        state = get_navigator_state(callback_context)
        
        # Estimate cost of this request
        estimated_cost = self._estimate_request_cost(llm_request, state.budget_config)
        
        if state.budget_config.current_spend_usd + estimated_cost > state.budget_config.max_spend_usd:
            # Return termination response
            return LlmResponse(
                content=Content(parts=[Part(text="BUDGET_EXCEEDED: Stopping exploration.")]),
                # usage_metadata will be None for mock response
            )
        return None  # Allow LLM call to proceed

    async def after_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_response: LlmResponse,
    ) -> LlmResponse | None:
        """Track actual token usage after LLM call."""
        if llm_response.usage_metadata:
            state = get_navigator_state(callback_context)
            cost = self._calculate_cost(
                llm_response.usage_metadata,
                state.budget_config.model_pricing_rates,
            )
            state.budget_config.current_spend_usd += cost
            update_navigator_state(callback_context, state)
        return None  # Don't modify response
```

### Usage Metadata Structure

```python
# From LlmResponse.usage_metadata
usage = llm_response.usage_metadata
prompt_tokens = usage.prompt_token_count      # Input tokens
output_tokens = usage.candidates_token_count  # Output tokens
total_tokens = usage.total_token_count        # Sum
```

### Alternatives Considered

- Tool-level budget checks: Rejected (doesn't catch agent "thinking" costs)
- Middleware pattern: ADK doesn't have middleware; plugins are the pattern

---

## 3. ADK Artifact Service for Map Storage

### Decision
Use `InMemoryArtifactService` with `context.save_artifact()` and `context.load_artifact()` for storing map outputs.

### Rationale
Artifacts persist across agent iterations within a session. Storing the current map as an artifact allows the `InstructionProvider` to load it fresh each iteration without bloating the prompt with previous versions.

### Key Implementation Details

```python
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.genai.types import Part

# Setup
artifact_service = InMemoryArtifactService()
runner = Runner(
    agent=navigator_agent,
    app_name="repo-map-navigator",
    session_service=session_service,
    artifact_service=artifact_service,  # Enable artifact storage
)

# In update_flight_plan tool
async def update_flight_plan(
    reasoning: str,
    updates: dict,
    tool_context: ToolContext,
) -> dict:
    # ... run CLI ...
    map_output = subprocess.run(...)
    
    # Save as artifact
    map_artifact = Part.from_text(map_output.stdout)
    version = await tool_context.save_artifact(
        filename="current_map.txt",
        artifact=map_artifact,
    )
    return {"status": "success", "map_version": version}

# In InstructionProvider
async def instruction_provider(context: ReadonlyContext) -> str:
    # Load latest map
    map_artifact = await context.load_artifact(filename="current_map.txt")
    map_content = map_artifact.text if map_artifact else "(No map generated yet)"
    # ... build instruction ...
```

### Alternatives Considered

- Store map in state: Rejected (bloats state dict, harder to manage versions)
- File system: Rejected (ArtifactService is the ADK pattern, handles cleanup)

---

## 4. LLM Response Usage Metadata

### Decision
Extract token counts from `LlmResponse.usage_metadata` for accurate cost tracking.

### Rationale
ADK provides usage metadata on every LLM response. This is the authoritative source for actual token consumption, more accurate than estimation.

### Key Implementation Details

```python
def extract_usage(response: LlmResponse) -> tuple[int, int]:
    """Extract input and output token counts from response."""
    if response.usage_metadata is None:
        return (0, 0)
    return (
        response.usage_metadata.prompt_token_count or 0,
        response.usage_metadata.candidates_token_count or 0,
    )

def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    pricing: ModelPricingRates,
) -> float:
    """Calculate cost in USD from token counts."""
    input_cost = (input_tokens / 1_000_000) * pricing.input_per_million
    output_cost = (output_tokens / 1_000_000) * pricing.output_per_million
    return input_cost + output_cost
```

### Available Fields

| Field | Type | Description |
|-------|------|-------------|
| `prompt_token_count` | int | Input/prompt tokens |
| `candidates_token_count` | int | Output/completion tokens |
| `total_token_count` | int | Sum of input + output |
| `cached_content_token_count` | int | Tokens from cache (if applicable) |

---

## 5. Model Pricing Data

### Decision
Store pricing as Pydantic model with per-million-token rates; default to Gemini 2.0 Flash pricing.

### Rationale
Pricing varies by model and changes over time. Configurable pricing allows users to select models and get accurate cost tracking.

### Key Implementation Details

```python
from pydantic import BaseModel

class ModelPricingRates(BaseModel):
    """Token pricing rates per million tokens."""
    model_name: str
    input_per_million: float   # USD per 1M input tokens
    output_per_million: float  # USD per 1M output tokens

# Default pricing (as of Dec 2025)
GEMINI_2_FLASH_PRICING = ModelPricingRates(
    model_name="gemini-2.0-flash",
    input_per_million=0.075,   # $0.075 per 1M input
    output_per_million=0.30,   # $0.30 per 1M output
)

GEMINI_2_FLASH_THINKING_PRICING = ModelPricingRates(
    model_name="gemini-2.0-flash-thinking",
    input_per_million=0.075,
    output_per_million=0.30,  # Thinking tokens at same rate
)

GEMINI_15_PRO_PRICING = ModelPricingRates(
    model_name="gemini-1.5-pro",
    input_per_million=1.25,
    output_per_million=5.00,
)
```

### Cost Example

For a typical iteration with 10k input tokens and 2k output tokens using Gemini 2.0 Flash:
- Input cost: (10,000 / 1,000,000) × $0.075 = $0.00075
- Output cost: (2,000 / 1,000,000) × $0.30 = $0.0006
- **Total: $0.00135 per iteration**

With $2.00 budget: ~1,400 iterations possible (far more than needed)

---

## 6. Interactive Execution Pattern

### Decision
In interactive mode, the `update_flight_plan` tool sets a flag in state that the runner loop checks; runner yields control back to caller with a `TurnReport`.

### Rationale
ADK's `Runner.run()` is a generator that yields events. We can iterate through events and pause when we detect an interactive breakpoint signal, returning control to the CLI.

### Key Implementation Details

```python
from dataclasses import dataclass
from typing import AsyncIterator

@dataclass
class TurnReport:
    """Report returned after each interactive turn."""
    step_number: int
    cost_this_turn: float
    total_cost: float
    map_size_tokens: int
    focus_areas: list[str]
    reasoning: str

async def run_interactive_step(
    runner: Runner,
    user_id: str,
    session_id: str,
) -> TurnReport | None:
    """Run one iteration of the navigator and return a turn report."""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=Content(parts=[Part(text="Continue exploration.")]),
    ):
        if event.is_final_response():
            # Check if agent signaled completion or interactive pause
            state = await get_session_state(runner, user_id, session_id)
            
            if state.get("interactive_pause"):
                return build_turn_report(state)
            
            if state.get("exploration_complete"):
                return None  # Signal completion
    
    return None

# CLI integration
async def navigate_interactive(repo_path: Path, goal: str, budget: float):
    """Run navigator in interactive mode with user approval."""
    runner = create_navigator_runner(repo_path, goal, budget, mode="interactive")
    
    while True:
        report = await run_interactive_step(runner, user_id, session_id)
        
        if report is None:
            # Exploration complete
            break
        
        # Display turn report
        display_turn_report(report)
        
        # Wait for user approval
        if not prompt_user_continue():
            break
    
    # Output final results
    output_final_context(runner, user_id, session_id)
```

### State Flags for Interactive Mode

```python
class NavigatorState(BaseModel):
    # ... other fields ...
    interactive_pause: bool = False  # Set by tool when iteration complete
    exploration_complete: bool = False  # Set by finalize_context tool
```

### Alternatives Considered

- Custom runner subclass: Rejected (ADK Runner is not designed for subclassing)
- Callback-based pause: Rejected (harder to integrate with CLI flow)
- Multiple agent invocations: Selected (clean, each `run()` call is one iteration)

---

## 7. Tool Definitions

### update_flight_plan Tool

```python
from google.adk.tools import FunctionTool, ToolContext
import subprocess
import tempfile

async def update_flight_plan(
    reasoning: str,
    updates: dict,
    tool_context: ToolContext,
) -> dict:
    """
    Update the flight plan configuration and regenerate the context map.
    
    Args:
        reasoning: Explanation for why these changes are being made.
        updates: Partial dictionary of FlightPlan fields to update.
            - verbosity: List of {pattern, level} rules
            - focus: {paths: [{pattern, weight}], symbols: [{name, weight}]}
            - budget: Token budget limit
    
    Returns:
        Dictionary with status and map metadata.
    """
    # 1. Load current state
    state = get_navigator_state(tool_context)
    
    # 2. Apply updates to flight plan (deep merge)
    updated_plan = state.flight_plan.model_copy(update=updates)
    
    # 3. Write to temp YAML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(updated_plan.to_yaml())
        config_path = f.name
    
    # 4. Execute repo-map CLI
    result = subprocess.run(
        ["repo-map", "generate", str(state.repo_path), "--config", config_path],
        capture_output=True,
        text=True,
    )
    
    # 5. Save output as artifact
    map_artifact = Part.from_text(result.stdout)
    version = await tool_context.save_artifact("current_map.txt", map_artifact)
    
    # 6. Parse header stats into map_metadata
    map_metadata = parse_map_header(result.stdout)
    
    # 7. Log decision
    state.decision_log.append(DecisionLogEntry(
        step=len(state.decision_log) + 1,
        action="update_flight_plan",
        reasoning=reasoning,
        config_diff=updates,
    ))
    
    # 8. Update state
    state.flight_plan = updated_plan
    state.map_metadata = map_metadata
    
    # 9. Set interactive pause if needed
    if state.execution_mode == "interactive":
        state.interactive_pause = True
    
    # 10. Persist state
    update_navigator_state(tool_context, state)
    
    return {
        "status": "success",
        "map_tokens": map_metadata.total_tokens,
        "files_included": map_metadata.file_count,
    }

update_flight_plan_tool = FunctionTool(func=update_flight_plan)
```

### finalize_context Tool

```python
async def finalize_context(
    summary: str,
    tool_context: ToolContext,
) -> dict:
    """
    Finalize the exploration and prepare final outputs.
    
    Args:
        summary: Reasoning summary explaining the final context selection.
    
    Returns:
        Dictionary with final context information.
    """
    state = get_navigator_state(tool_context)
    
    # Mark exploration complete
    state.exploration_complete = True
    state.reasoning_summary = summary
    
    update_navigator_state(tool_context, state)
    
    return {
        "status": "complete",
        "total_iterations": len(state.decision_log),
        "total_cost": state.budget_config.current_spend_usd,
    }

finalize_context_tool = FunctionTool(func=finalize_context)
```

---

## 8. InstructionProvider Implementation

### Decision
Use async `InstructionProvider` function that builds prompt from state + artifact.

### Key Implementation Details

```python
from google.adk.agents.readonly_context import ReadonlyContext

async def navigator_instruction_provider(context: ReadonlyContext) -> str:
    """Build dynamic instruction from current state."""
    state = get_navigator_state(context)
    
    # Load current map from artifact
    map_artifact = await context.load_artifact(filename="current_map.txt")
    current_map = map_artifact.text if map_artifact else "(Initial scan pending)"
    
    # Build decision history
    history_lines = []
    for entry in state.decision_log[-5:]:  # Last 5 decisions
        history_lines.append(f"Step {entry.step}: {entry.action} - {entry.reasoning}")
    decision_history = "\n".join(history_lines) or "(No previous decisions)"
    
    # Build economics summary
    budget_used = state.budget_config.current_spend_usd
    budget_max = state.budget_config.max_spend_usd
    budget_pct = (budget_used / budget_max * 100) if budget_max > 0 else 0
    
    return f"""You are the Navigator Agent for repo-map. Your task is to explore a codebase and build an optimal context window for the user's goal.

## User's Goal
{state.user_task}

## Token Budget
Target: {state.flight_plan.budget:,} tokens
Current map: {state.map_metadata.total_tokens:,} tokens ({state.map_metadata.total_tokens / state.flight_plan.budget * 100:.1f}% of budget)

## Cost Budget
Used: ${budget_used:.4f} / ${budget_max:.2f} ({budget_pct:.1f}%)

## Decision History
{decision_history}

## Current Repository Map
```
{current_map}
```

## Your Task
Analyze the current map against the user's goal. Decide whether to:
1. **Zoom in** - Increase verbosity on relevant files/directories (level 3-4)
2. **Zoom out** - Decrease verbosity on irrelevant areas (level 0-2)  
3. **Finalize** - If the context is optimal, call finalize_context

Use the update_flight_plan tool to refine the map, or finalize_context when done.
Always provide clear reasoning for your decisions."""
```

---

## Summary of Decisions

| Topic | Decision | Key Rationale |
|-------|----------|---------------|
| State Storage | Dict in session.state, Pydantic for typing | ADK expects dict-like state |
| Budget Enforcement | Plugin with before/after callbacks | Catches all LLM costs, can terminate |
| Map Storage | ArtifactService | Clean versioning, no state bloat |
| Token Tracking | LlmResponse.usage_metadata | Authoritative source |
| Pricing | Configurable Pydantic model | Supports multiple models |
| Interactive Mode | State flag + runner loop | Clean CLI integration |
