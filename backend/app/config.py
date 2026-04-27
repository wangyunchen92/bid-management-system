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
    AI_MODEL: str = "doubao-seed-1-8-251228"
    AI_VISION_MODEL: str = "doubao-seed-1-8-251228"  # 视觉模型，用于扫描件/图片识别

    # 企业信息配置
    COMPANY_NAME: str = "合肥新安彩印包装有限公司"
    COMPANY_ADDRESS: str = "合肥市长江西路蜀鑫大道12号"
    COMPANY_PHONE: str = "0551-65329905"
    COMPANY_FAX: str = "0551-65316566"
    COMPANY_ZIPCODE: str = "230031"
    COMPANY_LEGAL_PERSON: str = "吴晓东"
    COMPANY_CREDIT_CODE: str = "913401007349718851M"
    COMPANY_BANK: str = "工行开发区支行"
    COMPANY_BANK_ACCOUNT: str = "1302011909024926532"

    # 企业详情（用于法定代表人身份证明书等模板）
    COMPANY_TYPE: str = "有限责任公司（自然人投资或控股）"
    COMPANY_FOUNDED: str = "2002年02月06日"
    COMPANY_BUSINESS_TERM: str = "2002年02月06日至2032年02月05日"

    # 法定代表人详情
    LEGAL_PERSON_GENDER: str = "男"
    LEGAL_PERSON_AGE: str = "57"
    LEGAL_PERSON_TITLE: str = "执行董事兼总经理"

    # 授权代表（默认与法人同人，电话独立维护）
    AUTHORIZED_REP_NAME: str = "吴晓东"
    AUTHORIZED_REP_PHONE: str = "13075550821"

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
