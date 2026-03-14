from pathlib import Path

import dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_env_file = Path(__file__).parent.parent / ".env"
dotenv.load_dotenv(_env_file)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_file, extra="ignore")

    coordinator_model: str = "qwen/qwen3-next-80b-a3b-instruct"
    attractions_model: str = "qwen/qwen3-next-80b-a3b-instruct"
    flight_search_model: str = "qwen/qwen3-next-80b-a3b-instruct"
    nvidia_api_key: str = ""
    tavily_api_key: str = ""

settings = Settings()
