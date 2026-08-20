"""Application configuration.

Keep config small and explicit. Do not read environment variables directly in agents.
"""

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")

    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1", validation_alias="GROQ_BASE_URL"
    )
    groq_model: str = Field(default="openai/gpt-oss-20b", validation_alias="GROQ_MODEL")
    llm_max_retries: int = Field(default=2, ge=0, le=5, validation_alias="LLM_MAX_RETRIES")

    langsmith_api_key: str | None = Field(default=None, validation_alias="LANGSMITH_API_KEY")
    langsmith_tracing: bool = Field(default=False, validation_alias="LANGSMITH_TRACING")
    langsmith_project: str = Field(
        default="multi-agent-research-lab", validation_alias="LANGSMITH_PROJECT"
    )

    langfuse_public_key: str | None = Field(default=None, validation_alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str | None = Field(default=None, validation_alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com", validation_alias="LANGFUSE_HOST"
    )

    tavily_api_key: str | None = Field(default=None, validation_alias="TAVILY_API_KEY")

    max_iterations: int = Field(default=6, ge=1, le=20, validation_alias="MAX_ITERATIONS")
    timeout_seconds: int = Field(default=60, ge=5, le=600, validation_alias="TIMEOUT_SECONDS")

    @property
    def llm_api_key(self) -> str | None:
        """Prefer Groq when configured, while retaining OpenAI compatibility."""

        return self.groq_api_key or self.openai_api_key

    @property
    def llm_model(self) -> str:
        return self.groq_model if self.groq_api_key else self.openai_model

    @property
    def llm_base_url(self) -> str | None:
        return self.groq_base_url if self.groq_api_key else None

    @property
    def llm_provider(self) -> str:
        if self.groq_api_key:
            return "groq"
        if self.openai_api_key:
            return "openai"
        return "local"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
