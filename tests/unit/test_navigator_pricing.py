"""Unit tests for Navigator pricing utilities."""

from __future__ import annotations

from decimal import Decimal

import pytest

from repo_map.navigator.pricing import (
  GCP_BILLING_PRECISION,
  GEMINI_3_FLASH_PRICING,
  GEMINI_20_FLASH_PRICING,
  GEMINI_25_PRO_PRICING,
  ModelPricing,
  PricingRegistry,
  default_registry,
)


class TestModelPricing:
  """Tests for ModelPricing model."""

  def test_custom_pricing(self) -> None:
    """Test creating custom pricing rates."""
    custom = ModelPricing(
      model_name="custom-model",
      input_per_million=Decimal("0.50"),
      output_per_million=Decimal("1.50"),
    )
    assert custom.model_name == "custom-model"
    assert custom.input_per_million == Decimal("0.50")
    assert custom.output_per_million == Decimal("1.50")

  def test_pricing_must_be_positive(self) -> None:
    """Test that pricing rates must be positive."""
    with pytest.raises(ValueError, match="greater than 0"):
      ModelPricing(
        model_name="test",
        input_per_million=Decimal(0),
        output_per_million=Decimal("1.0"),
      )

    with pytest.raises(ValueError, match="greater than 0"):
      ModelPricing(
        model_name="test",
        input_per_million=Decimal("1.0"),
        output_per_million=Decimal("-0.5"),
      )


class TestModelPricingCalculateCost:
  """Tests for ModelPricing.calculate_cost method."""

  def test_zero_tokens(self) -> None:
    """Test cost calculation with zero tokens."""
    cost = GEMINI_20_FLASH_PRICING.calculate_cost(0, 0)
    assert cost == Decimal(0)

  def test_input_only(self) -> None:
    """Test cost calculation with only input tokens."""
    # 1M input tokens at $0.10
    cost = GEMINI_20_FLASH_PRICING.calculate_cost(1_000_000, 0)
    assert cost == Decimal("0.10").quantize(GCP_BILLING_PRECISION)

  def test_output_only(self) -> None:
    """Test cost calculation with only output tokens."""
    # 1M output tokens at $0.40
    cost = GEMINI_20_FLASH_PRICING.calculate_cost(0, 1_000_000)
    assert cost == Decimal("0.40").quantize(GCP_BILLING_PRECISION)

  def test_typical_iteration(self) -> None:
    """Test cost for a typical Navigator iteration.

    10k input tokens + 2k output tokens using Gemini 2.0 Flash.
    """
    cost = GEMINI_20_FLASH_PRICING.calculate_cost(10_000, 2_000)
    # Input: (10,000 / 1,000,000) x $0.10 = $0.001
    # Output: (2,000 / 1,000,000) x $0.40 = $0.0008
    # Total: $0.0018
    expected = Decimal("0.0018").quantize(GCP_BILLING_PRECISION)
    assert cost == expected

  def test_gemini_25_pro_pricing(self) -> None:
    """Test cost calculation with Gemini 2.5 Pro (more expensive)."""
    cost = GEMINI_25_PRO_PRICING.calculate_cost(10_000, 2_000)
    # Input: (10,000 / 1,000,000) x $1.25 = $0.0125
    # Output: (2,000 / 1,000,000) x $10.00 = $0.02
    # Total: $0.0325
    expected = Decimal("0.0325").quantize(GCP_BILLING_PRECISION)
    assert cost == expected

  def test_large_context(self) -> None:
    """Test cost for large context (100k tokens)."""
    cost = GEMINI_20_FLASH_PRICING.calculate_cost(100_000, 5_000)
    # Input: (100,000 / 1,000,000) x $0.10 = $0.01
    # Output: (5,000 / 1,000,000) x $0.40 = $0.002
    # Total: $0.012
    expected = Decimal("0.012").quantize(GCP_BILLING_PRECISION)
    assert cost == expected

  def test_sub_penny_precision(self) -> None:
    """Test that sub-penny amounts are preserved with 9 decimal places."""
    # Very small token count should produce sub-penny result
    cost = GEMINI_20_FLASH_PRICING.calculate_cost(100, 50)
    # Input: (100 / 1,000,000) x $0.10 = $0.00001
    # Output: (50 / 1,000,000) x $0.40 = $0.00002
    # Total: $0.00003
    expected = Decimal("0.00003").quantize(GCP_BILLING_PRECISION)
    assert cost == expected


