"""
系统配置
"""

import os
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    # 基础配置
    APP_NAME: str = "告警分析系统"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./alarm_system.db"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # 告警收集配置
    COLLECTOR_ENABLED: bool = True
    COLLECTOR_BATCH_SIZE: int = 100
    COLLECTOR_FLUSH_INTERVAL: int = 10
    
    # 告警分析配置
    ANALYZER_ENABLED: bool = True
    DUPLICATE_THRESHOLD: float = 0.8
    CORRELATION_WINDOW: int = 300
    
    # 通知配置
    NOTIFICATION_ENABLED: bool = True
    EMAIL_ENABLED: bool = False
    WEBHOOK_ENABLED: bool = False
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()