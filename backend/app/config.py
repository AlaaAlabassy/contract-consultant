from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Google Drive (backend ingestion - service account, no browser/OAuth needed).
    # The user must share the Drive folders with this service account's email.
    # Either the raw JSON content (e.g. from a Codespaces secret) or a file
    # path works - the JSON content takes precedence if both are set.
    google_service_account_json: str = ""
    google_service_account_file: str = "secrets/service-account.json"
    google_drive_root_folder_id: str = ""
    google_archiving_matrix_file_id: str = ""

    # Google OAuth (only needed later if/when an interactive frontend login is added)
    google_client_id: str = ""
    google_client_secret: str = ""

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "anthropic/claude-3.5-sonnet"

    # Embeddings
    embedding_model: str = "intfloat/multilingual-e5-small"

    # Storage
    database_url: str = "postgresql://postgres:postgres@postgres:5432/contracts"
    chroma_host: str = "chromadb"
    chroma_port: int = 8000
    redis_url: str = "redis://redis:6379/0"

    # Citation-lock confidence thresholds
    confidence_high: float = 0.90
    confidence_warn: float = 0.70
    confidence_refuse: float = 0.50


settings = Settings()
