"""
值班管理API路由
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.core.database import get_db_session
from src.api.auth import get_current_user
from src.models.alarm import User
from src.models.oncall import (
    OnCallTeam, OnCallMember, OnCallSchedule, OnCallShift, 
    EscalationPolicy, OnCallOverride,
    OnCallTeamCreate, OnCallTeamUpdate, OnCallTeamResponse,
    OnCallMemberCreate, OnCallMemberResponse,
    OnCallScheduleCreate, OnCallScheduleResponse,
    OnCallShiftResponse,
    EscalationPolicyCreate, EscalationPolicyResponse,
    OnCallOverrideCreate, OnCallOverrideResponse
)
from src.services.oncall_manager import oncall_manager
from src.services.escalation_engine import escalation_engine
from src.utils.logger import get_logger

router = APIRouter(prefix="/api/oncall", tags=["值班管理"])
logger = get_logger(__name__)


@router.post("/teams", response_model=OnCallTeamResponse)
async def create_team(
    team_data: OnCallTeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """创建值班团队"""
    try:
        team = await oncall_manager.create_team(team_data.dict())
        return OnCallTeamResponse.from_orm(team)
    except Exception as e:
        logger.error(f"创建值班团队失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/teams", response_model=List[OnCallTeamResponse])
async def list_teams(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """获取值班团队列表"""
    result = await db.execute(
        select(OnCallTeam).where(OnCallTeam.enabled == True)
        .order_by(OnCallTeam.created_at.desc())
    )
    teams = result.scalars().all()
    return [OnCallTeamResponse.from_orm(team) for team in teams]


@router.get("/teams/{team_id}", response_model=OnCallTeamResponse)
async def get_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """获取值班团队详情"""
    result = await db.execute(
        select(OnCallTeam).where(OnCallTeam.id == team_id)
    )
    team = result.scalar_one_or_none()
    
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    
    return OnCallTeamResponse.from_orm(team)


@router.put("/teams/{team_id}", response_model=OnCallTeamResponse)
async def update_team(
    team_id: int,
    team_data: OnCallTeamUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """更新值班团队"""
    result = await db.execute(
        select(OnCallTeam).where(OnCallTeam.id == team_id)
    )
    team = result.scalar_one_or_none()
    
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    
    for field, value in team_data.dict(exclude_unset=True).items():
        setattr(team, field, value)
    
    team.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(team)
    
    return OnCallTeamResponse.from_orm(team)


@router.post("/teams/{team_id}/members", response_model=OnCallMemberResponse)
async def add_team_member(
    team_id: int,
    member_data: OnCallMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """添加团队成员"""
    try:
        member_data.team_id = team_id
        member = await oncall_manager.add_member(member_data.dict())
        return OnCallMemberResponse.from_orm(member)
    except Exception as e:
        logger.error(f"添加团队成员失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/teams/{team_id}/members", response_model=List[OnCallMemberResponse])
async def list_team_members(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """获取团队成员列表"""
    result = await db.execute(
        select(OnCallMember).where(
            and_(
                OnCallMember.team_id == team_id,
                OnCallMember.enabled == True
            )
        ).order_by(OnCallMember.escalation_level, OnCallMember.created_at)
    )
    members = result.scalars().all()
    return [OnCallMemberResponse.from_orm(member) for member in members]


@router.get("/teams/{team_id}/current-oncall")
async def get_current_oncall(
    team_id: int):
    """获取当前值班人员"""
    member = await oncall_manager.get_current_oncall(team_id)
    
    if not member:
        return {"message": "当前无值班人员"}
    
    return {
        "member": OnCallMemberResponse.from_orm(member),
        "user": {
            "id": member.user.id,
            "username": member.user.username,
            "full_name": member.user.full_name,
            "email": member.user.email
        }
    }


@router.post("/schedules", response_model=OnCallScheduleResponse)
async def create_schedule(
    schedule_data: OnCallScheduleCreate):
    """创建值班计划"""
    try:
        schedule = await oncall_manager.create_schedule(schedule_data.dict())
        return OnCallScheduleResponse.from_orm(schedule)
    except Exception as e:
        logger.error(f"创建值班计划失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/schedules", response_model=List[OnCallScheduleResponse])
async def list_schedules(
    team_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """获取值班计划列表"""
    query = select(OnCallSchedule).where(OnCallSchedule.enabled == True)
    
    if team_id:
        query = query.where(OnCallSchedule.team_id == team_id)
    
    result = await db.execute(query.order_by(OnCallSchedule.created_at.desc()))
    schedules = result.scalars().all()
    return [OnCallScheduleResponse.from_orm(schedule) for schedule in schedules]


@router.get("/teams/{team_id}/schedule")
async def get_team_schedule(
    team_id: int,
    start_date: Optional[datetime] = Query(None),
    days: int = Query(30, ge=1, le=365)):
    """获取团队排班表"""
    if not start_date:
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    schedule = await oncall_manager.get_team_schedule(team_id, start_date, days)
    return {
        "team_id": team_id,
        "start_date": start_date,
        "days": days,
        "schedule": schedule
    }


@router.post("/overrides", response_model=OnCallOverrideResponse)
async def create_override(
    override_data: OnCallOverrideCreate):
    """创建值班覆盖"""
    try:
        override_dict = override_data.dict()
        override_dict["created_by"] = 1  # 默认用户ID
        override = await oncall_manager.create_override(override_dict)
        return OnCallOverrideResponse.from_orm(override)
    except Exception as e:
        logger.error(f"创建值班覆盖失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/escalation-policies", response_model=EscalationPolicyResponse)
async def create_escalation_policy(
    policy_data: EscalationPolicyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """创建升级策略"""
    try:
        policy = EscalationPolicy(**policy_data.dict())
        db.add(policy)
        await db.commit()
        await db.refresh(policy)
        
        return EscalationPolicyResponse.from_orm(policy)
    except Exception as e:
        logger.error(f"创建升级策略失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/escalation-policies", response_model=List[EscalationPolicyResponse])
async def list_escalation_policies(
    team_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """获取升级策略列表"""
    query = select(EscalationPolicy).where(EscalationPolicy.enabled == True)
    
    if team_id:
        query = query.where(EscalationPolicy.team_id == team_id)
    
    result = await db.execute(query.order_by(EscalationPolicy.created_at.desc()))
    policies = result.scalars().all()
    return [EscalationPolicyResponse.from_orm(policy) for policy in policies]


@router.post("/escalation/{alarm_id}/trigger")
async def trigger_escalation(
    alarm_id: int,
    team_id: Optional[int] = Query(None)):
    """触发告警升级"""
    success = await escalation_engine.trigger_escalation(alarm_id, team_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="触发升级失败")
    
    return {"message": "升级已触发", "alarm_id": alarm_id}


@router.post("/escalation/{alarm_id}/acknowledge")
async def acknowledge_escalation(
    alarm_id: int):
    """确认告警升级"""
    success = await escalation_engine.acknowledge_escalation(alarm_id, 1)
    
    if not success:
        raise HTTPException(status_code=400, detail="确认升级失败")
    
    return {"message": "升级已确认", "alarm_id": alarm_id}


@router.post("/escalation/{alarm_id}/resolve")
async def resolve_escalation(
    alarm_id: int):
    """解决告警升级"""
    success = await escalation_engine.resolve_escalation(alarm_id, 1)
    
    if not success:
        raise HTTPException(status_code=400, detail="解决升级失败")
    
    return {"message": "升级已解决", "alarm_id": alarm_id}


@router.get("/escalation/{alarm_id}/status")
async def get_escalation_status(
    alarm_id: int):
    """获取升级状态"""
    status = await escalation_engine.get_escalation_status(alarm_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="未找到升级记录")
    
    return status


@router.get("/escalations/active")
async def get_active_escalations(
):
    """获取所有活跃升级"""
    escalations = await escalation_engine.get_active_escalations()
    return {"escalations": escalations}


@router.get("/members/{member_id}/stats")
async def get_member_stats(
    member_id: int,
    days: int = Query(30, ge=1, le=365)):
    """获取成员统计"""
    stats = await oncall_manager.get_member_stats(member_id, days)
    return {
        "member_id": member_id,
        "period_days": days,
        "stats": stats
    }