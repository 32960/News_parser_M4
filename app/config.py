from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    database_url: str
    celery_broker_url: str
    celery_result_backend: str

    telegram_session_name: str
    telegram_api_id: str
    telegram_api_hash: str
    telegram_channel: str

    openai_api_key: SecretStr
    openai_model: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings():
    return Settings()
