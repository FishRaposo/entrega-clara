from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings with safe local demo defaults."""

    model_config = SettingsConfigDict(env_prefix="")

    app_env: str = "development"
    app_version: str = "0.1.0"
    demo_mode: bool = True


settings = Settings()
