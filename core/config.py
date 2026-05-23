from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    github_token: str = ""
    wandb_api_key: str = ""

    max_iterations: int = 3
    claude_auditor_model: str = "claude-sonnet-4-6"
    claude_quality_model: str = "claude-sonnet-4-6"
    claude_publisher_model: str = "claude-haiku-4-5"
    thinking_budget_tokens: int = 8000
    thinking_enabled: bool = True
    sandbox_mem_limit: str = "512m"
    log_level: str = "INFO"


settings = Settings()
