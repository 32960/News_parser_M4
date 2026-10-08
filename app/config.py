from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    celery_broker_url: str
    celery_result_backend: str

    # Path/name of Telethon session file (without forcing .session in code)
    # Accepts TELEGRAM_SESSION_PATH or older TELEGRAM_SESSION_NAME
    telegram_session_path: str = Field(
        validation_alias=AliasChoices(
            "TELEGRAM_SESSION_PATH",
            "TELEGRAM_SESSION_NAME",
            "telegram_session_path",
            "telegram_session_name",
        )
    )
    telegram_api_id: int
    telegram_api_hash: str
    # Target channel for publishing (@name or numeric id)
    telegram_target_channel: str = Field(
        validation_alias=AliasChoices(
            "TELEGRAM_TARGET_CHANNEL",
            "TELEGRAM_CHANNEL",
            "telegram_target_channel",
            "telegram_channel",
        )
    )

    openai_api_key: SecretStr
    openai_model: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
