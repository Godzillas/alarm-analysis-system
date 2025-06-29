"""
告警抑制API路由
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.auth import get_current_user, get_current_admin_user
from src.models.alarm import User
from src.models.suppression import (
    AlarmSuppressionCreate, AlarmSuppressionUpdate, AlarmSuppressionResponse,
    MaintenanceWindowCreate, MaintenanceWindowResponse,
    DependencyMapCreate, DependencyMapResponse,
    SuppressionTestRequest, SuppressionTestResult
)
from src.services.suppression_service import suppression_service


router = APIRouter()


@router.post("/", response_model=AlarmSuppressionResponse)
async def create_suppression(
    suppression_data: AlarmSuppressionCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
):
    """创建告警抑制规则"""
    try:
        suppression = await suppression_service.create_suppression(
            db=db,
            suppression_data=suppression_data.dict(),
            creator_id=current_user.id
        )
        return AlarmSuppressionResponse.from_orm(suppression)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建抑制规则失败: {str(e)}"
        )


@router.get("/", response_model=List[AlarmSuppressionResponse])
async def list_suppressions(
    status: Optional[str] = Query(None, description="抑制状态"),
    suppression_type: Optional[str] = Query(None, description="抑制类型"),
    limit: int = Query(50, ge=1, le=1000, description="限制数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """获取抑制规则列表"""
    suppressions = await suppression_service.list_suppressions(
        db=db,
        status=status,
        suppression_type=suppression_type,
        limit=limit,
        offset=offset
    )
    return [AlarmSuppressionResponse.from_orm(s) for s in suppressions]


@router.get("/{suppression_id}", response_model=AlarmSuppressionResponse)
async def get_suppression(
    suppression_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """获取抑制规则详情"""
    suppression = await suppression_service.get_suppression(db, suppression_id)
    if not suppression:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="抑制规则不存在"
        )
    return AlarmSuppressionResponse.from_orm(suppression)


@router.put("/{suppression_id}", response_model=AlarmSuppressionResponse)
async def update_suppression(
    suppression_id: int,
    update_data: AlarmSuppressionUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
):
    """更新抑制规则"""
    suppression = await suppression_service.update_suppression(
        db=db,
        suppression_id=suppression_id,
        update_data=update_data.dict(exclude_unset=True)
    )
    if not suppression:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="抑制规则不存在"
        )
    return AlarmSuppressionResponse.from_orm(suppression)


@router.delete("/{suppression_id}")
async def delete_suppression(
    suppression_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
):
    """删除抑制规则"""
    success = await suppression_service.delete_suppression(db, suppression_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="抑制规则不存在"
        )
    return {"message": "抑制规则删除成功"}


@router.post("/test", response_model=SuppressionTestResult)
async def test_suppression_rule(
    test_request: SuppressionTestRequest,
    current_user: User = Depends(get_current_admin_user)
):
    """测试抑制规则"""
    try:
        result = await suppression_service.test_suppression_rule(
            suppression_config=test_request.suppression_config.dict(),
            test_alarms=test_request.test_alarms,
            test_time=test_request.test_time
        )
        return SuppressionTestResult(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试抑制规则失败: {str(e)}"
        )


@router.get("/templates")
async def get_suppression_templates(
    current_user: User = Depends(get_current_user)
):
    """获取抑制规则模板"""
    return suppression_service.get_suppression_templates()


# 维护窗口管理

@router.post("/maintenance-windows", response_model=MaintenanceWindowResponse)
async def create_maintenance_window(
    window_data: MaintenanceWindowCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
):
    """创建维护窗口"""
    try:
        window = await suppression_service.create_maintenance_window(
            db=db,
            window_data=window_data.dict(),
            creator_id=current_user.id
        )
        return MaintenanceWindowResponse.from_orm(window)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建维护窗口失败: {str(e)}"
        )


@router.get("/maintenance-windows", response_model=List[MaintenanceWindowResponse])
async def list_maintenance_windows(
    status: Optional[str] = Query(None, description="维护状态"),
    upcoming_hours: Optional[int] = Query(None, ge=1, le=168, description="即将到来的小时数"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """获取维护窗口列表"""
    windows = await suppression_service.get_maintenance_windows(
        db=db,
        status=status,
        upcoming_hours=upcoming_hours
    )
    return [MaintenanceWindowResponse.from_orm(w) for w in windows]


# 依赖关系管理

@router.post("/dependencies", response_model=DependencyMapResponse)
async def create_dependency_map(
    dependency_data: DependencyMapCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
):
    """创建依赖关系映射"""
    try:
        dependency = await suppression_service.create_dependency_map(
            db=db,
            dependency_data=dependency_data.dict(),
            creator_id=current_user.id
        )
        return DependencyMapResponse.from_orm(dependency)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建依赖关系失败: {str(e)}"
        )


# 抑制状态和统计

@router.get("/stats/summary")
async def get_suppression_stats(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """获取抑制统计摘要"""
    
    # 这里可以添加统计逻辑
    return {
        "period_days": days,
        "total_suppressions": 0,
        "active_suppressions": 0,
        "suppressed_alarms": 0,
        "suppression_rate": 0.0,
        "top_rules": []
    }


@router.post("/{suppression_id}/pause")
async def pause_suppression(
    suppression_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
):
    """暂停抑制规则"""
    suppression = await suppression_service.update_suppression(
        db=db,
        suppression_id=suppression_id,
        update_data={"status": "paused"}
    )
    if not suppression:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="抑制规则不存在"
        )
    return {"message": "抑制规则已暂停"}


@router.post("/{suppression_id}/resume")
async def resume_suppression(
    suppression_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
):
    """恢复抑制规则"""
    suppression = await suppression_service.update_suppression(
        db=db,
        suppression_id=suppression_id,
        update_data={"status": "active"}
    )
    if not suppression:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="抑制规则不存在"
        )
    return {"message": "抑制规则已恢复"}


@router.post("/reload-cache")
async def reload_suppression_cache(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
):
    """重新加载抑制规则缓存"""
    try:
        await suppression_service.load_active_suppressions(db)
        return {"message": "抑制规则缓存重新加载成功"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新加载缓存失败: {str(e)}"
        )


# 抑制规则条件验证

@router.post("/validate-conditions")
async def validate_suppression_conditions(
    conditions: Dict[str, Any],
    current_user: User = Depends(get_current_admin_user)
):
    """验证抑制条件"""
    try:
        await suppression_service._validate_suppression_conditions(conditions)
        return {"valid": True, "message": "抑制条件验证通过"}
    except ValueError as e:
        return {"valid": False, "message": str(e)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证抑制条件失败: {str(e)}"
        )


# 抑制日志查询

@router.get("/{suppression_id}/logs")
async def get_suppression_logs(
    suppression_id: int,
    limit: int = Query(50, ge=1, le=1000, description="限制数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """获取抑制规则执行日志"""
    
    # 这里可以添加具体的日志查询逻辑
    return {
        "suppression_id": suppression_id,
        "logs": [],
        "total": 0,
        "limit": limit,
        "offset": offset
    }


# 批量操作

@router.post("/batch-pause")
async def batch_pause_suppressions(
    suppression_ids: List[int],
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
):
    """批量暂停抑制规则"""
    results = {"success": [], "failed": []}
    
    for suppression_id in suppression_ids:
        try:
            suppression = await suppression_service.update_suppression(
                db=db,
                suppression_id=suppression_id,
                update_data={"status": "paused"}
            )
            if suppression:
                results["success"].append(suppression_id)
            else:
                results["failed"].append({"id": suppression_id, "reason": "不存在"})
        except Exception as e:
            results["failed"].append({"id": suppression_id, "reason": str(e)})
    
    return results


@router.post("/batch-resume")
async def batch_resume_suppressions(
    suppression_ids: List[int],
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
):
    """批量恢复抑制规则"""
    results = {"success": [], "failed": []}
    
    for suppression_id in suppression_ids:
        try:
            suppression = await suppression_service.update_suppression(
                db=db,
                suppression_id=suppression_id,
                update_data={"status": "active"}
            )
            if suppression:
                results["success"].append(suppression_id)
            else:
                results["failed"].append({"id": suppression_id, "reason": "不存在"})
        except Exception as e:
            results["failed"].append({"id": suppression_id, "reason": str(e)})
    
    return results