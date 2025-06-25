"""
告警升级引擎
自动处理告警升级和通知流程
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update

from src.models.alarm import AlarmTable, AlarmSeverity, AlarmStatus
from src.models.oncall import OnCallTeam, OnCallMember, EscalationPolicy
from src.services.oncall_manager import oncall_manager
from src.core.database import async_session_maker
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EscalationStatus(str, Enum):
    """升级状态"""
    PENDING = "pending"           # 待处理
    NOTIFIED = "notified"         # 已通知
    ACKNOWLEDGED = "acknowledged" # 已确认
    ESCALATED = "escalated"       # 已升级
    RESOLVED = "resolved"         # 已解决
    TIMEOUT = "timeout"           # 超时


@dataclass
class EscalationStep:
    """升级步骤"""
    level: str
    members: List[OnCallMember]
    delay: int  # 延迟时间(秒)
    timeout: int  # 超时时间(秒)
    notification_methods: List[str]


@dataclass
class EscalationExecution:
    """升级执行状态"""
    alarm_id: int
    steps: List[EscalationStep]
    current_step: int
    status: EscalationStatus
    started_at: datetime
    last_notification: Optional[datetime]
    acknowledged_by: Optional[int]
    acknowledged_at: Optional[datetime]


class EscalationEngine:
    """告警升级引擎"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.active_escalations: Dict[int, EscalationExecution] = {}
        self.running = False
    
    async def start(self):
        """启动升级引擎"""
        self.running = True
        self.logger.info("告警升级引擎启动")
        
        # 启动后台任务
        asyncio.create_task(self._escalation_loop())
    
    async def stop(self):
        """停止升级引擎"""
        self.running = False
        self.logger.info("告警升级引擎停止")
    
    async def trigger_escalation(self, alarm_id: int, team_id: Optional[int] = None) -> bool:
        """触发告警升级"""
        try:
            # 检查是否已在升级中
            if alarm_id in self.active_escalations:
                self.logger.warning(f"告警 {alarm_id} 已在升级中")
                return False
            
            # 获取告警信息
            async with async_session_maker() as session:
                result = await session.execute(
                    select(AlarmTable).where(AlarmTable.id == alarm_id)
                )
                alarm = result.scalar_one_or_none()
                
                if not alarm:
                    self.logger.error(f"告警 {alarm_id} 不存在")
                    return False
                
                # 确定负责团队
                if not team_id:
                    team_id = await self._determine_responsible_team(alarm)
                
                if not team_id:
                    self.logger.warning(f"告警 {alarm_id} 无法确定负责团队")
                    return False
                
                # 构建升级步骤
                steps = await self._build_escalation_steps(session, team_id, alarm.severity)
                
                if not steps:
                    self.logger.warning(f"团队 {team_id} 没有可用的升级步骤")
                    return False
                
                # 创建升级执行
                execution = EscalationExecution(
                    alarm_id=alarm_id,
                    steps=steps,
                    current_step=0,
                    status=EscalationStatus.PENDING,
                    started_at=datetime.utcnow(),
                    last_notification=None,
                    acknowledged_by=None,
                    acknowledged_at=None
                )
                
                self.active_escalations[alarm_id] = execution
                
                # 立即执行第一步
                await self._execute_step(execution, 0)
                
                self.logger.info(f"触发告警 {alarm_id} 升级，共 {len(steps)} 个步骤")
                return True
                
        except Exception as e:
            self.logger.error(f"触发升级失败: {str(e)}")
            return False
    
    async def acknowledge_escalation(self, alarm_id: int, user_id: int) -> bool:
        """确认升级"""
        if alarm_id not in self.active_escalations:
            return False
        
        execution = self.active_escalations[alarm_id]
        execution.status = EscalationStatus.ACKNOWLEDGED
        execution.acknowledged_by = user_id
        execution.acknowledged_at = datetime.utcnow()
        
        self.logger.info(f"用户 {user_id} 确认告警 {alarm_id} 升级")
        return True
    
    async def resolve_escalation(self, alarm_id: int, user_id: int) -> bool:
        """解决升级"""
        if alarm_id not in self.active_escalations:
            return False
        
        execution = self.active_escalations[alarm_id]
        execution.status = EscalationStatus.RESOLVED
        
        # 从活跃列表中移除
        del self.active_escalations[alarm_id]
        
        self.logger.info(f"用户 {user_id} 解决告警 {alarm_id} 升级")
        return True
    
    async def _escalation_loop(self):
        """升级主循环"""
        while self.running:
            try:
                current_time = datetime.utcnow()
                completed_escalations = []
                
                for alarm_id, execution in self.active_escalations.items():
                    # 检查是否已确认或解决
                    if execution.status in [EscalationStatus.ACKNOWLEDGED, EscalationStatus.RESOLVED]:
                        continue
                    
                    # 检查当前步骤是否超时
                    if await self._check_step_timeout(execution, current_time):
                        # 升级到下一步
                        next_step = execution.current_step + 1
                        if next_step < len(execution.steps):
                            await self._execute_step(execution, next_step)
                            execution.current_step = next_step
                        else:
                            # 所有步骤都已执行，标记为超时
                            execution.status = EscalationStatus.TIMEOUT
                            completed_escalations.append(alarm_id)
                            self.logger.warning(f"告警 {alarm_id} 升级超时")
                
                # 清理已完成的升级
                for alarm_id in completed_escalations:
                    del self.active_escalations[alarm_id]
                
                # 等待下一次检查
                await asyncio.sleep(30)  # 30秒检查一次
                
            except Exception as e:
                self.logger.error(f"升级循环异常: {str(e)}")
                await asyncio.sleep(60)  # 出错时等待更长时间
    
    async def _determine_responsible_team(self, alarm: AlarmTable) -> Optional[int]:
        """确定负责团队"""
        # 基于系统ID确定团队
        if alarm.system_id:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(OnCallTeam).where(
                        and_(
                            OnCallTeam.system_id == alarm.system_id,
                            OnCallTeam.enabled == True
                        )
                    )
                )
                team = result.scalar_one_or_none()
                return team.id if team else None
        
        # 基于标签或其他规则确定团队
        # TODO: 实现更复杂的团队匹配逻辑
        
        return None
    
    async def _build_escalation_steps(
        self, 
        session: AsyncSession, 
        team_id: int, 
        severity: str
    ) -> List[EscalationStep]:
        """构建升级步骤"""
        steps = []
        
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
            # 默认升级策略
            steps = await self._build_default_escalation_steps(session, team_id)
        else:
            # 根据策略构建
            steps = await self._build_policy_escalation_steps(session, policy, severity)
        
        return steps
    
    async def _build_default_escalation_steps(
        self, 
        session: AsyncSession, 
        team_id: int
    ) -> List[EscalationStep]:
        """构建默认升级步骤"""
        steps = []
        
        # L1 级别成员
        l1_result = await session.execute(
            select(OnCallMember).where(
                and_(
                    OnCallMember.team_id == team_id,
                    OnCallMember.escalation_level == "L1",
                    OnCallMember.enabled == True
                )
            )
        )
        l1_members = l1_result.scalars().all()
        
        if l1_members:
            steps.append(EscalationStep(
                level="L1",
                members=l1_members,
                delay=0,
                timeout=300,  # 5分钟
                notification_methods=["email", "sms"]
            ))
        
        # L2 级别成员
        l2_result = await session.execute(
            select(OnCallMember).where(
                and_(
                    OnCallMember.team_id == team_id,
                    OnCallMember.escalation_level == "L2",
                    OnCallMember.enabled == True
                )
            )
        )
        l2_members = l2_result.scalars().all()
        
        if l2_members:
            steps.append(EscalationStep(
                level="L2",
                members=l2_members,
                delay=300,  # 5分钟后
                timeout=600,  # 10分钟
                notification_methods=["email", "sms", "phone"]
            ))
        
        # L3 级别成员
        l3_result = await session.execute(
            select(OnCallMember).where(
                and_(
                    OnCallMember.team_id == team_id,
                    OnCallMember.escalation_level == "L3",
                    OnCallMember.enabled == True
                )
            )
        )
        l3_members = l3_result.scalars().all()
        
        if l3_members:
            steps.append(EscalationStep(
                level="L3",
                members=l3_members,
                delay=900,  # 15分钟后
                timeout=1200,  # 20分钟
                notification_methods=["email", "sms", "phone"]
            ))
        
        return steps
    
    async def _build_policy_escalation_steps(
        self, 
        session: AsyncSession, 
        policy: EscalationPolicy, 
        severity: str
    ) -> List[EscalationStep]:
        """根据策略构建升级步骤"""
        steps = []
        
        # 检查严重程度过滤
        if policy.severity_filter and severity not in policy.severity_filter:
            return steps
        
        # 解析升级规则
        escalation_rules = policy.escalation_rules or []
        
        for rule in escalation_rules:
            level = rule.get("level", "L1")
            delay = rule.get("delay", 0)
            timeout = rule.get("timeout", 300)
            methods = rule.get("notification_methods", ["email"])
            
            # 获取该级别的成员
            result = await session.execute(
                select(OnCallMember).where(
                    and_(
                        OnCallMember.team_id == policy.team_id,
                        OnCallMember.escalation_level == level,
                        OnCallMember.enabled == True
                    )
                )
            )
            members = result.scalars().all()
            
            if members:
                steps.append(EscalationStep(
                    level=level,
                    members=members,
                    delay=delay,
                    timeout=timeout,
                    notification_methods=methods
                ))
        
        return steps
    
    async def _execute_step(self, execution: EscalationExecution, step_index: int):
        """执行升级步骤"""
        if step_index >= len(execution.steps):
            return
        
        step = execution.steps[step_index]
        current_time = datetime.utcnow()
        
        # 更新执行状态
        execution.status = EscalationStatus.NOTIFIED
        execution.last_notification = current_time
        
        # 获取告警信息
        async with async_session_maker() as session:
            result = await session.execute(
                select(AlarmTable).where(AlarmTable.id == execution.alarm_id)
            )
            alarm = result.scalar_one_or_none()
            
            if not alarm:
                return
            
            # 准备通知数据
            alert_data = {
                "id": alarm.id,
                "title": alarm.title,
                "description": alarm.description,
                "severity": alarm.severity,
                "source": alarm.source,
                "host": alarm.host,
                "service": alarm.service,
                "created_at": alarm.created_at.isoformat(),
                "escalation_level": step.level,
                "escalation_step": step_index + 1,
                "total_steps": len(execution.steps)
            }
            
            # 通知所有成员
            for member in step.members:
                try:
                    await oncall_manager.notify_oncall_member(member, alert_data)
                except Exception as e:
                    self.logger.error(f"通知成员 {member.id} 失败: {str(e)}")
            
            self.logger.info(
                f"执行告警 {execution.alarm_id} 升级步骤 {step_index + 1}/{len(execution.steps)} "
                f"(级别: {step.level}, 成员: {len(step.members)})"
            )
    
    async def _check_step_timeout(self, execution: EscalationExecution, current_time: datetime) -> bool:
        """检查步骤是否超时"""
        if execution.current_step >= len(execution.steps):
            return False
        
        step = execution.steps[execution.current_step]
        
        # 计算步骤开始时间
        if execution.current_step == 0:
            step_start = execution.started_at
        else:
            step_start = execution.last_notification or execution.started_at
        
        # 检查是否超时
        elapsed = (current_time - step_start).total_seconds()
        return elapsed >= step.timeout
    
    async def get_escalation_status(self, alarm_id: int) -> Optional[Dict[str, Any]]:
        """获取升级状态"""
        if alarm_id not in self.active_escalations:
            return None
        
        execution = self.active_escalations[alarm_id]
        
        return {
            "alarm_id": execution.alarm_id,
            "status": execution.status,
            "current_step": execution.current_step + 1,
            "total_steps": len(execution.steps),
            "started_at": execution.started_at.isoformat(),
            "last_notification": execution.last_notification.isoformat() if execution.last_notification else None,
            "acknowledged_by": execution.acknowledged_by,
            "acknowledged_at": execution.acknowledged_at.isoformat() if execution.acknowledged_at else None,
            "steps": [
                {
                    "level": step.level,
                    "member_count": len(step.members),
                    "delay": step.delay,
                    "timeout": step.timeout,
                    "notification_methods": step.notification_methods
                }
                for step in execution.steps
            ]
        }
    
    async def get_active_escalations(self) -> List[Dict[str, Any]]:
        """获取所有活跃升级"""
        return [
            await self.get_escalation_status(alarm_id) 
            for alarm_id in self.active_escalations.keys()
        ]


# 全局实例
escalation_engine = EscalationEngine()