"""Unit tests for Navigator pricing utilities."""

from __future__ import annotations

import pytest

from repo_map.navigator.pricing import (
  GEMINI_3_FLASH_PRICING,
  GEMINI_3_PRO_PRICING,
  GEMINI_20_FLASH_PRICING,
  GEMINI_25_FLASH_PRICING,
  GEMINI_25_PRO_PRICING,
  ModelPricingRates,
  calculate_cost,
  get_pricing_for_model,
)


class TestModelPricingRates:
  """Tests for ModelPricingRates model."""

  def test_preset_gemini_3_flash(self) -> None:
    """Test Gemini 3 Flash pricing."""
    assert GEMINI_3_FLASH_PRICING.model_name == "gemini-3-flash-preview"
    assert GEMINI_3_FLASH_PRICING.input_per_million == 0.50
    assert GEMINI_3_FLASH_PRICING.output_per_million == 3.00

  def test_preset_gemini_3_pro(self) -> None:
    """Test Gemini 3 Pro pricing."""
    assert GEMINI_3_PRO_PRICING.model_name == "gemini-3-pro-preview"
    assert GEMINI_3_PRO_PRICING.input_per_million == 2.00
    assert GEMINI_3_PRO_PRICING.output_per_million == 12.00

  def test_preset_gemini_25_pro(self) -> None:
    """Test Gemini 2.5 Pro pricing."""
    assert GEMINI_25_PRO_PRICING.model_name == "gemini-2.5-pro"
    assert GEMINI_25_PRO_PRICING.input_per_million == 1.25
    assert GEMINI_25_PRO_PRICING.output_per_million == 10.00

  def test_preset_gemini_25_flash(self) -> None:
    """Test Gemini 2.5 Flash pricing."""
    assert GEMINI_25_FLASH_PRICING.model_name == "gemini-2.5-flash"
    assert GEMINI_25_FLASH_PRICING.input_per_million == 0.30
    assert GEMINI_25_FLASH_PRICING.output_per_million == 2.50

  def test_preset_gemini_20_flash(self) -> None:
    """Test Gemini 2.0 Flash pricing."""
    assert GEMINI_20_FLASH_PRICING.model_name == "gemini-2.0-flash"
    assert GEMINI_20_FLASH_PRICING.input_per_million == 0.10
    assert GEMINI_20_FLASH_PRICING.output_per_million == 0.40

  def test_custom_pricing(self) -> None:
    """Test creating custom pricing rates."""
    custom = ModelPricingRates(
      model_name="custom-model",
      input_per_million=0.50,
      output_per_million=1.50,
    )
    assert custom.model_name == "custom-model"
    assert custom.input_per_million == 0.50
    assert custom.output_per_million == 1.50

  def test_pricing_must_be_positive(self) -> None:
    """Test that pricing rates must be positive."""
    with pytest.raises(ValueError, match="greater than 0"):
      ModelPricingRates(
        model_name="test",
        input_per_million=0,
        output_per_million=1.0,
      )

    with pytest.raises(ValueError, match="greater than 0"):
      ModelPricingRates(
        model_name="test",
        input_per_million=1.0,
        output_per_million=-0.5,
      )


