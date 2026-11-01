from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings with safe local demo defaults."""

    model_config = SettingsConfigDict(env_prefix="")

    app_env: str = "development"
    app_version: str = "0.1.0"
    app_name: str = "Entrega Clara"
    demo_mode: bool = True
    persistence_mode: str = "memory"
    default_locale: str = "pt-BR"
    default_currency: str = "BRL"
    tracking_update_interval_seconds: int = 2
    routing_graph_path: str = ""
    #: Time-of-day speed profile. Empty means the committed default
    #: (data/graph/traffic-profile.json); routing stays static if it is missing.
    traffic_profile_path: str = ""
    public_web_origin: str = "http://localhost:3000"
    maptiler_api_key: str = ""
    maptiler_style_url: str = ""


settings = Settings()
