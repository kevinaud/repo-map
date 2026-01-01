"""Model pricing configuration for Navigator cost tracking.

This module provides an object-oriented interface for model pricing and
registry management, using high-precision decimal arithmetic to match
GCP billing standards.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, Field

# GCP billing often tracks fractional cents (micro-dollars).
# We use 9 decimal places to ensure aggregation accuracy before rounding.
GCP_BILLING_PRECISION = Decimal("0.000000001")


class ModelPricing(BaseModel):
  """Represents pricing rates and cost calculation logic for a specific LLM.

  Uses Decimal for currency to avoid floating-point drift.
  """

  model_name: str
  input_per_million: Decimal = Field(gt=0, description="USD per 1M input tokens")
  output_per_million: Decimal = Field(gt=0, description="USD per 1M output tokens")

  def calculate_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
    """Calculate cost in USD based on this specific model's rates.

    Args:
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens

    Returns:
        Total cost quantized to 9 decimal places.
    """
    # Convert tokens to Decimal to ensure division doesn't cast back to float
    m_input = Decimal(input_tokens) / Decimal(1_000_000)
    m_output = Decimal(output_tokens) / Decimal(1_000_000)

    input_cost = m_input * self.input_per_million
    output_cost = m_output * self.output_per_million

    total_cost = input_cost + output_cost

    # Quantize to match GCP internal tracking precision
    return total_cost.quantize(GCP_BILLING_PRECISION, rounding=ROUND_HALF_UP)


class PricingRegistry:
  """Singleton-style registry to manage model lookup and configuration.

  Encapsulates the storage and retrieval logic for pricing configurations.
  """

  def __init__(self) -> None:
    self._models: dict[str, ModelPricing] = {}

  def register(self, pricing: ModelPricing) -> None:
    """Register a new pricing configuration."""
    self._models[pricing.model_name] = pricing

  def register_batch(self, pricing_list: list[ModelPricing]) -> None:
    """Register multiple configurations at once."""
    for p in pricing_list:
      self.register(p)

  def get_pricing(self, model_name: str) -> ModelPricing:
    """Retrieve pricing for a model. Supports exact and partial string matching.

    Args:
        model_name: The full or partial model name (e.g. "gemini-2.0-flash")

    Returns:
        ModelPricing object

    Raises:
        ValueError: If the model cannot be found.
    """
    # 1. Try exact match
    if model_name in self._models:
      return self._models[model_name]

    # 2. Try partial match (fuzzy lookup)
    for key, pricing in self._models.items():
      if key in model_name or model_name in key:
        return pricing

    raise ValueError(
      f"Unknown model: {model_name}. Known models: {', '.join(self._models.keys())}"
    )

  @property
  def model_names(self) -> list[str]:
    """Return list of registered model names."""
    return list(self._models.keys())


# Preset pricing configurations (as of Dec 2025)
# Source: https://ai.google.dev/gemini-api/docs/pricing

# Gemini 3 models
GEMINI_3_PRO_PRICING = ModelPricing(
  model_name="gemini-3-pro-preview",
  input_per_million=Decimal("2.00"),  # prompts <= 200k tokens
  output_per_million=Decimal("12.00"),  # including thinking tokens
)

GEMINI_3_FLASH_PRICING = ModelPricing(
  model_name="gemini-3-flash-preview",
  input_per_million=Decimal("0.50"),  # text/image/video
  output_per_million=Decimal("3.00"),  # including thinking tokens
)

# Gemini 2.5 models
GEMINI_25_PRO_PRICING = ModelPricing(
  model_name="gemini-2.5-pro",
  input_per_million=Decimal("1.25"),  # prompts <= 200k tokens
  output_per_million=Decimal("10.00"),  # including thinking tokens
)

GEMINI_25_FLASH_PRICING = ModelPricing(
  model_name="gemini-2.5-flash",
  input_per_million=Decimal("0.30"),  # text/image/video
  output_per_million=Decimal("2.50"),  # including thinking tokens
)

GEMINI_25_FLASH_LITE_PRICING = ModelPricing(
  model_name="gemini-2.5-flash-lite",
  input_per_million=Decimal("0.10"),  # text/image/video
  output_per_million=Decimal("0.40"),
)

# Gemini 2.0 models
GEMINI_20_FLASH_PRICING = ModelPricing(
  model_name="gemini-2.0-flash",
  input_per_million=Decimal("0.10"),  # text/image/video
  output_per_million=Decimal("0.40"),
)

GEMINI_20_FLASH_LITE_PRICING = ModelPricing(
  model_name="gemini-2.0-flash-lite",
  input_per_million=Decimal("0.075"),
  output_per_million=Decimal("0.30"),
)


def _create_default_registry() -> PricingRegistry:
  """Create and populate the default pricing registry."""
  registry = PricingRegistry()
  registry.register_batch(
    [
      GEMINI_3_PRO_PRICING,
      GEMINI_3_FLASH_PRICING,
      GEMINI_25_PRO_PRICING,
      GEMINI_25_FLASH_PRICING,
      GEMINI_25_FLASH_LITE_PRICING,
      GEMINI_20_FLASH_PRICING,
      GEMINI_20_FLASH_LITE_PRICING,
    ]
  )
  return registry


# Default global registry instance
default_registry = _create_default_registry()


def get_pricing_for_model(model_name: str) -> ModelPricing:
  """Get pricing for a specific model from the default registry.

  Args:
      model_name: The model identifier (e.g. "gemini-2.0-flash")

  Returns:
      ModelPricing object for the requested model
  """
  return default_registry.get_pricing(model_name)
