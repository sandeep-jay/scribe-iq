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

    # When true, emit JSON logs (recommended in production).
    log_json: bool = False

    database_url: str = "postgresql://rag:rag_dev_password@127.0.0.1:5433/rag_dev"

    # Asyncpg pool tuning (helps avoid queueing under concurrent slow LLM calls).
    db_pool_min_size: int = 2
    db_pool_max_size: int = 20
    db_pool_command_timeout_s: float = 30.0

    # Comma-separated exact origins. Next often uses 3001+ when 3000 is busy; LAN testing uses 192.168.x.x.
    cors_origins: str = ",".join(
        [f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in range(3000, 3013)]
        + [f"http://{host}:3020" for host in ("localhost", "127.0.0.1")]
        + [f"http://{host}:5173" for host in ("localhost", "127.0.0.1")]
    )

    # When true, also allow any localhost / 127.0.0.1 port and 192.168.* via regex (browser shows generic
    # "Failed to fetch" if Origin is not allowed). Set CORS_RELAX_LOCAL=false in locked-down deployments.
    cors_relax_local: bool = True

    # --- LLM (chat / JSON) ---
    llm_provider: str = "groq"  # groq | azure_openai | bedrock (azure alias supported)

    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_chat_model: str = "llama-3.3-70b-versatile"

    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str | None = "2024-10-21"
    azure_openai_chat_deployment: str | None = None
    azure_openai_json_deployment: str | None = None
    # Legacy aliases (AZURE_OPENAI_DEPLOYMENT / AZURE_OPENAI_MINI_DEPLOYMENT)
    azure_openai_deployment: str | None = None
    azure_openai_mini_deployment: str | None = None

    aws_region: str = "us-west-2"
    bedrock_chat_model_id: str | None = None
    bedrock_json_model_id: str | None = None
    bedrock_profile_name: str | None = None

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

    # GET /admin/responsible-ai/* when true (404 when false).
    responsible_ai_admin_enabled: bool = False


    def normalized_llm_provider(self) -> str:
        raw = (self.llm_provider or "groq").strip().lower()
        if raw in ("azure", "azure_openai"):
            return "azure_openai"
        if raw in ("groq", "azure_openai", "bedrock"):
            return raw
        return raw

    def resolved_azure_chat_deployment(self) -> str:
        for candidate in (
            self.azure_openai_chat_deployment,
            self.azure_openai_deployment,
            self.azure_openai_mini_deployment,
        ):
            if candidate and str(candidate).strip():
                return str(candidate).strip()
        return ""

    def resolved_azure_json_deployment(self) -> str:
        for candidate in (
            self.azure_openai_json_deployment,
            self.azure_openai_chat_deployment,
            self.azure_openai_deployment,
            self.azure_openai_mini_deployment,
        ):
            if candidate and str(candidate).strip():
                return str(candidate).strip()
        return ""

    def resolved_bedrock_chat_model_id(self) -> str:
        return (self.bedrock_chat_model_id or "").strip()

    def resolved_bedrock_json_model_id(self) -> str:
        return (self.bedrock_json_model_id or self.bedrock_chat_model_id or "").strip()

    def llm_configured(self) -> bool:
        provider = self.normalized_llm_provider()
        if provider == "groq":
            return bool((self.groq_api_key or "").strip() and (self.groq_chat_model or "").strip())
        if provider == "azure_openai":
            return bool(
                (self.azure_openai_endpoint or "").strip()
                and (self.azure_openai_api_key or "").strip()
                and self.resolved_azure_chat_deployment()
            )
        if provider == "bedrock":
            return bool((self.aws_region or "").strip() and self.resolved_bedrock_chat_model_id())
        return False

    def llm_json_mode_capability(self) -> str:
        provider = self.normalized_llm_provider()
        if provider in ("groq", "azure_openai"):
            return "native"
        if provider == "bedrock":
            return "prompt_enforced"
        return "unavailable"

    def embedding_configured(self) -> bool:
        ep = (self.embedding_provider or "none").strip().lower()
        if ep == "none":
            return False
        if ep == "openai":
            return bool((self.openai_api_key or "").strip())
        if ep == "azure":
            return bool(
                (self.azure_openai_endpoint or "").strip()
                and (self.azure_openai_api_key or "").strip()
                and (self.azure_embedding_deployment or "").strip()
            )
        return False


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def cors_origin_list(origins_csv: str) -> list[str]:
    return [o.strip() for o in origins_csv.split(",") if o.strip()]