class TestCalculateCost:
  """Tests for calculate_cost function."""

  def test_zero_tokens(self) -> None:
    """Test cost calculation with zero tokens."""
    cost = calculate_cost(0, 0, GEMINI_20_FLASH_PRICING)
    assert cost == 0.0

  def test_input_only(self) -> None:
    """Test cost calculation with only input tokens."""
    # 1M input tokens at $0.10
    cost = calculate_cost(1_000_000, 0, GEMINI_20_FLASH_PRICING)
    assert cost == pytest.approx(0.10, rel=1e-6)

  def test_output_only(self) -> None:
    """Test cost calculation with only output tokens."""
    # 1M output tokens at $0.40
    cost = calculate_cost(0, 1_000_000, GEMINI_20_FLASH_PRICING)
    assert cost == pytest.approx(0.40, rel=1e-6)

  def test_typical_iteration(self) -> None:
    """Test cost for a typical Navigator iteration.

    10k input tokens + 2k output tokens using Gemini 2.0 Flash.
    """
    cost = calculate_cost(10_000, 2_000, GEMINI_20_FLASH_PRICING)
    # Input: (10,000 / 1,000,000) x $0.10 = $0.001
    # Output: (2,000 / 1,000,000) x $0.40 = $0.0008
    # Total: $0.0018
    expected = 0.001 + 0.0008
    assert cost == pytest.approx(expected, rel=1e-6)

  def test_gemini_25_pro_pricing(self) -> None:
    """Test cost calculation with Gemini 2.5 Pro (more expensive)."""
    cost = calculate_cost(10_000, 2_000, GEMINI_25_PRO_PRICING)
    # Input: (10,000 / 1,000,000) x $1.25 = $0.0125
    # Output: (2,000 / 1,000,000) x $10.00 = $0.02
    # Total: $0.0325
    expected = 0.0125 + 0.02
    assert cost == pytest.approx(expected, rel=1e-6)

  def test_large_context(self) -> None:
    """Test cost for large context (100k tokens)."""
    cost = calculate_cost(100_000, 5_000, GEMINI_20_FLASH_PRICING)
    # Input: (100,000 / 1,000,000) x $0.10 = $0.01
    # Output: (5,000 / 1,000,000) x $0.40 = $0.002
    # Total: $0.012
    expected = 0.01 + 0.002
    assert cost == pytest.approx(expected, rel=1e-6)


class TestGetPricingForModel:
  """Tests for get_pricing_for_model function."""

  def test_exact_match_gemini_20_flash(self) -> None:
    """Test exact match for Gemini 2.0 Flash."""
    pricing = get_pricing_for_model("gemini-2.0-flash")
    assert pricing == GEMINI_20_FLASH_PRICING

  def test_exact_match_gemini_25_pro(self) -> None:
    """Test exact match for Gemini 2.5 Pro."""
    pricing = get_pricing_for_model("gemini-2.5-pro")
    assert pricing == GEMINI_25_PRO_PRICING

  def test_exact_match_gemini_3_flash(self) -> None:
    """Test exact match for Gemini 3 Flash."""
    pricing = get_pricing_for_model("gemini-3-flash-preview")
    assert pricing == GEMINI_3_FLASH_PRICING

  def test_unknown_model_raises(self) -> None:
    """Test that unknown model raises ValueError."""
    with pytest.raises(ValueError, match="Unknown model"):
      get_pricing_for_model("completely-unknown-model-xyz")

  def test_partial_match(self) -> None:
    """Test partial matching for model variants."""
    # Should find gemini-2.0-flash when given a variant name
    pricing = get_pricing_for_model("models/gemini-2.0-flash")
    assert pricing.model_name == "gemini-2.0-flash"


class TestCostEstimationScenarios:
  """Tests for real-world cost estimation scenarios."""

  def test_full_exploration_budget_2_dollars(self) -> None:
    """Test how many iterations fit in $2 budget."""
    # Typical iteration: 10k input + 2k output = ~$0.0018
    cost_per_iteration = calculate_cost(10_000, 2_000, GEMINI_20_FLASH_PRICING)
    max_iterations = 2.0 / cost_per_iteration

    # Should allow many iterations (>1000)
    assert max_iterations > 1000

  def test_budget_exhaustion_scenario(self) -> None:
    """Test accumulated cost tracking."""
    budget = 0.05  # $0.05 budget
    total_cost = 0.0
    iterations = 0

    while total_cost < budget:
      iteration_cost = calculate_cost(10_000, 2_000, GEMINI_20_FLASH_PRICING)
      if total_cost + iteration_cost > budget:
        break
      total_cost += iteration_cost
      iterations += 1

    # With $0.05 budget and ~$0.0018 per iteration
    # Should get ~27 iterations
    assert 20 < iterations < 40
    assert total_cost < budget
