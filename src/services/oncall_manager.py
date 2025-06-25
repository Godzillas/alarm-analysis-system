"""
值班管理服务
"""

import asyncio
from datetime import datetime, timedelta, time
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from src.models.oncall import (
    OnCallTeam, OnCallMember, OnCallSchedule, OnCallShift, 
    EscalationPolicy, OnCallOverride,
    OnCallShiftType, OnCallStatus, EscalationLevel
)
from src.models.alarm import User, AlarmTable, AlarmSeverity
from src.core.database import async_session_maker
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OnCallManager:
    """值班管理器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    async def create_team(self, team_data: Dict[str, Any]) -> OnCallTeam:
        """创建值班团队"""
        async with async_session_maker() as session:
            try:
                team = OnCallTeam(**team_data)
                session.add(team)
                await session.commit()
                await session.refresh(team)
                
                self.logger.info(f"创建值班团队: {team.name}")
                return team
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"创建值班团队失败: {str(e)}")
                raise
    
    async def add_member(self, member_data: Dict[str, Any]) -> OnCallMember:
        """添加团队成员"""
        async with async_session_maker() as session:
            try:
                # 检查用户是否已在团队中
                existing = await session.execute(
                    select(OnCallMember).where(
                        and_(
                            OnCallMember.team_id == member_data['team_id'],
                            OnCallMember.user_id == member_data['user_id']
                        )
                    )
                )
                
                if existing.scalar_one_or_none():
                    raise ValueError("用户已在团队中")
                
                member = OnCallMember(**member_data)
                session.add(member)
                await session.commit()
                await session.refresh(member)
                
                self.logger.info(f"添加团队成员: 团队{member.team_id}, 用户{member.user_id}")
                return member
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"添加团队成员失败: {str(e)}")
                raise
    
    async def create_schedule(self, schedule_data: Dict[str, Any]) -> OnCallSchedule:
        """创建值班计划"""
        async with async_session_maker() as session:
            try:
                schedule = OnCallSchedule(**schedule_data)
                session.add(schedule)
                await session.commit()
                await session.refresh(schedule)
                
                # 自动生成初始班次
                await self._generate_shifts(session, schedule)
                
                self.logger.info(f"创建值班计划: {schedule.name}")
                return schedule
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"创建值班计划失败: {str(e)}")
                raise
    
    async def _generate_shifts(self, session: AsyncSession, schedule: OnCallSchedule):
        """生成班次"""
        # 获取团队成员
        result = await session.execute(
            select(OnCallMember).where(
                and_(
                    OnCallMember.team_id == schedule.team_id,
                    OnCallMember.enabled == True
                )
            ).order_by(OnCallMember.id)
        )
        members = result.scalars().all()
        
        if not members:
            self.logger.warning(f"团队 {schedule.team_id} 没有可用成员")
            return
        
        # 生成未来30天的班次
        current_time = schedule.rotation_start
        end_time = current_time + timedelta(days=30)
        member_index = 0
        
        while current_time < end_time:
            shift_end = current_time + timedelta(days=schedule.shift_duration)
            
            shift = OnCallShift(
                schedule_id=schedule.id,
                member_id=members[member_index].id,
                start_time=current_time,
                end_time=shift_end,
                status=OnCallStatus.SCHEDULED
            )
            
            session.add(shift)
            
            # 轮换到下一个成员
            member_index = (member_index + 1) % len(members)
            current_time = shift_end
        
        await session.commit()
        self.logger.info(f"为计划 {schedule.name} 生成班次")
    
    async def get_current_oncall(self, team_id: int) -> Optional[OnCallMember]:
        """获取当前值班人员"""
        current_time = datetime.utcnow()
        
        async with async_session_maker() as session:
            # 首先检查是否有覆盖值班
            override_result = await session.execute(
                select(OnCallOverride).where(
                    and_(
                        OnCallOverride.team_id == team_id,
                        OnCallOverride.start_time <= current_time,
                        OnCallOverride.end_time >= current_time
                    )
                )
            )
            override = override_result.scalar_one_or_none()
            
            if override:
                # 返回覆盖值班人员
                member_result = await session.execute(
                    select(OnCallMember).where(
                        and_(
                            OnCallMember.team_id == team_id,
                            OnCallMember.user_id == override.user_id
                        )
                    ).options(selectinload(OnCallMember.user))
                )
                return member_result.scalar_one_or_none()
            
            # 查找当前班次
            shift_result = await session.execute(
                select(OnCallShift).join(OnCallMember).where(
                    and_(
                        OnCallMember.team_id == team_id,
                        OnCallShift.start_time <= current_time,
                        OnCallShift.end_time >= current_time,
                        OnCallShift.status == OnCallStatus.ACTIVE
                    )
                ).options(selectinload(OnCallShift.member).selectinload(OnCallMember.user))
            )
            
            shift = shift_result.scalar_one_or_none()
            return shift.member if shift else None
    
    async def get_escalation_chain(self, team_id: int, severity: str) -> List[OnCallMember]:
        """获取升级链"""
        async with async_session_maker() as session:
            # 获取升级策略
            policy_result = await session.execute(
                select(EscalationPolicy).where(
                    and_(
                        EscalationPolicy.team_id == team_id,
                        EscalationPolicy.enabled == True
                    )
                )
            )
            policy = policy_result.scalar_one_or_none()
            
            if not policy:
                # 没有策略，返回所有成员
                result = await session.execute(
                    select(OnCallMember).where(
                        and_(
                            OnCallMember.team_id == team_id,
                            OnCallMember.enabled == True
                        )
                    ).options(selectinload(OnCallMember.user))
                    .order_by(OnCallMember.escalation_level)
                )
                return result.scalars().all()
            
            # 根据策略筛选
            severity_filter = policy.severity_filter
            if severity_filter and severity not in severity_filter:
                return []
            
            # 构建升级链
            escalation_rules = policy.escalation_rules
            chain = []
            
            for rule in escalation_rules:
                level = rule.get('level', 'L1')
                delay = rule.get('delay', 300)  # 延迟时间
                
                # 查找该级别的成员
                result = await session.execute(
                    select(OnCallMember).where(
                        and_(
                            OnCallMember.team_id == team_id,
                            OnCallMember.escalation_level == level,
                            OnCallMember.enabled == True
                        )
                    ).options(selectinload(OnCallMember.user))
                )
                
                level_members = result.scalars().all()
                for member in level_members:
                    member.escalation_delay = delay  # 临时属性
                    chain.append(member)
            
            return chain
    
    async def acknowledge_alert(self, shift_id: int, user_id: int, response_time: int):
        """确认告警"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(OnCallShift).where(OnCallShift.id == shift_id)
                )
                shift = result.scalar_one_or_none()
                
                if shift:
                    shift.alerts_acknowledged += 1
                    
                    # 更新平均响应时间
                    if shift.alerts_received > 0:
                        total_time = shift.response_time_avg * (shift.alerts_received - 1)
                        shift.response_time_avg = (total_time + response_time) // shift.alerts_received
                    else:
                        shift.response_time_avg = response_time
                    
                    await session.commit()
                    self.logger.info(f"用户 {user_id} 确认班次 {shift_id} 的告警")
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"确认告警失败: {str(e)}")
                raise
    
    async def resolve_alert(self, shift_id: int, user_id: int):
        """解决告警"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(OnCallShift).where(OnCallShift.id == shift_id)
                )
                shift = result.scalar_one_or_none()
                
                if shift:
                    shift.alerts_resolved += 1
                    await session.commit()
                    self.logger.info(f"用户 {user_id} 解决班次 {shift_id} 的告警")
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"解决告警失败: {str(e)}")
                raise
    
    async def create_override(self, override_data: Dict[str, Any]) -> OnCallOverride:
        """创建值班覆盖"""
        async with async_session_maker() as session:
            try:
                # 检查时间冲突
                result = await session.execute(
                    select(OnCallOverride).where(
                        and_(
                            OnCallOverride.team_id == override_data['team_id'],
                            or_(
                                and_(
                                    OnCallOverride.start_time <= override_data['start_time'],
                                    OnCallOverride.end_time >= override_data['start_time']
                                ),
                                and_(
                                    OnCallOverride.start_time <= override_data['end_time'],
                                    OnCallOverride.end_time >= override_data['end_time']
                                )
                            )
                        )
                    )
                )
                
                if result.scalar_one_or_none():
                    raise ValueError("时间段冲突")
                
                override = OnCallOverride(**override_data)
                session.add(override)
                await session.commit()
                await session.refresh(override)
                
                self.logger.info(f"创建值班覆盖: 团队{override.team_id}, 用户{override.user_id}")
                return override
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"创建值班覆盖失败: {str(e)}")
                raise
    
    async def get_team_schedule(self, team_id: int, start_date: datetime, days: int = 30) -> List[Dict[str, Any]]:
        """获取团队排班表"""
        end_date = start_date + timedelta(days=days)
        
        async with async_session_maker() as session:
            # 获取班次
            shift_result = await session.execute(
                select(OnCallShift).join(OnCallMember).where(
                    and_(
                        OnCallMember.team_id == team_id,
                        OnCallShift.start_time >= start_date,
                        OnCallShift.start_time <= end_date
                    )
                ).options(
                    selectinload(OnCallShift.member).selectinload(OnCallMember.user)
                ).order_by(OnCallShift.start_time)
            )
            shifts = shift_result.scalars().all()
            
            # 获取覆盖
            override_result = await session.execute(
                select(OnCallOverride).where(
                    and_(
                        OnCallOverride.team_id == team_id,
                        OnCallOverride.start_time >= start_date,
                        OnCallOverride.start_time <= end_date
                    )
                ).options(selectinload(OnCallOverride.user))
                .order_by(OnCallOverride.start_time)
            )
            overrides = override_result.scalars().all()
            
            # 合并结果
            schedule = []
            
            for shift in shifts:
                schedule.append({
                    "type": "shift",
                    "id": shift.id,
                    "user": {
                        "id": shift.member.user.id,
                        "username": shift.member.user.username,
                        "full_name": shift.member.user.full_name
                    },
                    "start_time": shift.start_time,
                    "end_time": shift.end_time,
                    "status": shift.status,
                    "stats": {
                        "alerts_received": shift.alerts_received,
                        "alerts_acknowledged": shift.alerts_acknowledged,
                        "alerts_resolved": shift.alerts_resolved,
                        "response_time_avg": shift.response_time_avg
                    }
                })
            
            for override in overrides:
                schedule.append({
                    "type": "override",
                    "id": override.id,
                    "user": {
                        "id": override.user.id,
                        "username": override.user.username,
                        "full_name": override.user.full_name
                    },
                    "start_time": override.start_time,
                    "end_time": override.end_time,
                    "reason": override.reason
                })
            
            # 按时间排序
            schedule.sort(key=lambda x: x["start_time"])
            
            return schedule
    
    async def get_member_stats(self, member_id: int, days: int = 30) -> Dict[str, Any]:
        """获取成员统计"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        async with async_session_maker() as session:
            # 获取成员的班次统计
            result = await session.execute(
                select(
                    func.count(OnCallShift.id).label('total_shifts'),
                    func.sum(OnCallShift.alerts_received).label('total_alerts'),
                    func.sum(OnCallShift.alerts_acknowledged).label('total_acknowledged'),
                    func.sum(OnCallShift.alerts_resolved).label('total_resolved'),
                    func.avg(OnCallShift.response_time_avg).label('avg_response_time')
                ).where(
                    and_(
                        OnCallShift.member_id == member_id,
                        OnCallShift.start_time >= start_date
                    )
                )
            )
            
            stats = result.first()
            
            return {
                "total_shifts": stats.total_shifts or 0,
                "total_alerts": stats.total_alerts or 0,
                "total_acknowledged": stats.total_acknowledged or 0,
                "total_resolved": stats.total_resolved or 0,
                "avg_response_time": int(stats.avg_response_time or 0),
                "acknowledgment_rate": (
                    (stats.total_acknowledged / stats.total_alerts * 100) 
                    if stats.total_alerts else 0
                ),
                "resolution_rate": (
                    (stats.total_resolved / stats.total_alerts * 100) 
                    if stats.total_alerts else 0
                )
            }
    
    async def advance_schedule(self, schedule_id: int):
        """推进排班计划"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(OnCallSchedule).where(OnCallSchedule.id == schedule_id)
                )
                schedule = result.scalar_one_or_none()
                
                if not schedule or not schedule.auto_advance:
                    return
                
                # 检查是否需要生成新的班次
                last_shift_result = await session.execute(
                    select(OnCallShift).where(
                        OnCallShift.schedule_id == schedule_id
                    ).order_by(desc(OnCallShift.end_time)).limit(1)
                )
                
                last_shift = last_shift_result.scalar_one_or_none()
                current_time = datetime.utcnow()
                
                # 如果最后一个班次即将结束（24小时内），生成新班次
                if last_shift and (last_shift.end_time - current_time).total_seconds() < 86400:
                    await self._generate_shifts(session, schedule)
                    self.logger.info(f"自动推进排班计划: {schedule.name}")
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"推进排班计划失败: {str(e)}")
                raise
    
    async def notify_oncall_member(self, member: OnCallMember, alert_data: Dict[str, Any]):
        """通知值班成员"""
        try:
            # 这里实现通知逻辑
            # 可以集成短信、电话、邮件等通知方式
            
            contact_methods = member.contact_methods or []
            
            for method in contact_methods:
                if method == "email":
                    await self._send_email_notification(member, alert_data)
                elif method == "sms":
                    await self._send_sms_notification(member, alert_data)
                elif method == "phone":
                    await self._make_phone_call(member, alert_data)
            
            self.logger.info(f"通知值班成员 {member.user_id}: {alert_data['title']}")
            
        except Exception as e:
            self.logger.error(f"通知值班成员失败: {str(e)}")
    
    async def _send_email_notification(self, member: OnCallMember, alert_data: Dict[str, Any]):
        """发送邮件通知"""
        # TODO: 实现邮件通知
        pass
    
    async def _send_sms_notification(self, member: OnCallMember, alert_data: Dict[str, Any]):
        """发送短信通知"""
        # TODO: 实现短信通知
        pass
    
    async def _make_phone_call(self, member: OnCallMember, alert_data: Dict[str, Any]):
        """拨打电话通知"""
        # TODO: 实现电话通知
        pass


# 全局实例
oncall_manager = OnCallManager()