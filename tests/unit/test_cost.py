"""Unit tests for cost estimation utilities."""

from __future__ import annotations

from repo_map.core.cost import (
  CostManifest,
  calculate_file_costs,
  estimate_tokens,
  format_budget_warning,
  format_cost_annotation,
)
from repo_map.core.verbosity import VerbosityLevel


class TestEstimateTokens:
  """Test token estimation."""

  def test_empty_string(self) -> None:
    """Test empty string returns 0."""
    assert estimate_tokens("") == 0

  def test_short_string(self) -> None:
    """Test short string estimation."""
    # 4 chars = 1 token
    assert estimate_tokens("1234") == 1

  def test_typical_code(self) -> None:
    """Test estimation on typical code."""
    code = "def hello_world():\n    print('Hello, World!')\n"
    tokens = estimate_tokens(code)
    # ~48 chars / 4 = 12 tokens
    assert tokens == len(code) // 4

  def test_consistency_with_repomap(self) -> None:
    """Test that estimation matches RepoMap's heuristic."""
    # This test ensures we're using the same algorithm
    text = "x" * 400
    assert estimate_tokens(text) == 100


class TestCalculateFileCosts:
  """Test file cost calculation."""

  def test_full_content_only(self) -> None:
    """Test costs with only full content provided."""
    content = "x" * 400  # 100 tokens at L4
    costs = calculate_file_costs(content)

    assert costs[VerbosityLevel.EXCLUDE] == 0
    assert costs[VerbosityLevel.EXISTENCE] == 5  # Fixed estimate
    assert costs[VerbosityLevel.STRUCTURE] == 15  # ~15% of L4
    assert costs[VerbosityLevel.INTERFACE] == 40  # ~40% of L4
    assert costs[VerbosityLevel.IMPLEMENTATION] == 100

  def test_with_structure_content(self) -> None:
    """Test costs with explicit structure content."""
    content = "x" * 400
    structure = "x" * 60  # 15 tokens

    costs = calculate_file_costs(content, structure_content=structure)
    assert costs[VerbosityLevel.STRUCTURE] == 15

  def test_with_interface_content(self) -> None:
    """Test costs with explicit interface content."""
    content = "x" * 400
    interface = "x" * 160  # 40 tokens

    costs = calculate_file_costs(content, interface_content=interface)
    assert costs[VerbosityLevel.INTERFACE] == 40

  def test_all_levels_present(self) -> None:
    """Test that all 5 levels are in result."""
    costs = calculate_file_costs("hello")
    assert len(costs) == 5
    assert all(level in costs for level in VerbosityLevel)


class TestFormatCostAnnotation:
  """Test cost annotation formatting."""

  def test_basic_format(self) -> None:
    """Test basic annotation format."""
    costs = {
      VerbosityLevel.EXISTENCE: 5,
      VerbosityLevel.STRUCTURE: 50,
      VerbosityLevel.INTERFACE: 120,
      VerbosityLevel.IMPLEMENTATION: 340,
    }
    result = format_cost_annotation("src/main.py", costs)
    assert result == "# src/main.py [L1:5 L2:50 L3:120 L4:340]"

  def test_missing_levels_use_zero(self) -> None:
    """Test that missing levels default to 0."""
    costs = {VerbosityLevel.IMPLEMENTATION: 100}
    result = format_cost_annotation("test.py", costs)
    assert "L1:0" in result
    assert "L4:100" in result


class TestFormatBudgetWarning:
  """Test budget warning formatting."""

  def test_warning_format(self) -> None:
    """Test warning message format."""
    result = format_budget_warning(budget=20000, actual=25340)
    assert "25340" in result
    assert "20000" in result
    assert "+5340" in result
    assert "BUDGET EXCEEDED" in result


class TestCostManifest:
  """Test CostManifest tracking."""

  def test_initial_state(self) -> None:
    """Test initial manifest state."""
    manifest = CostManifest(budget=10000)
    assert manifest.budget == 10000
    assert manifest.actual == 0
    assert manifest.overrun == 0
    assert manifest.is_over_budget is False

  def test_add_file(self) -> None:
    """Test adding file costs."""
    manifest = CostManifest(budget=10000)
    costs = {
      VerbosityLevel.EXISTENCE: 5,
      VerbosityLevel.STRUCTURE: 50,
      VerbosityLevel.INTERFACE: 120,
      VerbosityLevel.IMPLEMENTATION: 340,
    }
    manifest.add_file("src/main.py", costs, VerbosityLevel.INTERFACE)

    assert "src/main.py" in manifest.files
    assert manifest.actual == 120  # L3 cost

  def test_multiple_files(self) -> None:
    """Test adding multiple files."""
    manifest = CostManifest(budget=500)
    costs1 = {VerbosityLevel.IMPLEMENTATION: 200}
    costs2 = {VerbosityLevel.IMPLEMENTATION: 150}

    manifest.add_file("a.py", costs1, VerbosityLevel.IMPLEMENTATION)
    manifest.add_file("b.py", costs2, VerbosityLevel.IMPLEMENTATION)

    assert manifest.actual == 350
    assert manifest.is_over_budget is False

  def test_over_budget(self) -> None:
    """Test budget overrun detection."""
    manifest = CostManifest(budget=100)
    costs = {VerbosityLevel.IMPLEMENTATION: 150}
    manifest.add_file("big.py", costs, VerbosityLevel.IMPLEMENTATION)

    assert manifest.is_over_budget is True
    assert manifest.overrun == 50

  def test_total_at_level(self) -> None:
    """Test calculating totals at different levels."""
    manifest = CostManifest(budget=10000)
    costs1 = {
      VerbosityLevel.EXISTENCE: 5,
      VerbosityLevel.IMPLEMENTATION: 200,
    }
    costs2 = {
      VerbosityLevel.EXISTENCE: 5,
      VerbosityLevel.IMPLEMENTATION: 300,
    }

    manifest.add_file("a.py", costs1, VerbosityLevel.IMPLEMENTATION)
    manifest.add_file("b.py", costs2, VerbosityLevel.IMPLEMENTATION)

    assert manifest.total_at_level(VerbosityLevel.EXISTENCE) == 10
    assert manifest.total_at_level(VerbosityLevel.IMPLEMENTATION) == 500

  def test_get_top_contributors(self) -> None:
    """Test getting top contributing files."""
    manifest = CostManifest(budget=10000)
    costs_small = {VerbosityLevel.IMPLEMENTATION: 100}
    costs_large = {VerbosityLevel.IMPLEMENTATION: 500}
    costs_medium = {VerbosityLevel.IMPLEMENTATION: 250}

    manifest.add_file("small.py", costs_small, VerbosityLevel.IMPLEMENTATION)
    manifest.add_file("large.py", costs_large, VerbosityLevel.IMPLEMENTATION)
    manifest.add_file("medium.py", costs_medium, VerbosityLevel.IMPLEMENTATION)

    top = manifest.get_top_contributors(2)
    assert len(top) == 2
    assert top[0][0] == "large.py"
    assert top[0][1] == 500