class TestPricingRegistry:
  """Tests for PricingRegistry class."""

  def test_register_and_get(self) -> None:
    """Test registering and retrieving pricing."""
    registry = PricingRegistry()
    pricing = ModelPricing(
      model_name="test-model",
      input_per_million=Decimal("0.10"),
      output_per_million=Decimal("0.40"),
    )
    registry.register(pricing)
    assert registry.get("test-model") == pricing

  def test_register_batch(self) -> None:
    """Test registering multiple configurations at once."""
    registry = PricingRegistry()
    pricings = [
      ModelPricing(
        model_name="model-a",
        input_per_million=Decimal("0.10"),
        output_per_million=Decimal("0.40"),
      ),
      ModelPricing(
        model_name="model-b",
        input_per_million=Decimal("0.20"),
        output_per_million=Decimal("0.50"),
      ),
    ]
    registry.register_batch(pricings)
    assert registry.get("model-a").model_name == "model-a"
    assert registry.get("model-b").model_name == "model-b"

  def test_exact_match_gemini_20_flash(self) -> None:
    """Test exact match for Gemini 2.0 Flash."""
    pricing = default_registry.get("gemini-2.0-flash")
    assert pricing == GEMINI_20_FLASH_PRICING

  def test_exact_match_gemini_25_pro(self) -> None:
    """Test exact match for Gemini 2.5 Pro."""
    pricing = default_registry.get("gemini-2.5-pro")
    assert pricing == GEMINI_25_PRO_PRICING

  def test_exact_match_gemini_3_flash(self) -> None:
    """Test exact match for Gemini 3 Flash."""
    pricing = default_registry.get("gemini-3-flash-preview")
    assert pricing == GEMINI_3_FLASH_PRICING

  def test_unknown_model_raises(self) -> None:
    """Test that unknown model raises ValueError."""
    with pytest.raises(ValueError, match="Unknown model"):
      default_registry.get("completely-unknown-model-xyz")

  def test_partial_match(self) -> None:
    """Test partial matching for model variants."""
    # Should find gemini-2.0-flash when given a variant name
    pricing = default_registry.get("models/gemini-2.0-flash")
    assert pricing.model_name == "gemini-2.0-flash"

  def test_model_names_property(self) -> None:
    """Test that model_names returns list of registered models."""
    names = default_registry.model_names
    assert "gemini-2.0-flash" in names
    assert "gemini-3-flash-preview" in names


class TestCostEstimationScenarios:
  """Tests for real-world cost estimation scenarios."""

  def test_full_exploration_budget_half_dollar(self) -> None:
    """Test how many iterations fit in $0.50 budget."""
    # Typical iteration: 10k input + 2k output = ~$0.0018
    cost_per_iteration = GEMINI_20_FLASH_PRICING.calculate_cost(10_000, 2_000)
    max_iterations = Decimal("0.50") / cost_per_iteration

    # Should allow many iterations (>200)
    assert max_iterations > 200

  def test_budget_exhaustion_scenario(self) -> None:
    """Test accumulated cost tracking."""
    budget = Decimal("0.05")  # $0.05 budget
    total_cost = Decimal(0)
    iterations = 0

    while total_cost < budget:
      iteration_cost = GEMINI_20_FLASH_PRICING.calculate_cost(10_000, 2_000)
      if total_cost + iteration_cost > budget:
        break
      total_cost += iteration_cost
      iterations += 1

    # With $0.05 budget and ~$0.0018 per iteration
    # Should get ~27 iterations
    assert 20 < iterations < 40
    assert total_cost < budget
