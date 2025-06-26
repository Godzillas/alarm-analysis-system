"""
应用中间件
"""

import logging
import time
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.exceptions import AlarmSystemException, to_http_exception
from src.core.responses import error_response
from src.core.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """全局错误处理中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except AlarmSystemException as exc:
            logger.error(f"Business exception: {exc.message}", extra={
                "code": exc.code,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method
            })
            http_exc = to_http_exception(exc)
            return JSONResponse(
                status_code=http_exc.status_code,
                content=error_response(
                    message=exc.message,
                    code=exc.code,
                    details=exc.details
                ).dict()
            )
        except Exception as exc:
            logger.exception(f"Unexpected error: {str(exc)}", extra={
                "path": request.url.path,
                "method": request.method
            })
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message="内部服务器错误",
                    code="INTERNAL_ERROR",
                    details={"error": str(exc)}
                ).dict()
            )


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # 记录请求开始
        logger.info(f"Request started", extra={
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent")
        })
        
        try:
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录请求完成
            logger.info(f"Request completed", extra={
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time": f"{process_time:.3f}s"
            })
            
            # 添加处理时间到响应头
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as exc:
            # 计算处理时间（即使出错）
            process_time = time.time() - start_time
            
            logger.error(f"Request failed", extra={
                "method": request.method,
                "url": str(request.url),
                "process_time": f"{process_time:.3f}s",
                "error": str(exc)
            })
            
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 对于API响应，添加CORS头
        if request.url.path.startswith("/api/"):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        
        return response