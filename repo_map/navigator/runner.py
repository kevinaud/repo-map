"""Navigator runner for agent execution.

This module provides the runner setup and execution modes for the
Navigator agent, including autonomous and interactive modes.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

import structlog
from google.adk import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from repo_map.core.flight_plan import FlightPlan
from repo_map.mapper import generate_repomap
from repo_map.navigator.agent import create_navigator_agent
from repo_map.navigator.plugin import BudgetEnforcementPlugin
from repo_map.navigator.pricing import get_pricing_for_model
from repo_map.navigator.state import (
  NAVIGATOR_STATE_KEY,
  BudgetConfig,
  MapMetadata,
  NavigatorOutput,
  NavigatorState,
  TurnReport,
)
from repo_map.settings import settings

if TYPE_CHECKING:
  from collections.abc import AsyncIterator
  from pathlib import Path

logger = structlog.get_logger()


@dataclass
class NavigatorProgress:
  """Progress event emitted during exploration."""

  step: int
  action: str
  tokens: int
  cost_so_far: Decimal  # Use Decimal for monetary precision
  message: str


def create_navigator_runner(
  model: str | None = None,
) -> tuple[Runner, BudgetEnforcementPlugin]:
  """Create and configure the Navigator runner.

  Args:
      model: Model identifier to use. Defaults to settings.navigator_model.

  Returns:
      Tuple of (Runner, BudgetEnforcementPlugin) for execution and cost tracking
  """
  if model is None:
    # pydantic-settings dynamically adds attributes from env vars,
    # which pyright cannot infer statically
    model = str(settings.navigator_model)  # pyright: ignore[reportUnknownMemberType]

  agent = create_navigator_agent(model=model)
  budget_plugin = BudgetEnforcementPlugin()

  session_service = InMemorySessionService()
  artifact_service = InMemoryArtifactService()

  runner = Runner(
    agent=agent,
    app_name="repo-map-navigator",
    session_service=session_service,
    artifact_service=artifact_service,
    plugins=[budget_plugin],  # Pass plugins in constructor for proper registration
  )

  return runner, budget_plugin


def generate_initial_map(repo_path: Path, token_budget: int) -> tuple[str, MapMetadata]:
  """Generate an initial low-verbosity map for agent exploration.

  Creates a structural overview map (verbosity level 2) to give the agent
  context about the repository before it starts making decisions.

  Args:
      repo_path: Path to repository root
      token_budget: Maximum token budget

  Returns:
      Tuple of (map_content, metadata)
  """
  from repo_map.core.cost import estimate_tokens

  # Generate a structural overview (default verbosity = 2)
  # Use a fraction of the budget for initial overview
  initial_budget = min(token_budget // 2, 4000)

  result = generate_repomap(
    root_dir=repo_path,
    token_limit=initial_budget,
  )

  if result is None:
    # Empty or inaccessible repo
    return "(Repository is empty or inaccessible)", MapMetadata()

  # Build metadata with token estimate
  metadata = MapMetadata()
  metadata.file_count = len(result.files)
  metadata.total_tokens = estimate_tokens(result.content)

  # Calculate budget utilization
  if token_budget > 0:
    metadata.budget_utilization = (metadata.total_tokens / token_budget) * 100

  return result.content, metadata


async def initialize_session(
  runner: Runner,
  user_id: str,
  session_id: str,
  repo_path: Path,
  user_task: str,
  token_budget: int,
  cost_limit: float,
  model: str,
  execution_mode: Literal["autonomous", "interactive"] = "autonomous",
) -> None:
  """Initialize a Navigator session with starting state.

  Args:
      runner: The Runner instance
      user_id: User identifier
      session_id: Session identifier
      repo_path: Path to repository
      user_task: User's goal description
      token_budget: Maximum tokens for context
      cost_limit: Maximum USD to spend
      model: Model name for pricing lookup
      execution_mode: "autonomous" or "interactive"
  """
  # Get pricing for the model
  pricing = get_pricing_for_model(model)

  # Generate initial map to give agent context
  logger.info("generating_initial_map", repo_path=str(repo_path))
  initial_map, initial_metadata = generate_initial_map(repo_path, token_budget)

  # Create initial state with map metadata
  initial_state = NavigatorState(
    user_task=user_task,
    repo_path=str(repo_path.absolute()),
    execution_mode=execution_mode,
    budget_config=BudgetConfig(
      max_spend_usd=Decimal(str(cost_limit)),
      current_spend_usd=Decimal("0.0"),
      model_pricing=pricing,
    ),
    flight_plan=FlightPlan(budget=token_budget),
    decision_log=[],
    map_metadata=initial_metadata,
  )

  # Create session with initial state and initial map
  # Include initial_map in the state dict so instruction provider can access it
  await runner.session_service.create_session(
    app_name=runner.app_name,
    user_id=user_id,
    session_id=session_id,
    state={
      NAVIGATOR_STATE_KEY: initial_state.model_dump(mode="json"),
      "initial_map": initial_map,
    },
  )

  logger.info(
    "session_initialized",
    session_id=session_id,
    repo_path=str(repo_path),
    token_budget=token_budget,
    cost_limit=cost_limit,
    initial_tokens=initial_metadata.total_tokens,
    initial_files=initial_metadata.file_count,
  )


async def run_autonomous(
  runner: Runner,
  budget_plugin: BudgetEnforcementPlugin,
  user_id: str,
  session_id: str,
  max_iterations: int = 20,
  debug: bool = False,
) -> AsyncIterator[NavigatorProgress | NavigatorOutput]:
  """Run the Navigator in autonomous mode.

  Executes the exploration loop continuously until:
  - Agent calls finalize_context
  - Budget is exhausted
  - Max iterations reached

  Args:
      runner: The Runner instance
      budget_plugin: Budget tracking plugin
      user_id: User identifier
      session_id: Session identifier
      max_iterations: Maximum exploration iterations
      debug: Enable verbose debug logging

  Yields:
      NavigatorProgress events and final NavigatorOutput
  """
  iteration = 0

  # Load initial state (used if max_iterations == 0)
  session = await runner.session_service.get_session(
    app_name=runner.app_name,
    user_id=user_id,
    session_id=session_id,
  )
  if session is None:
    raise ValueError(f"Session {session_id} not found")

  state_dict = session.state.get(NAVIGATOR_STATE_KEY, {})
  state = NavigatorState.model_validate(state_dict)

  while iteration < max_iterations:
    iteration += 1

    # Run one agent iteration
    logger.debug("starting_iteration", iteration=iteration, max=max_iterations)

    final_response = None
    tool_calls = []
    async for event in runner.run_async(
      user_id=user_id,
      session_id=session_id,
      new_message=Content(
        parts=[Part.from_text(text="Continue exploration based on current state.")]
      ),
    ):
      # Track tool calls for debug output
      if hasattr(event, "content") and event.content and event.content.parts:
        # ADK Event.content.parts has dynamic Part types; filter by attribute
        tool_calls.extend(  # pyright: ignore[reportUnknownMemberType]
          part.function_call.name
          for part in event.content.parts
          if hasattr(part, "function_call") and part.function_call
        )
      if event.is_final_response():
        final_response = event

    if debug and tool_calls:
      logger.info("tool_calls_made", iteration=iteration, tools=tool_calls)

    # Get current state
    session = await runner.session_service.get_session(
      app_name=runner.app_name,
      user_id=user_id,
      session_id=session_id,
    )
    if session is None:
      raise ValueError(f"Session {session_id} not found")

    state_dict = session.state.get(NAVIGATOR_STATE_KEY, {})
    state = NavigatorState.model_validate(state_dict)

    # Emit progress event
    last_decision = state.decision_log[-1] if state.decision_log else None

    if debug:
      # Log detailed state info
      logger.info(
        "iteration_state",
        iteration=iteration,
        action=last_decision.action if last_decision else "unknown",
        tokens=state.map_metadata.total_tokens,
        files=state.map_metadata.file_count,
        cost=state.budget_config.current_spend_usd,
        budget_remaining=state.budget_config.remaining_budget,
        complete=state.exploration_complete,
      )
      if last_decision:
        logger.info("reasoning", reasoning=last_decision.reasoning[:200])
        if last_decision.config_patch:
          logger.info("config_changes", diff=last_decision.config_patch)

    yield NavigatorProgress(
      step=iteration,
      action=last_decision.action if last_decision else "unknown",
      tokens=state.map_metadata.total_tokens,
      cost_so_far=state.budget_config.current_spend_usd,
      message=last_decision.reasoning[:100] if last_decision else "Processing...",
    )

    # Check for completion
    if state.exploration_complete:
      logger.info(
        "exploration_complete",
        iterations=iteration,
        total_cost=state.budget_config.current_spend_usd,
      )
      break

    # Check for budget exhaustion (indicated by agent response)
    if final_response and final_response.content:
      response_text = ""
      if final_response.content.parts:
        for part in final_response.content.parts:
          if hasattr(part, "text") and part.text:
            response_text += part.text

      if "BUDGET_EXCEEDED" in response_text:
        logger.warning("budget_exhausted", iteration=iteration)
        # Mark exploration complete with partial results
        state.exploration_complete = True
        state.reasoning_summary = (
          "Exploration stopped due to budget exhaustion. "
          "Partial results delivered based on exploration so far."
        )
        # Update state
        session.state[NAVIGATOR_STATE_KEY] = state.model_dump(mode="json")
        break
  else:
    # Max iterations reached without completion
    logger.warning(
      "max_iterations_reached",
      max_iterations=max_iterations,
      total_cost=float(state.budget_config.current_spend_usd),
    )
    if not state.reasoning_summary:
      state.reasoning_summary = (
        f"Exploration stopped after reaching max iterations ({max_iterations}). "
        "Results may be incomplete."
      )

  # Load final map from artifact
  context_string = ""
  try:
    # artifact_service is Optional but always configured in create_navigator_runner
    artifact = await runner.artifact_service.load_artifact(  # pyright: ignore[reportOptionalMemberAccess]
      app_name=runner.app_name,
      user_id=user_id,
      session_id=session_id,
      filename="current_map.txt",
    )
    if artifact and artifact.text:
      context_string = artifact.text
  except Exception:
    logger.warning("failed_to_load_final_artifact")

  # Build final output
  output = NavigatorOutput(
    context_string=context_string,
    flight_plan_yaml=state.flight_plan.to_yaml(),
    reasoning_summary=state.reasoning_summary,
    total_iterations=len(state.decision_log),
    total_cost=state.budget_config.current_spend_usd,
    token_count=state.map_metadata.total_tokens,
  )

  yield output


def build_turn_report(state: NavigatorState, last_cost: float) -> TurnReport:
  """Build a TurnReport from current state.

  Args:
      state: Current NavigatorState
      last_cost: Cost of the last iteration

  Returns:
      TurnReport for user display
  """
  last_decision = state.decision_log[-1] if state.decision_log else None

  return TurnReport(
    step_number=len(state.decision_log),
    cost_this_turn=Decimal(str(last_cost)),
    total_cost=state.budget_config.current_spend_usd,
    map_size_tokens=state.map_metadata.total_tokens,
    budget_remaining=state.budget_config.remaining_budget,
    focus_areas=state.map_metadata.focus_areas,
    last_action=last_decision.action if last_decision else "none",
    reasoning=last_decision.reasoning if last_decision else "",
  )


async def run_interactive_step(
  runner: Runner,
  budget_plugin: BudgetEnforcementPlugin,
  user_id: str,
  session_id: str,
) -> TurnReport | NavigatorOutput | None:
  """Run one interactive step and return a turn report.

  Args:
      runner: The Runner instance
      budget_plugin: Budget tracking plugin
      user_id: User identifier
      session_id: Session identifier

  Returns:
      TurnReport if paused for user input
      NavigatorOutput if exploration complete
      None if error
  """
  # Run one agent iteration
  async for _event in runner.run_async(
    user_id=user_id,
    session_id=session_id,
    new_message=Content(
      parts=[Part.from_text(text="Continue exploration based on current state.")]
    ),
  ):
    pass  # Process all events

  # Get current state
  session = await runner.session_service.get_session(
    app_name=runner.app_name,
    user_id=user_id,
    session_id=session_id,
  )
  if session is None:
    raise ValueError(f"Session {session_id} not found")

  state_dict = session.state.get(NAVIGATOR_STATE_KEY, {})
  state = NavigatorState.model_validate(state_dict)

  # Check for completion
  if state.exploration_complete:
    # Load final map
    context_string = ""
    try:
      # artifact_service is Optional but always configured in create_navigator_runner
      artifact = await runner.artifact_service.load_artifact(  # pyright: ignore[reportOptionalMemberAccess]
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
        filename="current_map.txt",
      )
      if artifact and artifact.text:
        context_string = artifact.text
    except Exception:
      logger.warning("failed_to_load_final_artifact_interactive")

    return NavigatorOutput(
      context_string=context_string,
      flight_plan_yaml=state.flight_plan.to_yaml(),
      reasoning_summary=state.reasoning_summary,
      total_iterations=len(state.decision_log),
      total_cost=state.budget_config.current_spend_usd,
      token_count=state.map_metadata.total_tokens,
    )

  # Reset interactive pause flag
  if state.interactive_pause:
    state.interactive_pause = False
    session.state[NAVIGATOR_STATE_KEY] = state.model_dump(mode="json")

  # Return turn report
  return build_turn_report(state, float(budget_plugin.last_iteration_cost))
