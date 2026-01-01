"""Model pricing configuration for Navigator cost tracking.

This module provides pricing data for various LLM models and cost calculation
utilities for budget enforcement.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelPricingRates(BaseModel):
  """Token pricing rates per million tokens."""

  model_name: str
  input_per_million: float = Field(gt=0, description="USD per 1M input tokens")
  output_per_million: float = Field(gt=0, description="USD per 1M output tokens")


# Preset pricing configurations (as of Dec 2025)
# Source: https://ai.google.dev/gemini-api/docs/pricing

# Gemini 3 models
GEMINI_3_PRO_PRICING = ModelPricingRates(
  model_name="gemini-3-pro-preview",
  input_per_million=2.00,  # prompts <= 200k tokens
  output_per_million=12.00,  # including thinking tokens
)

GEMINI_3_FLASH_PRICING = ModelPricingRates(
  model_name="gemini-3-flash-preview",
  input_per_million=0.50,  # text/image/video
  output_per_million=3.00,  # including thinking tokens
)

# Gemini 2.5 models
GEMINI_25_PRO_PRICING = ModelPricingRates(
  model_name="gemini-2.5-pro",
  input_per_million=1.25,  # prompts <= 200k tokens
  output_per_million=10.00,  # including thinking tokens
)

GEMINI_25_FLASH_PRICING = ModelPricingRates(
  model_name="gemini-2.5-flash",
  input_per_million=0.30,  # text/image/video
  output_per_million=2.50,  # including thinking tokens
)

GEMINI_25_FLASH_LITE_PRICING = ModelPricingRates(
  model_name="gemini-2.5-flash-lite",
  input_per_million=0.10,  # text/image/video
  output_per_million=0.40,
)

# Gemini 2.0 models
GEMINI_20_FLASH_PRICING = ModelPricingRates(
  model_name="gemini-2.0-flash",
  input_per_million=0.10,  # text/image/video
  output_per_million=0.40,
)

GEMINI_20_FLASH_LITE_PRICING = ModelPricingRates(
  model_name="gemini-2.0-flash-lite",
  input_per_million=0.075,
  output_per_million=0.30,
)

# Mapping of model names to pricing
MODEL_PRICING_MAP: dict[str, ModelPricingRates] = {
  # Gemini 3
  "gemini-3-pro-preview": GEMINI_3_PRO_PRICING,
  "gemini-3-flash-preview": GEMINI_3_FLASH_PRICING,
  # Gemini 2.5
  "gemini-2.5-pro": GEMINI_25_PRO_PRICING,
  "gemini-2.5-flash": GEMINI_25_FLASH_PRICING,
  "gemini-2.5-flash-lite": GEMINI_25_FLASH_LITE_PRICING,
  # Gemini 2.0
  "gemini-2.0-flash": GEMINI_20_FLASH_PRICING,
  "gemini-2.0-flash-lite": GEMINI_20_FLASH_LITE_PRICING,
}


def calculate_cost(
  input_tokens: int,
  output_tokens: int,
  pricing: ModelPricingRates,
) -> float:
  """Calculate cost in USD from token counts.

  Args:
      input_tokens: Number of input/prompt tokens
      output_tokens: Number of output/completion tokens
      pricing: Pricing rates for the model

  Returns:
      Total cost in USD
  """
  input_cost = (input_tokens / 1_000_000) * pricing.input_per_million
  output_cost = (output_tokens / 1_000_000) * pricing.output_per_million
  return input_cost + output_cost


def get_pricing_for_model(model_name: str) -> ModelPricingRates:
  """Get pricing rates for a model by name.

  Args:
      model_name: Model identifier (e.g., "gemini-2.0-flash")

  Returns:
      ModelPricingRates for the model

  Raises:
      ValueError: If model name is not recognized
  """
  if model_name in MODEL_PRICING_MAP:
    return MODEL_PRICING_MAP[model_name]

  # Try to find a partial match
  for key, pricing in MODEL_PRICING_MAP.items():
    if key in model_name or model_name in key:
      return pricing

  raise ValueError(
    f"Unknown model: {model_name}. Known models: {', '.join(MODEL_PRICING_MAP.keys())}"
  )
