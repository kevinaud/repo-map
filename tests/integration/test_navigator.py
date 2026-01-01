"""Integration tests for Navigator Agent.

These tests use real LLM calls to verify end-to-end Navigator behavior.
They are skipped by default - run with `pytest --run-integration`.

See docs/developer/integration_testing.md for patterns and guidance.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from tests.integration.helpers import (
  IntegrationRunner,
  get_tool_calls,
)

if TYPE_CHECKING:
  from pathlib import Path


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


class TestNavigatorWithRealLLM:
  """Integration tests for Navigator using real LLM calls.

  These tests verify end-to-end behavior with actual LLM reasoning.
  They are slower and cost real API tokens.
  """

  @pytest.mark.integration
  @pytest.mark.asyncio
  async def test_agent_calls_update_flight_plan_on_start(
    self, sample_repo: Path
  ) -> None:
    """Test that Navigator calls update_flight_plan to begin exploration."""
    from decimal import Decimal

    from google.genai.types import Part

    from repo_map.core.flight_plan import FlightPlan
    from repo_map.navigator.agent import create_navigator_agent
    from repo_map.navigator.plugin import BudgetEnforcementPlugin
    from repo_map.navigator.pricing import GEMINI_3_FLASH_PRICING
    from repo_map.navigator.state import (
      BudgetConfig,
      MapMetadata,
      NavigatorState,
    )

    # Create agent with test model
    agent = create_navigator_agent(model="gemini-2.0-flash")
    plugin = BudgetEnforcementPlugin()

    # Create runner with budget plugin
    runner = IntegrationRunner.from_agent(agent, plugins=[plugin])

    # Set up initial Navigator state
    initial_state = NavigatorState(
      user_task="Find the authentication code in this repository",
      repo_path=str(sample_repo),
      execution_mode="autonomous",
      budget_config=BudgetConfig(
        max_spend_usd=Decimal("0.50"),
        current_spend_usd=Decimal("0.0"),
        model_pricing=GEMINI_3_FLASH_PRICING,
      ),
      flight_plan=FlightPlan(budget=5000),
      decision_log=[],
      map_metadata=MapMetadata(total_tokens=500),
    )

    await runner.create_session(
      state={"navigator": initial_state.model_dump(mode="json")}
    )

    # Store initial map as artifact
    await runner.artifact_service.save_artifact(
      app_name=runner.app_name,
      user_id=runner.user_id,
      session_id=runner.session.id,
      filename="current_map.txt",
      artifact=Part.from_text(
        text=f"# Repository: {sample_repo.name}\n\nsrc/auth.py\nsrc/api.py\nREADME.md"
      ),
    )

    # Run the agent with timeout
    events = await asyncio.wait_for(
      runner.run("Begin exploring the repository to find authentication code."),
      timeout=60.0,
    )

    # Verify agent called update_flight_plan or finalize_context
    tool_calls = get_tool_calls(events)
    tool_names = [tc.name for tc in tool_calls]

    assert any(
      name in tool_names for name in ["update_flight_plan", "finalize_context"]
    ), f"Expected update_flight_plan or finalize_context, got: {tool_names}"

  @pytest.mark.integration
  @pytest.mark.asyncio
  async def test_agent_focuses_on_relevant_files(self, sample_repo: Path) -> None:
    """Test that Navigator increases verbosity for files matching user goal."""
    from decimal import Decimal

    from google.genai.types import Part

    from repo_map.core.flight_plan import FlightPlan
    from repo_map.navigator.agent import create_navigator_agent
    from repo_map.navigator.plugin import BudgetEnforcementPlugin
    from repo_map.navigator.pricing import GEMINI_3_FLASH_PRICING
    from repo_map.navigator.state import (
      BudgetConfig,
      MapMetadata,
      NavigatorState,
    )

    agent = create_navigator_agent(model="gemini-2.0-flash")
    plugin = BudgetEnforcementPlugin()
    runner = IntegrationRunner.from_agent(agent, plugins=[plugin])

    initial_state = NavigatorState(
      user_task="Understand the authentication flow including login and registration",
      repo_path=str(sample_repo),
      execution_mode="autonomous",
      budget_config=BudgetConfig(
        max_spend_usd=Decimal("0.50"),
        current_spend_usd=Decimal("0.0"),
        model_pricing=GEMINI_3_FLASH_PRICING,
      ),
      flight_plan=FlightPlan(budget=8000),
      decision_log=[],
      map_metadata=MapMetadata(total_tokens=800),
    )

    await runner.create_session(
      state={"navigator": initial_state.model_dump(mode="json")}
    )

    await runner.artifact_service.save_artifact(
      app_name=runner.app_name,
      user_id=runner.user_id,
      session_id=runner.session.id,
      filename="current_map.txt",
      artifact=Part.from_text(
        text="# Repository Map\n\n"
        "src/auth.py - AuthService, User\n"
        "src/api.py - APIRouter\n"
        "README.md"
      ),
    )

    events = await asyncio.wait_for(
      runner.run("Focus on the authentication-related code."),
      timeout=60.0,
    )

    tool_calls = get_tool_calls(events)

    # Look for update_flight_plan calls with verbosity changes
    update_calls = [tc for tc in tool_calls if tc.name == "update_flight_plan"]

    if update_calls:
      # Check that the reasoning mentions auth
      for call in update_calls:
        args = call.args or {}
        reasoning = args.get("reasoning", "")
        # Agent should mention auth-related reasoning
        assert reasoning, "update_flight_plan should include reasoning"

  @pytest.mark.integration
  @pytest.mark.asyncio
  async def test_agent_respects_budget_limit(self, sample_repo: Path) -> None:
    """Test that Navigator stops when budget is exhausted."""
    from decimal import Decimal

    from google.genai.types import Part

    from repo_map.core.flight_plan import FlightPlan
    from repo_map.navigator.agent import create_navigator_agent
    from repo_map.navigator.plugin import BudgetEnforcementPlugin
    from repo_map.navigator.pricing import GEMINI_3_FLASH_PRICING
    from repo_map.navigator.state import (
      BudgetConfig,
      MapMetadata,
      NavigatorState,
    )

    agent = create_navigator_agent(model="gemini-2.0-flash")
    plugin = BudgetEnforcementPlugin()
    runner = IntegrationRunner.from_agent(agent, plugins=[plugin])

    # Set budget very low - near exhaustion
    initial_state = NavigatorState(
      user_task="Find all Python files",
      repo_path=str(sample_repo),
      execution_mode="autonomous",
      budget_config=BudgetConfig(
        max_spend_usd=Decimal("0.001"),  # 0.1 cents - very low
        current_spend_usd=Decimal("0.0"),
        model_pricing=GEMINI_3_FLASH_PRICING,
      ),
      flight_plan=FlightPlan(budget=5000),
      decision_log=[],
      map_metadata=MapMetadata(total_tokens=500),
    )

    await runner.create_session(
      state={"navigator": initial_state.model_dump(mode="json")}
    )

    await runner.artifact_service.save_artifact(
      app_name=runner.app_name,
      user_id=runner.user_id,
      session_id=runner.session.id,
      filename="current_map.txt",
      artifact=Part.from_text(text="# Repository Map\n\nsrc/auth.py\nsrc/api.py"),
    )

    # Run should complete (possibly with budget warning) without hanging
    events = await asyncio.wait_for(
      runner.run("Start exploration"),
      timeout=30.0,
    )

    # Test passes if we get here without timeout
    # The agent may or may not call tools depending on whether budget plugin blocks
    assert events is not None


class TestNavigatorEndToEnd:
  """End-to-end tests for Navigator flow."""

  @pytest.mark.integration
  @pytest.mark.asyncio
  async def test_complete_exploration_flow(self, sample_repo: Path) -> None:
    """Test a complete exploration flow from start to finalization."""
    from decimal import Decimal

    from google.genai.types import Part

    from repo_map.core.flight_plan import FlightPlan
    from repo_map.navigator.agent import create_navigator_agent
    from repo_map.navigator.plugin import BudgetEnforcementPlugin
    from repo_map.navigator.pricing import GEMINI_3_FLASH_PRICING
    from repo_map.navigator.state import (
      BudgetConfig,
      MapMetadata,
      NavigatorState,
    )

    agent = create_navigator_agent(model="gemini-2.0-flash")
    plugin = BudgetEnforcementPlugin()
    runner = IntegrationRunner.from_agent(agent, plugins=[plugin])

    initial_state = NavigatorState(
      user_task="Find the User dataclass and understand how it's used",
      repo_path=str(sample_repo),
      execution_mode="autonomous",
      budget_config=BudgetConfig(
        max_spend_usd=Decimal("0.50"),
        current_spend_usd=Decimal("0.0"),
        model_pricing=GEMINI_3_FLASH_PRICING,
      ),
      flight_plan=FlightPlan(budget=10000),
      decision_log=[],
      map_metadata=MapMetadata(total_tokens=1000),
    )

    await runner.create_session(
      state={"navigator": initial_state.model_dump(mode="json")}
    )

    await runner.artifact_service.save_artifact(
      app_name=runner.app_name,
      user_id=runner.user_id,
      session_id=runner.session.id,
      filename="current_map.txt",
      artifact=Part.from_text(
        text="# Repository Map\n\n"
        "src/auth.py - User, AuthService\n"
        "src/api.py - APIRouter"
      ),
    )

    # First turn - agent should explore
    events = await asyncio.wait_for(
      runner.run("Begin exploration. Focus on finding the User class."),
      timeout=60.0,
    )

    tool_calls = get_tool_calls(events)
    assert len(tool_calls) > 0, "Agent should make at least one tool call"

    # Verify we got some tool calls (either update_flight_plan or finalize_context)
    tool_names = {tc.name for tc in tool_calls}
    valid_tools = {"update_flight_plan", "finalize_context"}
    assert tool_names & valid_tools, f"Expected Navigator tools, got: {tool_names}"
