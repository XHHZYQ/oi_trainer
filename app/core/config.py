"""应用配置：pydantic-settings，必填项不给默认值（fail-fast）。"""
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# 按 APP_ENV 切换 env 文件：local -> .env.local
_env_file = f".env.{os.getenv('APP_ENV', 'local')}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_file, env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    database_url: str  # 必填，形如 postgresql+asyncpg://user:pass@host:5432/oi_trainer
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str  # 必填
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440


settings = Settings()
