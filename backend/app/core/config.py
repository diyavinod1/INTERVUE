"""
Central application configuration.

Everything here is loaded from environment variables (via a `.env` file in
development). Nothing secret is ever hard-coded, and nothing secret is ever
put on a schema that gets sent to the frontend (see api/routes for the one
explicit "public config" endpoint that hand-picks safe fields).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- App ----
    environment: str = "development"
    log_level: str = "INFO"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    # ---- Database ----
    database_url: str = "sqlite:///./intervue.db"

    # ---- Supabase (optional, only used for storage / auth if configured) ----
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # ---- OpenRouter (LLM) ----
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"
    openrouter_fallback_model: str = "meta-llama/llama-3.1-70b-instruct"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: int = 30
    openrouter_max_retries: int = 2

    # ---- Sarvam (Voice) ----
    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_tts_voice: str = "meera"
    sarvam_stt_language: str = "en-IN"
    enable_voice_fallback: bool = True

    # ---- Uploads ----
    max_resume_size_mb: int = 5

    # ---- Interview tuning ----
    min_questions: int = 6
    max_questions: int = 12


@lru_cache
def get_settings() -> Settings:
    """Settings are cached so the .env file is only parsed once per process."""
    return Settings()
