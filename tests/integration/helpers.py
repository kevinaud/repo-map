"""
Integration Testing Helpers for ADK-Based Code

Utilities for integration tests that use real LLMs.
See docs/developer/integration_testing.md for usage patterns.

WARNING: These helpers make real API calls and incur costs.
         Do NOT import from unit tests.
"""

from __future__ import annotations

import importlib
import os
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv
from google.adk.agents import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService

if TYPE_CHECKING:
  from google.adk.agents.base_agent import BaseAgent
  from google.adk.events import Event
  from google.adk.plugins import BasePlugin
  from google.adk.sessions import Session
  from google.genai.types import FunctionCall


# Default model for integration tests - fast and cost-effective
DEFAULT_TEST_MODEL = "gemini-2.5-flash"


def load_integration_env() -> None:
  """
  Load environment variables for integration tests.

  Looks for .env file in tests/integration/ or project root.
  """
  # Try integration directory first
  integration_env = os.path.join(os.path.dirname(__file__), ".env")
  if os.path.exists(integration_env):
    load_dotenv(integration_env, override=True)
    return

  # Fall back to project root
  root_env = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
  if os.path.exists(root_env):
    load_dotenv(root_env, override=True)


class IntegrationRunner:
  """
  Runner wrapper for integration testing with real LLMs.

  Provides simplified session management and event collection
  for multi-turn conversation testing.

  Example:
      runner = await IntegrationRunner.create("my_project.agents.my_agent")
      events = await runner.run("Hello")
      assert_agent_says_contains("hello", events=events)
  """

  app_name = "integration_test"
  user_id = "test_user"

  def __init__(
    self,
    agent: BaseAgent,
    session_service: InMemorySessionService | None = None,
    artifact_service: InMemoryArtifactService | None = None,
    memory_service: InMemoryMemoryService | None = None,
    plugins: list[BasePlugin] | None = None,
  ) -> None:
    """
    Initialize IntegrationRunner.

    Args:
        agent: The agent to run.
        session_service: Optional session service (creates InMemory if not provided).
        artifact_service: Optional artifact service (creates InMemory if not provided).
        memory_service: Optional memory service (creates InMemory if not provided).
        plugins: Optional list of plugins to add to the runner.
    """
    self.agent = agent
    self.session_service = session_service or InMemorySessionService()
    self.artifact_service = artifact_service or InMemoryArtifactService()
    self.memory_service = memory_service or InMemoryMemoryService()

    self.runner = Runner(  # pyright: ignore[reportUnknownMemberType]
      app_name=self.app_name,
      agent=agent,
      session_service=self.session_service,
      artifact_service=self.artifact_service,
      memory_service=self.memory_service,
    )

    if plugins:
      for plugin in plugins:
        self.runner.plugins.append(plugin)  # pyright: ignore[reportUnknownMemberType]

    self._session: Session | None = None

  @property
  def session(self) -> Session:
    """Get the current session. Raises if no session exists."""
    if self._session is None:
      raise RuntimeError("No session. Call run() first or create_session().")
    return self._session

  async def create_session(
    self,
    session_id: str | None = None,
    state: dict[str, Any] | None = None,
  ) -> Session:
    """
    Create a new session.

    Args:
        session_id: Optional session ID (auto-generated if not provided).
        state: Optional initial state dict.

    Returns:
        The created session.
    """
    self._session = await self.session_service.create_session(
      app_name=self.app_name,
      user_id=self.user_id,
      session_id=session_id,
      state=state or {},
    )
    return self._session

  def new_session(self, session_id: str | None = None) -> None:
    """
    Start a fresh session, discarding the current one.

    Args:
        session_id: Optional session ID for the new session.
    """
    import asyncio

    asyncio.get_event_loop().run_until_complete(
      self.create_session(session_id=session_id)
    )

  async def run(self, prompt: str) -> list[Event]:
    """
    Run the agent with a user prompt.

    Creates a session if one doesn't exist.

    Args:
        prompt: The user's message.

    Returns:
        List of events from the agent run.
    """
    from google.genai import types

    if self._session is None:
      await self.create_session()

    user_content = types.Content(
      role="user",
      parts=[types.Part.from_text(text=prompt)],
    )

    events: list[Event] = [
      event
      async for event in self.runner.run_async(  # pyright: ignore[reportUnknownMemberType]
        user_id=self.user_id,
        session_id=self._session.id,  # pyright: ignore[reportOptionalMemberAccess]
        new_message=user_content,
      )
    ]

    # Refresh session to get updated state
    self._session = await self.session_service.get_session(
      app_name=self.app_name,
      user_id=self.user_id,
      session_id=self._session.id,  # pyright: ignore[reportOptionalMemberAccess]
    )

    return events

  @classmethod
  async def create(
    cls,
    agent_module: str,
    *,
    initial_state: dict[str, Any] | None = None,
    plugins: list[BasePlugin] | None = None,
  ) -> IntegrationRunner:
    """
    Create an IntegrationRunner from an agent module path.

    Args:
        agent_module: Python module path (e.g., "my_project.agents.my_agent").
        initial_state: Optional initial session state.
        plugins: Optional list of plugins.

    Returns:
        Configured IntegrationRunner ready to use.
    """
    load_integration_env()

    module = importlib.import_module(agent_module)

    # Look for root_agent or agent.root_agent
    if hasattr(module, "root_agent"):
      agent = module.root_agent
    elif hasattr(module, "agent") and hasattr(module.agent, "root_agent"):
      agent = module.agent.root_agent
    else:
      raise ValueError(
        f"Module {agent_module} must export 'root_agent' or 'agent.root_agent'"
      )

    runner = cls(agent, plugins=plugins)

    if initial_state:
      await runner.create_session(state=initial_state)

    return runner

  @classmethod
  async def from_fixture(
    cls,
    fixture_name: str,
    *,
    initial_state: dict[str, Any] | None = None,
    plugins: list[BasePlugin] | None = None,
  ) -> IntegrationRunner:
    """
    Create an IntegrationRunner from a fixture agent.

    Args:
        fixture_name: Name of fixture directory under tests/integration/fixture/.
        initial_state: Optional initial session state.
        plugins: Optional list of plugins.

    Returns:
        Configured IntegrationRunner ready to use.
    """
    agent_module = f"tests.integration.fixture.{fixture_name}"
    return await cls.create(
      agent_module,
      initial_state=initial_state,
      plugins=plugins,
    )

  @classmethod
  def from_agent(
    cls,
    agent: BaseAgent,
    *,
    plugins: list[BasePlugin] | None = None,
  ) -> IntegrationRunner:
    """
    Create an IntegrationRunner from an agent instance.

    Args:
        agent: The agent instance to test.
        plugins: Optional list of plugins.

    Returns:
        Configured IntegrationRunner ready to use.
    """
    load_integration_env()
    return cls(agent, plugins=plugins)


