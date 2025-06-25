"""
错误处理工具
"""

import asyncio
import logging
import traceback
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AlarmSystemError(Exception):
    """告警系统基础异常"""
    
    def __init__(self, message: str, error_code: str = "ALARM_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(AlarmSystemError):
    """数据库错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATABASE_ERROR", details)


class ValidationError(AlarmSystemError):
    """验证错误"""
    
    def __init__(self, message: str, field: str = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", error_details)


class AuthenticationError(AlarmSystemError):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTH_ERROR", details)


class AuthorizationError(AlarmSystemError):
    """授权错误"""
    
    def __init__(self, message: str = "权限不足", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHZ_ERROR", details)


class ConfigurationError(AlarmSystemError):
    """配置错误"""
    
    def __init__(self, message: str, config_key: str = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
        super().__init__(message, "CONFIG_ERROR", error_details)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器"""
    logger = logging.getLogger(__name__)
    
    if isinstance(exc, AlarmSystemError):
        # 自定义业务异常
        logger.warning(f"业务异常: {exc.error_code} - {exc.message}")
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        )
    
    elif isinstance(exc, HTTPException):
        # FastAPI HTTP异常
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP_ERROR",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    else:
        # 未预期的系统异常
        logger.error(f"系统异常: {str(exc)}")
        logger.error(traceback.format_exc())
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "内部服务器错误",
                "details": {"trace_id": id(exc)}
            }
        )


def handle_database_error(func):
    """数据库错误装饰器"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger(func.__module__)
            logger.error(f"数据库操作失败 {func.__name__}: {str(e)}")
            
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                raise ValidationError("数据已存在，请检查唯一性约束")
            elif "foreign key" in str(e).lower():
                raise ValidationError("关联数据不存在，请检查外键约束")
            elif "connection" in str(e).lower():
                raise DatabaseError("数据库连接失败")
            else:
                raise DatabaseError(f"数据库操作失败: {str(e)}")
    
    return wrapper


def safe_execute(default_value=None, log_error=True):
    """安全执行装饰器，捕获异常并返回默认值"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger = logging.getLogger(func.__module__)
                    logger.error(f"函数执行失败 {func.__name__}: {str(e)}")
                return default_value
        
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger = logging.getLogger(func.__module__)
                    logger.error(f"函数执行失败 {func.__name__}: {str(e)}")
                return default_value
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator