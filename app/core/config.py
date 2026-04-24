from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "TCF Oral Practice Tool"
    debug: bool = False
    secret_key: str = "CHANGE-ME"

    # Database
    database_url: str = "postgresql+asyncpg://tcf_user:tcf_pass@localhost:5432/tcf_oral"

    # Deepgram
    deepgram_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # S3
    s3_endpoint: str = ""
    s3_bucket: str = "tcf-audio"
    s3_access_key: str = ""
    s3_secret_key: str = ""

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24h

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
