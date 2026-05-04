"""Runtime configuration from environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "scribe-iq-backend"
    log_level: str = "INFO"

    database_url: str = "postgresql://rag:rag_dev_password@127.0.0.1:5433/rag_dev"

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- LLM (chat / JSON) ---
    llm_provider: str = "groq"  # groq | azure

    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_chat_model: str = "llama-3.3-70b-versatile"

    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str | None = "2024-02-01"
    azure_openai_deployment: str | None = None
    azure_openai_mini_deployment: str | None = None

    # --- Embeddings (Groq chat does not provide embeddings API) ---
    embed_dim: int = 1536
    embedding_provider: str = "openai"  # openai | azure | none
    openai_api_key: str | None = None
    openai_embeddings_model: str = "text-embedding-3-small"
    openai_embeddings_dimensions: int | None = 1536

    azure_embedding_deployment: str | None = None

    # Optional shared secret (env BACKEND_API_KEY); no SSO in Phase 1.
    backend_api_key: str | None = None

    # Writes from POST /notes/generate (explicit opt-in; keep false outside trusted demos).
    note_generation_enabled: bool = False

    # Groq-backed GET /patients/{id}/meeting-prep (cached in patient_meeting_prep).
    meeting_prep_enabled: bool = True


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def cors_origin_list(origins_csv: str) -> list[str]:
    return [o.strip() for o in origins_csv.split(",") if o.strip()]
