"""Test configuration and shared fixtures."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
  """Register custom markers."""
  config.addinivalue_line(
    "markers",
    "integration: marks tests as integration tests (require API keys, slower)",
  )


def pytest_addoption(parser: pytest.Parser) -> None:
  """Add custom command line options."""
  parser.addoption(
    "--run-integration",
    action="store_true",
    default=False,
    help="run integration tests",
  )


def pytest_collection_modifyitems(
  config: pytest.Config,
  items: list[pytest.Item],
) -> None:
  """Skip integration tests unless --run-integration is passed."""
  if config.getoption("--run-integration"):
    return

  skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
  for item in items:
    if "integration" in item.keywords:
      item.add_marker(skip_integration)
