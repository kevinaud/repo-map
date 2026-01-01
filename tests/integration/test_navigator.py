"""Integration tests for Navigator Agent."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
  from pathlib import Path

import pytest

from repo_map.core.flight_plan import FlightPlan
from repo_map.navigator.plugin import BudgetEnforcementPlugin
from repo_map.navigator.pricing import GEMINI_3_FLASH_PRICING
from repo_map.navigator.runner import (
  NavigatorOutput,
  NavigatorProgress,
  create_navigator_runner,
  initialize_session,
  run_autonomous,
)
from repo_map.navigator.state import (
  BudgetConfig,
  DecisionLogEntry,
  MapMetadata,
  NavigatorState,
)


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
  """Create a sample repository for Navigator integration tests."""
  # Create src directory with Python code
  src = tmp_path / "src"
  src.mkdir()

  (src / "__init__.py").write_text('"""Source package."""\n')

  (src / "auth.py").write_text('''"""Authentication module."""

from dataclasses import dataclass


@dataclass
class User:
    """A user entity."""
    username: str
    email: str
    password_hash: str


class AuthService:
    """Service for authentication operations."""

    def __init__(self, secret_key: str) -> None:
        """Initialize with secret key."""
        self.secret_key = secret_key
        self._users: dict[str, User] = {}

    def register(self, username: str, email: str, password: str) -> User:
        """Register a new user."""
        from hashlib import sha256
        password_hash = sha256(password.encode()).hexdigest()
        user = User(username, email, password_hash)
        self._users[username] = user
        return user

    def login(self, username: str, password: str) -> bool:
        """Authenticate a user."""
        from hashlib import sha256
        if username not in self._users:
            return False
        user = self._users[username]
        password_hash = sha256(password.encode()).hexdigest()
        return user.password_hash == password_hash
''')

  (src / "api.py").write_text('''"""API endpoints."""

from typing import Any


class APIRouter:
    """Simple API router."""

    def __init__(self) -> None:
        self.routes: dict[str, callable] = {}

    def get(self, path: str):
        """Decorator for GET routes."""
        def decorator(func):
            self.routes[f"GET {path}"] = func
            return func
        return decorator

    def post(self, path: str):
        """Decorator for POST routes."""
        def decorator(func):
            self.routes[f"POST {path}"] = func
            return func
        return decorator


router = APIRouter()


@router.get("/users")
def list_users() -> list[dict[str, Any]]:
    """List all users."""
    return []


@router.post("/login")
def login_endpoint(username: str, password: str) -> dict[str, Any]:
    """Login endpoint."""
    return {"success": True}
''')

  # Create README
  (tmp_path / "README.md").write_text("""# Sample Project

A sample project for testing Navigator.

## Features

- User authentication
- RESTful API
- Data management

## Getting Started

