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
    ENVIRONMENT: str = "development"
    
    # 数据库配置
    DATABASE_URL: str = "mysql+aiomysql://root:@localhost:3306/alarm_system"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10
    REDIS_TIMEOUT: int = 5
    
    # 告警收集配置
    COLLECTOR_ENABLED: bool = True
    COLLECTOR_BATCH_SIZE: int = 100
    COLLECTOR_FLUSH_INTERVAL: int = 10
    COLLECTOR_MAX_QUEUE_SIZE: int = 10000
    COLLECTOR_WORKER_COUNT: int = 4
    
    # 告警分析配置
    ANALYZER_ENABLED: bool = True
    DUPLICATE_THRESHOLD: float = 0.8
    CORRELATION_WINDOW: int = 300
    ANALYSIS_BATCH_SIZE: int = 50
    ANALYSIS_INTERVAL: int = 30
    
    # 通知配置
    NOTIFICATION_ENABLED: bool = True
    EMAIL_ENABLED: bool = False
    WEBHOOK_ENABLED: bool = False
    NOTIFICATION_RETRY_COUNT: int = 3
    NOTIFICATION_RETRY_INTERVAL: int = 300
    NOTIFICATION_TIMEOUT: int = 30
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "alarm-system-secret-key-2024-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    PASSWORD_MIN_LENGTH: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION: int = 900
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/alarm_system.log"
    LOG_MAX_SIZE: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    # 性能配置
    CACHE_TTL: int = 300
    API_RATE_LIMIT: int = 1000
    WEBSOCKET_MAX_CONNECTIONS: int = 100
    BACKGROUND_TASK_INTERVAL: int = 60
    
    # 存储配置
    STATIC_FILES_PATH: str = "static"
    UPLOAD_MAX_SIZE: int = 5242880  # 5MB
    ALLOWED_FILE_TYPES: str = "jpg,jpeg,png,gif,pdf,txt,csv,json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()