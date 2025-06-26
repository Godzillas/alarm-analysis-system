"""
数据生命周期管理API
"""

from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.auth import get_current_user
from src.core.exceptions import DatabaseException, ConfigurationException
from src.services.data_lifecycle_service import DataLifecycleService
from src.models.alarm import User

router = APIRouter(prefix="/api/v1/data-lifecycle", tags=["data-lifecycle"])


class ArchiveRequest(BaseModel):
    """归档请求模型"""
    archive_before_days: int = Field(default=90, ge=1, le=3650, description="归档多少天前的数据")
    batch_size: int = Field(default=1000, ge=100, le=10000, description="批处理大小")


class CleanupRequest(BaseModel):
    """清理请求模型"""
    cleanup_before_days: int = Field(default=365, ge=30, le=3650, description="清理多少天前的数据")
    batch_size: int = Field(default=1000, ge=100, le=10000, description="批处理大小")
    dry_run: bool = Field(default=True, description="是否为演练模式")


class BackupRequest(BaseModel):
    """备份请求模型"""
    backup_path: Optional[str] = Field(default=None, description="备份文件路径")


@router.post("/archive", response_model=Dict[str, int])
async def archive_old_data(
    request: ArchiveRequest,
    current_user: User = Depends(get_current_user)
):
    """归档旧数据"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only administrators can archive data")
    
    service = DataLifecycleService()
    
    try:
        result = await service.archive_old_data(
            archive_before_days=request.archive_before_days,
            batch_size=request.batch_size
        )
        return result
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup", response_model=Dict[str, int])
async def cleanup_old_data(
    request: CleanupRequest,
    current_user: User = Depends(get_current_user)
):
    """清理旧数据"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only administrators can cleanup data")
    
    service = DataLifecycleService()
    
    try:
        result = await service.cleanup_old_data(
            cleanup_before_days=request.cleanup_before_days,
            batch_size=request.batch_size,
            dry_run=request.dry_run
        )
        return result
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize", response_model=Dict[str, Any])
async def optimize_database(
    current_user: User = Depends(get_current_user)
):
    """优化数据库"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only administrators can optimize database")
    
    service = DataLifecycleService()
    
    try:
        result = await service.optimize_database()
        return result
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=Dict[str, Any])
async def get_data_statistics(
    current_user: User = Depends(get_current_user)
):
    """获取数据统计信息"""
    service = DataLifecycleService()
    
    try:
        result = await service.get_data_statistics()
        return result
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup", response_model=Dict[str, str])
async def create_backup(
    request: BackupRequest,
    current_user: User = Depends(get_current_user)
):
    """创建数据备份"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only administrators can create backups")
    
    service = DataLifecycleService()
    
    try:
        backup_file = await service.create_backup(backup_path=request.backup_path)
        return {
            "backup_file": backup_file,
            "created_at": datetime.utcnow().isoformat(),
            "status": "success"
        }
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_lifecycle_health():
    """获取数据生命周期服务健康状态"""
    service = DataLifecycleService()
    
    try:
        stats = await service.get_data_statistics()
        
        # 简单的健康检查逻辑
        total_alarms = stats.get('alarms', {}).get('total', 0)
        db_info = stats.get('database', {})
        
        health_status = {
            "status": "healthy",
            "total_alarms": total_alarms,
            "database_info": db_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 如果数据量过大，提示需要清理
        if total_alarms > 100000:
            health_status["warnings"] = ["Large number of alarms detected, consider archiving old data"]
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }