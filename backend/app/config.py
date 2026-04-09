"""
配置管理模块
"""

import json
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # 应用配置
    APP_NAME: str = "bid-system"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8002

    # 数据库配置
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "root123456"
    DB_NAME: str = "bid_system"
    DB_TYPE: str = "sqlite"

    # JWT 配置
    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS 配置
    CORS_ORIGINS: str = '["http://localhost:5180"]'

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    # AI 配置（火山引擎/豆包）
    AI_API_KEY: str = "46813e98-c5d7-4979-9875-81d6aa3b4243"
    AI_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    AI_MODEL: str = "doubao-seed-1-6-251015"

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE == "sqlite":
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bid.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            return f"sqlite+aiosqlite:///{db_path}"
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        if self.DB_TYPE == "sqlite":
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bid.db")
            return f"sqlite:///{db_path}"
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:5180"]


settings = Settings()