# -----------------------------------------------------------------------------
# Assertion Helpers
# -----------------------------------------------------------------------------


def get_agent_responses(events: list[Event]) -> list[str]:
  """
  Extract text responses from agent events.

  Args:
      events: List of events from agent run.

  Returns:
      List of text strings from model responses.
  """
  responses = []
  for event in events:
    if not hasattr(event, "content") or event.content is None:
      continue
    if getattr(event, "author", None) == "user":
      continue

    parts = event.content.parts
    if parts is None:
      continue
    responses.extend(part.text for part in parts if hasattr(part, "text") and part.text)  # pyright: ignore[reportUnknownMemberType]

  return responses


def get_tool_calls(events: list[Event]) -> list[FunctionCall]:
  """
  Extract tool/function calls from agent events.

  Args:
      events: List of events from agent run.

  Returns:
      List of FunctionCall objects.
  """
  tool_calls = []
  for event in events:
    if not hasattr(event, "content") or event.content is None:
      continue

    parts = event.content.parts
    if parts is None:
      continue
    tool_calls.extend(  # pyright: ignore[reportUnknownMemberType]
      part.function_call
      for part in parts
      if hasattr(part, "function_call") and part.function_call
    )

  return tool_calls


def assert_agent_says_contains(
  text: str,
  *,
  events: list[Event],
  case_insensitive: bool = False,
) -> None:
  """
  Assert that agent response contains expected text.

  Args:
      text: Text to search for.
      events: List of events from agent run.
      case_insensitive: Whether to ignore case.

  Raises:
      AssertionError: If text not found in any response.
  """
  responses = get_agent_responses(events)
  search_text = text.lower() if case_insensitive else text

  for response in responses:
    check_response = response.lower() if case_insensitive else response
    if search_text in check_response:
      return

  all_text = "\n".join(responses)
  raise AssertionError(
    f"Expected agent to say something containing '{text}', but got:\n{all_text}"
  )


def assert_agent_says_not_contains(
  text: str,
  *,
  events: list[Event],
  case_insensitive: bool = False,
) -> None:
  """
  Assert that agent response does NOT contain text.

  Args:
      text: Text that should NOT appear.
      events: List of events from agent run.
      case_insensitive: Whether to ignore case.

  Raises:
      AssertionError: If text found in any response.
  """
  responses = get_agent_responses(events)
  search_text = text.lower() if case_insensitive else text

  for response in responses:
    check_response = response.lower() if case_insensitive else response
    if search_text in check_response:
      raise AssertionError(
        f"Expected agent NOT to say '{text}', but found it in:\n{response}"
      )


def assert_tool_was_called(
  tool_name: str,
  *,
  events: list[Event],
  expected_args: dict[str, Any] | None = None,
) -> None:
  """
  Assert that a specific tool was called.

  Args:
      tool_name: Name of the tool to check.
      events: List of events from agent run.
      expected_args: Optional dict of expected arguments.

  Raises:
      AssertionError: If tool was not called or args don't match.
  """
  tool_calls = get_tool_calls(events)

  matching_calls = [tc for tc in tool_calls if tc.name == tool_name]

  if not matching_calls:
    called_tools = [tc.name for tc in tool_calls]
    raise AssertionError(
      f"Expected tool '{tool_name}' to be called, "
      f"but only these tools were called: {called_tools}"
    )

  if expected_args is not None:
    for call in matching_calls:
      if all(call.args.get(k) == v for k, v in expected_args.items()):  # pyright: ignore[reportOptionalMemberAccess]
        return
    raise AssertionError(
      f"Tool '{tool_name}' was called, but not with expected args {expected_args}. "
      f"Actual calls: {[c.args for c in matching_calls]}"
    )


def assert_tool_was_not_called(
  tool_name: str,
  *,
  events: list[Event],
) -> None:
  """
  Assert that a specific tool was NOT called.

  Args:
      tool_name: Name of the tool that should not have been called.
      events: List of events from agent run.

  Raises:
      AssertionError: If tool was called.
  """
  tool_calls = get_tool_calls(events)

  for call in tool_calls:
    if call.name == tool_name:
      raise AssertionError(
        f"Expected tool '{tool_name}' NOT to be called, but it was called "
        f"with args: {call.args}"
      )


def assert_tool_call_count(
  tool_name: str,
  expected_count: int,
  *,
  events: list[Event],
) -> None:
  """
  Assert that a tool was called a specific number of times.

  Args:
      tool_name: Name of the tool to check.
      expected_count: Expected number of calls.
      events: List of events from agent run.

  Raises:
      AssertionError: If call count doesn't match.
  """
  tool_calls = get_tool_calls(events)
  actual_count = sum(1 for tc in tool_calls if tc.name == tool_name)

  if actual_count != expected_count:
    raise AssertionError(
      f"Expected tool '{tool_name}' to be called {expected_count} times, "
      f"but it was called {actual_count} times"
    )
