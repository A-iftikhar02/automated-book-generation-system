from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = Path(__file__).resolve().parent / "assets"


class Settings(BaseSettings):
    """All runtime configuration. Values come from the environment or the project-root .env file."""

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "BookPilot"
    VERSION: str = "2.0.0"

    # Database (Docker Postgres)
    DATABASE_URL: str = "postgresql+psycopg://bookpilot:bookpilot@localhost:5442/bookpilot"

    # AI providers. Any provider with a key can be used; leave the others empty.
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    CEREBRAS_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    # Local models via Ollama (https://ollama.com). No key; enable it and use "ollama:<model>" in a chain.
    OLLAMA_ENABLED: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_NUM_CTX: int = 32768  # context window requested per call; Ollama's default is far too small for books
    OLLAMA_TIMEOUT_SECONDS: int = 14400  # CPU-only machines can take over an hour per chapter segment with large models
    OLLAMA_THINK: bool = False  # "thinking" mode for models that support it; slower and rarely better for prose

    # Models as comma-separated fallback chains of "provider:model" (no prefix = OpenRouter).
    # The first model that answers wins; on rate limits/quota/outages the next one is tried.
    WRITER_MODELS: str = Field(
        default="anthropic/claude-sonnet-5.5",
        validation_alias=AliasChoices("WRITER_MODELS", "OPENROUTER_WRITER_MODEL"),
    )
    EDITOR_MODELS: str = Field(
        default="anthropic/claude-haiku-5.5",
        validation_alias=AliasChoices("EDITOR_MODELS", "OPENROUTER_EDITOR_MODEL"),
    )
    IMAGE_MODEL: str = Field(
        default="google/gemini-3.1-flash-image",
        validation_alias=AliasChoices("IMAGE_MODEL", "OPENROUTER_IMAGE_MODEL"),
    )
    LLM_TIMEOUT_SECONDS: int = Field(default=600, validation_alias=AliasChoices("LLM_TIMEOUT_SECONDS", "OPENROUTER_TIMEOUT_SECONDS"))
    APP_URL: str = "http://localhost:3000"

    # Quality assurance
    LANGUAGETOOL_URL: str = "http://localhost:8010"
    EPUBCHECK_JAR: str = ""  # optional path to epubcheck.jar; enables EPUB validation

    # Optional Slack notifications (disabled unless explicitly enabled AND a webhook is set)
    SLACK_ENABLED: bool = False
    SLACK_WEBHOOK_URL: str = ""

    # Storage & workers
    STORAGE_DIR: Path = BASE_DIR / "storage"
    RUN_WORKER_IN_PROCESS: bool = False
    WORKER_CONCURRENCY: int = 2
    WORKER_POLL_SECONDS: float = 2.0

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"]

    @property
    def openrouter_configured(self) -> bool:
        return bool(self.OPENROUTER_API_KEY.strip())

    def provider_key(self, provider: str) -> str:
        if provider == "ollama":
            return "ollama" if self.OLLAMA_ENABLED else ""
        return (getattr(self, f"{provider.upper()}_API_KEY", "") or "").strip()

    @property
    def llm_configured(self) -> bool:
        """True when at least one model in the writer and editor chains has a configured provider."""
        from .services.llm import chain_available  # local import: llm imports settings

        return chain_available(self.WRITER_MODELS) and chain_available(self.EDITOR_MODELS)

    @property
    def slack_active(self) -> bool:
        return self.SLACK_ENABLED and bool(self.SLACK_WEBHOOK_URL.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
