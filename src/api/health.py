"""
健康检查API
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from src.core.config import settings
from src.core.database import get_db_session
from src.core.responses import HealthResponse, data_response
from src.core.exceptions import ServiceUnavailableException

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db_session)):
    """系统健康检查"""
    
    services_status = {}
    overall_status = "healthy"
    
    # 检查数据库连接
    try:
        await db.execute(text("SELECT 1"))
        services_status["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        services_status["database"] = {
            "status": "unhealthy", 
            "message": f"Database error: {str(e)}"
        }
        overall_status = "unhealthy"
    
    # 检查Redis连接
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.close()
        services_status["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        services_status["redis"] = {
            "status": "unhealthy",
            "message": f"Redis error: {str(e)}"
        }
        overall_status = "degraded"
    
    # 检查配置
    config_issues = []
    if not settings.SECRET_KEY or settings.SECRET_KEY == "alarm-system-secret-key-2024-change-in-production":
        config_issues.append("SECRET_KEY should be changed in production")
    
    if config_issues:
        services_status["configuration"] = {
            "status": "warning",
            "message": "Configuration issues detected",
            "issues": config_issues
        }
        if overall_status == "healthy":
            overall_status = "degraded"
    else:
        services_status["configuration"] = {
            "status": "healthy",
            "message": "Configuration validated"
        }
    
    return HealthResponse(
        status=overall_status,
        version=settings.VERSION,
        timestamp=datetime.utcnow().isoformat(),
        services=services_status
    )


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db_session)):
    """就绪检查 - 检查所有依赖服务是否可用"""
    
    try:
        # 检查数据库
        await db.execute(text("SELECT 1"))
        
        # 检查Redis
        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.close()
        
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        raise ServiceUnavailableException("System not ready", {"error": str(e)})


@router.get("/health/live")
async def liveness_check():
    """存活检查 - 简单的应用程序存活检查"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION
    }