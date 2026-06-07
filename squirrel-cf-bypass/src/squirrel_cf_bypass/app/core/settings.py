from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    CF_BYPASS_HOST: str = "0.0.0.0"
    CF_BYPASS_PORT: int = 8002
    CF_BYPASS_LOG_LEVEL: str = "INFO"


settings = Settings()
