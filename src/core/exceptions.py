"""
统一异常处理
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class AlarmSystemException(Exception):
    """告警系统基础异常"""
    
    def __init__(self, message: str, code: str = "ALARM_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseException(AlarmSystemException):
    """数据库异常"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATABASE_ERROR", details)


class ValidationException(AlarmSystemException):
    """数据验证异常"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", details)


class AuthenticationException(AlarmSystemException):
    """认证异常"""
    
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTH_ERROR", details)


class AuthorizationException(AlarmSystemException):
    """授权异常"""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHORIZATION_ERROR", details)


class ResourceNotFoundException(AlarmSystemException):
    """资源未找到异常"""
    
    def __init__(self, resource: str, identifier: Any, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} not found: {identifier}"
        details = details or {}
        details.update({"resource": resource, "identifier": identifier})
        super().__init__(message, "RESOURCE_NOT_FOUND", details)


class ConfigurationException(AlarmSystemException):
    """配置异常"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIG_ERROR", details)


class ServiceUnavailableException(AlarmSystemException):
    """服务不可用异常"""
    
    def __init__(self, service: str, details: Optional[Dict[str, Any]] = None):
        message = f"Service unavailable: {service}"
        details = details or {}
        details["service"] = service
        super().__init__(message, "SERVICE_UNAVAILABLE", details)


# HTTP异常转换函数
def to_http_exception(exc: AlarmSystemException) -> HTTPException:
    """将自定义异常转换为HTTP异常"""
    
    status_mapping = {
        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "AUTH_ERROR": status.HTTP_401_UNAUTHORIZED,
        "AUTHORIZATION_ERROR": status.HTTP_403_FORBIDDEN,
        "RESOURCE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "CONFIG_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "SERVICE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
        "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    status_code = status_mapping.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    detail = {
        "message": exc.message,
        "code": exc.code,
        "details": exc.details
    }
    
    return HTTPException(status_code=status_code, detail=detail)