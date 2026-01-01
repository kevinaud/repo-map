"""
ADK Testing Helpers

Reusable utilities for testing code built on Google ADK.
See docs/developer/unit_testing.md for usage patterns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from google.adk.agents import LlmAgent, RunConfig
from google.adk.agents.invocation_context import InvocationContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.adk.models import LlmResponse
from google.adk.models.base_llm import BaseLlm
from google.adk.sessions import InMemorySessionService
from google.genai import types

if TYPE_CHECKING:
  from collections.abc import AsyncGenerator

  from google.adk.agents.callback_context import CallbackContext
  from google.adk.agents.readonly_context import ReadonlyContext
  from google.adk.models import LlmRequest
  from google.adk.models.base_llm import BaseLlmConnection
  from google.adk.tools import ToolContext


class FakeLlm(BaseLlm):
  """
  Fake LLM implementation for deterministic testing.

  Records all requests and returns scripted responses in order.

  Usage:
      fake_llm = FakeLlm.with_responses([
          "First response",
          types.Part.from_function_call(name="my_tool", args={"x": 1}),
          "Response after tool",
      ])

      agent = LlmAgent(name="test", model=fake_llm, tools=[...])

      # After running agent, inspect requests:
      assert len(fake_llm.requests) == 2
  """

  # Pydantic model config to allow extra attributes
  model_config: ClassVar[dict[str, str]] = {"extra": "allow"}

  def __init__(
    self,
    responses: list[str | types.Part | list[types.Part]] | None = None,
    *,
    error: Exception | None = None,
  ):
    """
    Initialize FakeLlm.

    Args:
        responses: Scripted responses to return in order. Each can be:
            - str: Converted to text Part
            - Part: Used directly (e.g., function_call)
            - list[Part]: Multiple parts in one response
        error: If set, raise this error instead of returning responses.
    """
    super().__init__(model="fake-model")
    self._responses = list(responses or [])
    self._error = error
    self._response_index = 0
    self.requests: list[LlmRequest] = []

  @classmethod
  def with_responses(
    cls,
    responses: list[str | types.Part | list[types.Part]],
  ) -> FakeLlm:
    """Create a FakeLlm with scripted responses."""
    return cls(responses=responses)

  @classmethod
  def with_error(cls, error: Exception) -> FakeLlm:
    """Create a FakeLlm that raises an error."""
    return cls(error=error)

  def _get_next_response(self) -> types.Content:
    """Get next scripted response as Content."""
    if self._response_index >= len(self._responses):
      raise RuntimeError(
        f"FakeLlm exhausted all {len(self._responses)} responses. "
        f"Test made more LLM calls than expected."
      )

    response = self._responses[self._response_index]
    self._response_index += 1

    # Normalize to list of Parts
    if isinstance(response, str):
      parts = [types.Part.from_text(text=response)]
    elif isinstance(response, types.Part):
      parts = [response]
    else:
      parts = response

    return types.Content(role="model", parts=parts)

  async def generate_content_async(
    self,
    llm_request: LlmRequest,
    stream: bool = False,
  ) -> AsyncGenerator[LlmResponse, None]:
    """Generate content from scripted responses."""
    self.requests.append(llm_request)

    if self._error:
      raise self._error

    content = self._get_next_response()

    # Create realistic usage metadata
    usage = types.GenerateContentResponseUsageMetadata(
      prompt_token_count=100,
      candidates_token_count=50,
      total_token_count=150,
    )

    yield LlmResponse(content=content, usage_metadata=usage)

  def connect(self, llm_request: LlmRequest) -> BaseLlmConnection:
    """Live connection - not supported for FakeLlm."""
    raise NotImplementedError("FakeLlm does not support live connections")

  @property
  def model_name(self) -> str:
    """Return the model name."""
    return self._model  # type: ignore[reportUnknownMemberType]


async def create_invocation_context(
  agent: LlmAgent,
  *,
  state: dict[str, Any] | None = None,
  artifacts: dict[str, str | bytes] | None = None,
  app_name: str = "test_app",
  user_id: str = "test_user",
) -> InvocationContext:
  """
  Create an InvocationContext for testing.

  Args:
      agent: The agent to create context for.
      state: Initial session state dict.
      artifacts: Dict of filename -> content to pre-save as artifacts.
      app_name: App name for session.
      user_id: User ID for session.

  Returns:
      Fully configured InvocationContext with in-memory services.
  """
  session_service = InMemorySessionService()
  artifact_service = InMemoryArtifactService()
  memory_service = InMemoryMemoryService()

  session = await session_service.create_session(
    app_name=app_name,
    user_id=user_id,
    state=state or {},
  )

  ctx = InvocationContext(
    invocation_id="test-invocation-id",
    agent=agent,
    session=session,
    session_service=session_service,
    artifact_service=artifact_service,
    memory_service=memory_service,
    run_config=RunConfig(),
  )

  # Pre-save artifacts if provided
  if artifacts:
    for filename, content in artifacts.items():
      if isinstance(content, str):
        part = types.Part.from_text(text=content)
      else:
        part = types.Part.from_bytes(data=content, mime_type="application/octet-stream")

      await artifact_service.save_artifact(
        app_name=app_name,
        user_id=user_id,
        session_id=session.id,
        filename=filename,
        artifact=part,
      )

  return ctx


async def create_tool_context(
  agent: LlmAgent,
  *,
  state: dict[str, Any] | None = None,
  artifacts: dict[str, str | bytes] | None = None,
) -> ToolContext:
  """
  Create a ToolContext for testing FunctionTools.

  Args:
      agent: The agent (tools need agent reference).
      state: Initial session state dict.
      artifacts: Dict of filename -> content to pre-save.

  Returns:
      ToolContext ready for tool testing.
  """
  from google.adk.tools import ToolContext

  invocation_ctx = await create_invocation_context(
    agent, state=state, artifacts=artifacts
  )
  return ToolContext(invocation_ctx)


async def create_callback_context(
  agent: LlmAgent,
  *,
  state: dict[str, Any] | None = None,
  artifacts: dict[str, str | bytes] | None = None,
) -> CallbackContext:
  """
  Create a CallbackContext for testing plugin callbacks.

  Args:
      agent: The agent for context.
      state: Initial session state dict.
      artifacts: Dict of filename -> content to pre-save.

  Returns:
      CallbackContext ready for callback testing.
  """
  from google.adk.agents.callback_context import CallbackContext

  invocation_ctx = await create_invocation_context(
    agent, state=state, artifacts=artifacts
  )
  return CallbackContext(invocation_ctx)


async def create_readonly_context(
  agent: LlmAgent,
  *,
  state: dict[str, Any] | None = None,
  artifacts: dict[str, str | bytes] | None = None,
) -> ReadonlyContext:
  """
  Create a ReadonlyContext for testing instruction providers.

  Args:
      agent: The agent for context.
      state: Initial session state dict.
      artifacts: Dict of filename -> content to pre-save.

  Returns:
      ReadonlyContext ready for instruction provider testing.
  """
  from google.adk.agents.readonly_context import ReadonlyContext

  invocation_ctx = await create_invocation_context(
    agent, state=state, artifacts=artifacts
  )
  return ReadonlyContext(invocation_ctx)


def create_minimal_agent(
  name: str = "test_agent",
  responses: list[str | types.Part | list[types.Part]] | None = None,
) -> tuple[LlmAgent, FakeLlm]:
  """
  Create a minimal agent with FakeLlm for testing.

  Args:
      name: Agent name.
      responses: Scripted LLM responses.

  Returns:
      Tuple of (agent, fake_llm) so you can inspect requests.
  """
  fake_llm = FakeLlm.with_responses(responses or ["Default response"])
  agent = LlmAgent(name=name, model=fake_llm)
  return agent, fake_llm


def simplify_events(
  events: list[Any],
) -> list[tuple[str, str | types.Part]]:
  """
  Simplify event list for easier assertions.

  Args:
      events: List of ADK Event objects.

  Returns:
      List of (author, content) tuples where content is either
      the text string or the Part object (for function calls).
  """
  result = []
  for event in events:
    if not hasattr(event, "content") or event.content is None:
      continue

    author = getattr(event, "author", "unknown")

    for part in event.content.parts:
      if hasattr(part, "text") and part.text:
        result.append((author, part.text))  # type: ignore[reportUnknownMemberType]
      elif (hasattr(part, "function_call") and part.function_call) or (
        hasattr(part, "function_response") and part.function_response
      ):
        result.append((author, part))  # type: ignore[reportUnknownMemberType]

  return result
