from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env", extra="ignore"
    )

    coordinator_model: str = "qwen/qwen3-next-80b-a3b-instruct"
    nvidia_api_key: str = ""
    tavily_api_key: str = ""


settings = Settings()