Run `python -m src.main` to start.
""")

  return tmp_path


class TestNavigatorIntegration:
  """Integration tests for Navigator with mock LLM."""

  @pytest.mark.integration
  @pytest.mark.asyncio
  async def test_autonomous_exploration_with_mock_llm(self, sample_repo: Path) -> None:
    """Test that Navigator can run through exploration loop with mock LLM."""
    # This test uses mocks to verify the integration flow works
    # without making actual LLM calls

    runner, _budget_plugin = create_navigator_runner()

    # Initialize session
    await initialize_session(
      runner=runner,
      user_id="test-user",
      session_id="test-session",
      repo_path=sample_repo,
      user_task="Understand the authentication system",
      token_budget=5000,
      cost_limit=1.0,
      model="gemini-2.0-flash",
    )

    # Verify session was created with correct state
    session = await runner.session_service.get_session(
      app_name=runner.app_name,
      user_id="test-user",
      session_id="test-session",
    )

    assert session is not None
    state_dict = session.state.get("navigator", {})
    assert state_dict["user_task"] == "Understand the authentication system"
    assert state_dict["repo_path"] == str(sample_repo)

  @pytest.mark.integration
  @pytest.mark.asyncio
  async def test_runner_creates_valid_runner_components(self) -> None:
    """Test that create_navigator_runner returns valid components."""
    runner, plugin = create_navigator_runner()

    # Verify runner components
    assert runner.app_name == "repo-map-navigator"
    # Plugin is passed to Runner constructor; verify it's a valid instance
    assert isinstance(plugin, BudgetEnforcementPlugin)

    # Verify agent is configured
    assert runner.agent is not None
    assert runner.agent.name == "navigator"

  @pytest.mark.integration
  @pytest.mark.asyncio
  async def test_progress_events_yielded(self, sample_repo: Path) -> None:
    """Test that run_autonomous yields NavigatorProgress events."""
    # Create mock state that completes immediately
    state = NavigatorState.model_construct(
      user_task="Test task",
      repo_path=str(sample_repo),
      execution_mode="autonomous",
      budget_config=BudgetConfig(
        max_spend_usd=Decimal("1.0"),
        current_spend_usd=Decimal("0.01"),
        model_pricing=GEMINI_3_FLASH_PRICING,
      ),
      flight_plan=FlightPlan(budget=5000),
      decision_log=[
        DecisionLogEntry(
          step=1,
          action="update_flight_plan",
          reasoning="Initial exploration",
          config_patch=[],
        ),
      ],
      map_metadata=MapMetadata(total_tokens=500),
      exploration_complete=True,
      reasoning_summary="Found auth code",
      interactive_pause=False,
    )

    # Mock runner components
    mock_session = MagicMock()
    mock_session.state = {"navigator": state.model_dump(mode="json")}

    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = mock_session

    mock_artifact = MagicMock()
    mock_artifact.text = "# Mock Repository Map\n\nsrc/auth.py"
    mock_artifact_service = AsyncMock()
    mock_artifact_service.load_artifact.return_value = mock_artifact

    mock_runner = MagicMock()
    mock_runner.app_name = "test-app"
    mock_runner.session_service = mock_session_service
    mock_runner.artifact_service = mock_artifact_service

    async def mock_run_async(*args: Any, **kwargs: Any):
      event = MagicMock()
      event.is_final_response.return_value = True
      event.content = MagicMock()
      event.content.parts = []
      yield event

    mock_runner.run_async = mock_run_async
    mock_plugin = MagicMock()

    # Patch NavigatorState.model_validate to skip path validation
    def reconstruct_state(d: dict[str, Any]) -> NavigatorState:
      return NavigatorState.model_construct(
        user_task=d.get("user_task", ""),
        repo_path=d.get("repo_path", ""),
        execution_mode=d.get("execution_mode", "autonomous"),
        budget_config=BudgetConfig.model_validate(d.get("budget_config", {})),
        flight_plan=FlightPlan.model_validate(d.get("flight_plan", {})),
        decision_log=[
          DecisionLogEntry.model_validate(e) for e in d.get("decision_log", [])
        ],
        map_metadata=MapMetadata.model_validate(d.get("map_metadata", {})),
        interactive_pause=d.get("interactive_pause", False),
        exploration_complete=d.get("exploration_complete", False),
        reasoning_summary=d.get("reasoning_summary", ""),
      )

    with patch.object(NavigatorState, "model_validate", side_effect=reconstruct_state):
      results = [
        item
        async for item in run_autonomous(
          mock_runner, mock_plugin, "user-1", "session-1", max_iterations=5
        )
      ]

    # Should have progress event and output
    assert len(results) == 2
    assert isinstance(results[0], NavigatorProgress)
    assert isinstance(results[1], NavigatorOutput)

    # Verify output content
    output = results[1]
    assert output.context_string == "# Mock Repository Map\n\nsrc/auth.py"
    assert output.reasoning_summary == "Found auth code"
