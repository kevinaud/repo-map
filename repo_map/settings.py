import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
  log_level: str = "INFO"

  # API Keys
  gemini_api_key: str | None = Field(
    default=None,
    description="Gemini API key for Navigator agent",
  )

  # Navigator Agent settings
  navigator_model: str = "gemini-3-flash-preview"
  navigator_default_token_budget: int = 20000
  navigator_default_cost_limit_usd: float = 2.0

  model_config = SettingsConfigDict(
    env_file=(".env", ".env.secrets"),
    env_file_encoding="utf-8",
    extra="ignore",
  )

  def configure_api_key(self) -> None:
    """Set GOOGLE_API_KEY env var from gemini_api_key if available.

    The Google ADK expects GOOGLE_API_KEY to be set in the environment.
    This method bridges our GEMINI_API_KEY setting to what the SDK expects.
    """
    if self.gemini_api_key and not os.environ.get("GOOGLE_API_KEY"):
      os.environ["GOOGLE_API_KEY"] = self.gemini_api_key


settings = Settings()
# Configure API key on module load
settings.configure_api_key()
