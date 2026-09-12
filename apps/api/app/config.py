from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    mock_ai: bool = True
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    netlify_token: str = ""
    netlify_account_slug: str = ""

    vercel_token: str = ""
    vercel_team_id: str = ""
    vercel_oidc_token: str = ""

    autodev_internal_token: str = "change-me"
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
