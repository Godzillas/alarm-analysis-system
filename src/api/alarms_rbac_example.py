"""
带RBAC权限控制的告警管理API示例
演示如何在现有API中集成权限控制
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.auth import get_current_user
from src.core.rbac import require_permission, require_any_permission, data_filter
from src.models.alarm import (
    AlarmTable, AlarmCreate, AlarmUpdate, AlarmResponse, 
    AlarmStatus, AlarmSeverity, User, PaginatedResponse
)
from src.services.collector import AlarmCollector

router = APIRouter(prefix="/api/v1/alarms-rbac", tags=["alarms-rbac"])


@router.post("/", response_model=AlarmResponse)
@require_permission("alarms.create")
async def create_alarm(
    alarm: AlarmCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """创建新告警 - 需要 alarms.create 权限"""
    try:
        collector = AlarmCollector()
        await collector.collect_alarm_dict(alarm.dict())
        
        new_alarm = AlarmTable(**alarm.dict())
        db.add(new_alarm)
        await db.commit()
        await db.refresh(new_alarm)
        
        return new_alarm
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建告警失败: {str(e)}")


@router.get("/", response_model=PaginatedResponse[AlarmResponse])
@require_permission("alarms.read")
async def get_alarms(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    status: Optional[AlarmStatus] = None,
    severity: Optional[AlarmSeverity] = None,
    source: Optional[str] = None,
    host: Optional[str] = None,
    service: Optional[str] = None,
    environment: Optional[str] = None,
    system_id: Optional[int] = Query(None, description="系统 ID 过滤"),
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000)
):
    """获取告警列表 - 需要 alarms.read 权限，自动应用数据权限过滤"""
    
    # 构建基础查询
    base_query = select(AlarmTable)
    count_query = select(func.count(AlarmTable.id))
    
    filters = []
    if status:
        filters.append(AlarmTable.status == status)
    if severity:
        filters.append(AlarmTable.severity == severity)
    if source:
        filters.append(AlarmTable.source.ilike(f"%{source}%"))
    if host:
        filters.append(AlarmTable.host.ilike(f"%{host}%"))
    if service:
        filters.append(AlarmTable.service.ilike(f"%{service}%"))
    if environment:
        filters.append(AlarmTable.environment.ilike(f"%{environment}%"))
    if system_id:
        filters.append(AlarmTable.system_id == system_id)
    if search:
        search_filter = or_(
            AlarmTable.title.ilike(f"%{search}%"),
            AlarmTable.description.ilike(f"%{search}%")
        )
        filters.append(search_filter)
    
    # 应用数据权限过滤 - 非管理员用户只能看到有权限的系统的告警
    if not current_user.is_admin:
        from src.core.rbac import get_user_accessible_systems
        accessible_systems = await get_user_accessible_systems(current_user)
        
        if accessible_systems:  # 如果有系统限制
            filters.append(AlarmTable.system_id.in_(accessible_systems))
        else:
            # 如果没有配置系统权限，可能需要其他过滤逻辑
            # 这里可以根据业务需求决定是返回空结果还是应用其他过滤
            pass
    
    if filters:
        base_query = base_query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 获取分页数据
    data_query = base_query.order_by(desc(AlarmTable.created_at)).offset(skip).limit(limit)
    result = await db.execute(data_query)
    alarms = result.scalars().all()
    
    # 应用数据权限过滤 (转换为字典格式进行过滤)
    alarm_dicts = [
        {
            "id": alarm.id,
            "title": alarm.title,
            "description": alarm.description,
            "severity": alarm.severity,
            "status": alarm.status,
            "source": alarm.source,
            "system_id": alarm.system_id,
            "created_at": alarm.created_at,
            # 添加其他需要的字段
        }
        for alarm in alarms
    ]
    
    filtered_alarms = await data_filter.filter_alarms(current_user, alarm_dicts)
    
    # 计算分页信息
    page = (skip // limit) + 1
    pages = (total + limit - 1) // limit
    
    return PaginatedResponse[AlarmResponse](
        data=filtered_alarms,
        total=len(filtered_alarms),
        page=page,
        page_size=limit,
        pages=pages
    )


@router.get("/{alarm_id}", response_model=AlarmResponse)
@require_permission("alarms.read")
async def get_alarm(
    alarm_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """获取单个告警详情 - 需要 alarms.read 权限"""
    result = await db.execute(select(AlarmTable).where(AlarmTable.id == alarm_id))
    alarm = result.scalar_one_or_none()
    
    if not alarm:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    # 检查数据权限
    can_access = await data_filter.can_access_resource(
        current_user, "alarms", alarm_id
    )
    
    if not can_access:
        raise HTTPException(status_code=403, detail="无权访问此告警")
    
    return alarm


@router.put("/{alarm_id}", response_model=AlarmResponse)
@require_permission("alarms.update")
async def update_alarm(
    alarm_id: int,
    alarm_update: AlarmUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """更新告警 - 需要 alarms.update 权限"""
    result = await db.execute(select(AlarmTable).where(AlarmTable.id == alarm_id))
    alarm = result.scalar_one_or_none()
    
    if not alarm:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    # 检查数据权限
    can_access = await data_filter.can_access_resource(
        current_user, "alarms", alarm_id
    )
    
    if not can_access:
        raise HTTPException(status_code=403, detail="无权修改此告警")
    
    # 更新字段
    update_data = alarm_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alarm, field, value)
    
    alarm.updated_at = datetime.utcnow()
    
    try:
        await db.commit()
        await db.refresh(alarm)
        return alarm
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新告警失败: {str(e)}")


@router.delete("/{alarm_id}")
@require_permission("alarms.delete")
async def delete_alarm(
    alarm_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """删除告警 - 需要 alarms.delete 权限"""
    result = await db.execute(select(AlarmTable).where(AlarmTable.id == alarm_id))
    alarm = result.scalar_one_or_none()
    
    if not alarm:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    # 检查数据权限
    can_access = await data_filter.can_access_resource(
        current_user, "alarms", alarm_id
    )
    
    if not can_access:
        raise HTTPException(status_code=403, detail="无权删除此告警")
    
    try:
        await db.delete(alarm)
        await db.commit()
        return {"message": "告警删除成功"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除告警失败: {str(e)}")


@router.post("/{alarm_id}/acknowledge")
@require_any_permission(["alarms.acknowledge", "alarms.update"])
async def acknowledge_alarm(
    alarm_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """确认告警 - 需要 alarms.acknowledge 或 alarms.update 权限"""
    result = await db.execute(select(AlarmTable).where(AlarmTable.id == alarm_id))
    alarm = result.scalar_one_or_none()
    
    if not alarm:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    # 检查数据权限
    can_access = await data_filter.can_access_resource(
        current_user, "alarms", alarm_id
    )
    
    if not can_access:
        raise HTTPException(status_code=403, detail="无权确认此告警")
    
    if alarm.status == AlarmStatus.ACKNOWLEDGED:
        raise HTTPException(status_code=400, detail="告警已经被确认")
    
    try:
        alarm.status = AlarmStatus.ACKNOWLEDGED
        alarm.acknowledged_at = datetime.utcnow()
        alarm.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(alarm)
        
        return {
            "message": "告警确认成功",
            "alarm_id": alarm_id,
            "acknowledged_at": alarm.acknowledged_at,
            "acknowledged_by": current_user.username
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"确认告警失败: {str(e)}")


@router.post("/{alarm_id}/resolve")
@require_any_permission(["alarms.resolve", "alarms.update"])
async def resolve_alarm(
    alarm_id: int,
    resolution_note: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """解决告警 - 需要 alarms.resolve 或 alarms.update 权限"""
    result = await db.execute(select(AlarmTable).where(AlarmTable.id == alarm_id))
    alarm = result.scalar_one_or_none()
    
    if not alarm:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    # 检查数据权限
    can_access = await data_filter.can_access_resource(
        current_user, "alarms", alarm_id
    )
    
    if not can_access:
        raise HTTPException(status_code=403, detail="无权解决此告警")
    
    if alarm.status == AlarmStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="告警已经被解决")
    
    try:
        alarm.status = AlarmStatus.RESOLVED
        alarm.resolved_at = datetime.utcnow()
        alarm.updated_at = datetime.utcnow()
        
        # 如果有解决备注，可以存储到metadata中
        if resolution_note:
            metadata = alarm.alarm_metadata or {}
            metadata["resolution_note"] = resolution_note
            metadata["resolved_by"] = current_user.username
            alarm.alarm_metadata = metadata
        
        await db.commit()
        await db.refresh(alarm)
        
        return {
            "message": "告警解决成功",
            "alarm_id": alarm_id,
            "resolved_at": alarm.resolved_at,
            "resolved_by": current_user.username,
            "resolution_note": resolution_note
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"解决告警失败: {str(e)}")


@router.get("/stats/summary")
@require_permission("analytics.read")
async def get_alarm_stats(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    system_id: Optional[int] = Query(None, description="系统ID过滤")
):
    """获取告警统计 - 需要 analytics.read 权限"""
    
    # 构建查询条件
    filters = []
    
    # 应用数据权限过滤
    if not current_user.is_admin:
        from src.core.rbac import get_user_accessible_systems
        accessible_systems = await get_user_accessible_systems(current_user)
        
        if accessible_systems:
            filters.append(AlarmTable.system_id.in_(accessible_systems))
    
    if system_id:
        filters.append(AlarmTable.system_id == system_id)
    
    base_filter = and_(*filters) if filters else True
    
    try:
        # 按状态统计
        status_stats = await db.execute(
            select(
                AlarmTable.status,
                func.count(AlarmTable.id).label('count')
            )
            .where(base_filter)
            .group_by(AlarmTable.status)
        )
        
        # 按严重程度统计
        severity_stats = await db.execute(
            select(
                AlarmTable.severity,
                func.count(AlarmTable.id).label('count')
            )
            .where(base_filter)
            .group_by(AlarmTable.severity)
        )
        
        # 总计统计
        total_count = await db.execute(
            select(func.count(AlarmTable.id)).where(base_filter)
        )
        
        return {
            "total_alarms": total_count.scalar(),
            "by_status": {row.status: row.count for row in status_stats},
            "by_severity": {row.severity: row.count for row in severity_stats},
            "accessible_systems": not current_user.is_admin,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


# 权限演示端点
@router.get("/permissions/demo")
async def permission_demo(current_user: User = Depends(get_current_user)):
    """演示不同权限级别的访问"""
    from src.services.rbac_service import RBACService
    
    rbac_service = RBACService()
    
    # 检查用户的各种权限
    permissions_to_check = [
        "alarms.read",
        "alarms.create", 
        "alarms.update",
        "alarms.delete",
        "alarms.acknowledge",
        "alarms.resolve",
        "analytics.read",
        "analytics.export",
        "users.read",
        "config.update",
        "system.manage"
    ]
    
    user_permissions = {}
    for perm in permissions_to_check:
        has_perm = await rbac_service.check_permission(
            current_user.id, perm, log_access=False
        )
        user_permissions[perm] = has_perm
    
    # 获取用户角色
    user_roles = []
    if hasattr(current_user, 'roles') and current_user.roles:
        user_roles = [
            {
                "name": role.name,
                "display_name": role.display_name,
                "level": role.level
            }
            for role in current_user.roles
        ]
    
    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "is_admin": current_user.is_admin
        },
        "roles": user_roles,
        "permissions": user_permissions,
        "permission_summary": {
            "can_read_alarms": user_permissions.get("alarms.read", False),
            "can_modify_alarms": any([
                user_permissions.get("alarms.update", False),
                user_permissions.get("alarms.delete", False)
            ]),
            "can_manage_system": user_permissions.get("system.manage", False),
            "total_permissions": sum(user_permissions.values())
        }
    }