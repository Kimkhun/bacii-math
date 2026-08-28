from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bacii"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-secret-change-me-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    gemini_project: str = ""
    gemini_location: str = "global"
    gemini_model: str = "gemini-3.5-flash"
    gemini_vision_model: str = ""
    google_application_credentials: str = ""

    ollama_url: str = "http://localhost:11434/api/generate"
    text_model: str = "qwen2.5:3b"
    vision_model: str = "qwen2.5vl:3b"

    # Handwriting OCR provider: "gemini" (Vertex cloud vision, default),
    # "ollama" (local), or "fallback" (try ollama, then gemini on failure).
    vision_provider: str = "gemini"

    gemini_rate_limit_per_minute: int = 10
    explanation_cache_ttl_seconds: int = 86400

    # Hard cap on each Gemini (Vertex) call so a slow/hanging request can't
    # stall the Gemini -> Ollama -> deterministic fallback chain (seconds).
    gemini_timeout_seconds: int = 45


settings = Settings()
