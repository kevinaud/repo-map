from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
  log_level: str = "INFO"

  model_config = SettingsConfigDict(
    env_file=(".env", ".env.secrets"),
    env_file_encoding="utf-8",
    extra="ignore",
  )


settings = Settings()
