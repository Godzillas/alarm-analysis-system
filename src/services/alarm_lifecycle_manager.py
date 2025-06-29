"""
告警生命周期管理器
实现完整的告警生命周期自动化管理
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from src.core.database import async_session_maker
from src.core.logging import get_logger
from src.models.alarm import AlarmTable, AlarmStatus, AlarmSeverity
from src.models.alarm_processing import (
    AlarmProcessing, AlarmProcessingStatus, AlarmPriority,
    ProcessingActionType, AlarmProcessingHistory
)
from src.services.notification_service import NotificationService
from src.services.oncall_manager import OnCallManager

logger = get_logger(__name__)


class LifecycleEventType(Enum):
    """生命周期事件类型"""
    CREATED = "created"
    ACKNOWLEDGED = "acknowledged"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"
    SLA_WARNING = "sla_warning"
    SLA_BREACH = "sla_breach"


@dataclass
class LifecycleRule:
    """生命周期规则"""
    name: str
    condition: Dict[str, Any]
    action: Dict[str, Any]
    priority: int = 100
    enabled: bool = True


@dataclass
class EscalationLevel:
    """升级级别"""
    level: int
    delay_minutes: int
    targets: List[int]  # 用户ID列表
    notification_channels: List[str]
    auto_assign: bool = False


class AlarmLifecycleManager:
    """告警生命周期管理器"""
    
    def __init__(self):
        self.logger = logger
        self.notification_service = NotificationService()
        self.oncall_manager = OnCallManager()
        self.rules: List[LifecycleRule] = []
        self.escalation_policies: Dict[str, List[EscalationLevel]] = {}
        self._load_default_rules()
        self._load_escalation_policies()
    
    def _load_default_rules(self):
        """加载默认生命周期规则"""
        self.rules = [
            # 自动确认规则
            LifecycleRule(
                name="auto_acknowledge_low_priority",
                condition={
                    "severity": ["low", "info"],
                    "age_minutes": 5,
                    "status": ["active"]
                },
                action={
                    "type": "acknowledge",
                    "message": "低优先级告警自动确认"
                },
                priority=200
            ),
            
            # SLA预警规则
            LifecycleRule(
                name="sla_warning",
                condition={
                    "sla_remaining_percent": 20,
                    "status": ["pending", "acknowledged", "in_progress"]
                },
                action={
                    "type": "sla_warning",
                    "notify": ["assigned_user", "manager"]
                },
                priority=50
            ),
            
            # 自动升级规则
            LifecycleRule(
                name="auto_escalate_critical",
                condition={
                    "severity": ["critical"],
                    "age_minutes": 30,
                    "status": ["pending"]
                },
                action={
                    "type": "escalate",
                    "escalation_policy": "critical_alerts"
                },
                priority=10
            ),
            
            # 智能关闭规则
            LifecycleRule(
                name="auto_close_resolved",
                condition={
                    "status": ["resolved"],
                    "age_hours": 24,
                    "no_activity_hours": 2
                },
                action={
                    "type": "close",
                    "message": "已解决告警自动关闭"
                },
                priority=300
            )
        ]
    
    def _load_escalation_policies(self):
        """加载升级策略"""
        self.escalation_policies = {
            "critical_alerts": [
                EscalationLevel(
                    level=1,
                    delay_minutes=15,
                    targets=[],  # 当前值班人员
                    notification_channels=["email", "sms", "phone"],
                    auto_assign=True
                ),
                EscalationLevel(
                    level=2,
                    delay_minutes=30,
                    targets=[],  # 值班经理
                    notification_channels=["email", "sms", "phone", "slack"],
                    auto_assign=True
                ),
                EscalationLevel(
                    level=3,
                    delay_minutes=60,
                    targets=[],  # 技术总监
                    notification_channels=["email", "sms", "phone", "slack"],
                    auto_assign=False
                )
            ],
            
            "high_alerts": [
                EscalationLevel(
                    level=1,
                    delay_minutes=30,
                    targets=[],
                    notification_channels=["email", "slack"],
                    auto_assign=True
                ),
                EscalationLevel(
                    level=2,
                    delay_minutes=120,
                    targets=[],
                    notification_channels=["email", "sms", "slack"],
                    auto_assign=True
                )
            ],
            
            "medium_alerts": [
                EscalationLevel(
                    level=1,
                    delay_minutes=120,
                    targets=[],
                    notification_channels=["email"],
                    auto_assign=False
                )
            ]
        }
    
    async def process_lifecycle_events(self):
        """处理生命周期事件"""
        try:
            async with async_session_maker() as session:
                # 获取需要处理的告警
                from sqlalchemy import select, and_, or_
                from sqlalchemy.orm import selectinload, joinedload
                
                # 查询告警和对应的处理记录
                query = select(AlarmTable).where(
                    AlarmTable.status.in_(['active', 'acknowledged'])
                )
                
                result = await session.execute(query)
                alarms = result.scalars().all()
                
                for alarm in alarms:
                    # 获取告警的处理记录
                    processing_query = select(AlarmProcessing).where(
                        AlarmProcessing.alarm_id == alarm.id
                    )
                    processing_result = await session.execute(processing_query)
                    processing_records = processing_result.scalars().all()
                    
                    # 为告警添加处理记录属性
                    alarm.processing = processing_records
                    
                    await self._process_alarm_lifecycle(session, alarm)
                
                await session.commit()
                
        except Exception as e:
            self.logger.error(f"处理生命周期事件失败: {str(e)}")
    
    async def _process_alarm_lifecycle(self, session, alarm: AlarmTable):
        """处理单个告警的生命周期"""
        try:
            # 计算告警年龄
            age = datetime.utcnow() - alarm.created_at
            age_minutes = age.total_seconds() / 60
            age_hours = age_minutes / 60
            
            # 获取处理记录
            processing = alarm.processing[0] if alarm.processing else None
            
            # 应用生命周期规则
            for rule in sorted(self.rules, key=lambda r: r.priority):
                if not rule.enabled:
                    continue
                
                if await self._check_rule_condition(alarm, processing, rule.condition, age_minutes, age_hours):
                    await self._execute_rule_action(session, alarm, processing, rule.action)
                    break  # 只执行第一个匹配的规则
                    
        except Exception as e:
            self.logger.error(f"处理告警 {alarm.id} 生命周期失败: {str(e)}")
    
    async def _check_rule_condition(
        self, 
        alarm: AlarmTable, 
        processing: Optional[AlarmProcessing],
        condition: Dict[str, Any],
        age_minutes: float,
        age_hours: float
    ) -> bool:
        """检查规则条件"""
        try:
            # 检查严重程度
            if "severity" in condition:
                if alarm.severity not in condition["severity"]:
                    return False
            
            # 检查告警状态
            if "status" in condition:
                if alarm.status not in condition["status"]:
                    return False
            
            # 检查处理状态
            if "processing_status" in condition:
                if not processing or processing.status.value not in condition["processing_status"]:
                    return False
            
            # 检查年龄（分钟）
            if "age_minutes" in condition:
                if age_minutes < condition["age_minutes"]:
                    return False
            
            # 检查年龄（小时）
            if "age_hours" in condition:
                if age_hours < condition["age_hours"]:
                    return False
            
            # 检查SLA剩余时间
            if "sla_remaining_percent" in condition and processing:
                if processing.sla_deadline:
                    total_time = processing.sla_deadline - alarm.created_at
                    remaining_time = processing.sla_deadline - datetime.utcnow()
                    remaining_percent = (remaining_time.total_seconds() / total_time.total_seconds()) * 100
                    
                    if remaining_percent > condition["sla_remaining_percent"]:
                        return False
            
            # 检查无活动时间
            if "no_activity_hours" in condition and processing:
                last_activity = await self._get_last_activity_time(processing.id)
                if last_activity:
                    no_activity_hours = (datetime.utcnow() - last_activity).total_seconds() / 3600
                    if no_activity_hours < condition["no_activity_hours"]:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"检查规则条件失败: {str(e)}")
            return False
    
    async def _execute_rule_action(
        self,
        session,
        alarm: AlarmTable,
        processing: Optional[AlarmProcessing],
        action: Dict[str, Any]
    ):
        """执行规则动作"""
        try:
            action_type = action.get("type")
            
            if action_type == "acknowledge":
                await self._auto_acknowledge(session, alarm, processing, action)
            
            elif action_type == "escalate":
                await self._auto_escalate(session, alarm, processing, action)
            
            elif action_type == "sla_warning":
                await self._send_sla_warning(alarm, processing, action)
            
            elif action_type == "close":
                await self._auto_close(session, alarm, processing, action)
            
            elif action_type == "assign":
                await self._auto_assign(session, alarm, processing, action)
            
        except Exception as e:
            self.logger.error(f"执行规则动作失败: {str(e)}")
    
    async def _auto_acknowledge(
        self,
        session,
        alarm: AlarmTable,
        processing: Optional[AlarmProcessing],
        action: Dict[str, Any]
    ):
        """自动确认告警"""
        if not processing:
            # 创建处理记录
            from src.models.alarm_processing import AlarmProcessingCreate
            processing_data = AlarmProcessingCreate(
                priority=self._get_auto_priority(alarm.severity),
                estimated_effort_hours=1
            )
            
            from src.services.alarm_processing_service import AlarmProcessingService
            service = AlarmProcessingService()
            processing = await service.create_processing(alarm.id, 0, processing_data)  # 系统用户
        
        # 更新为确认状态
        processing.status = AlarmProcessingStatus.ACKNOWLEDGED
        processing.acknowledged_at = datetime.utcnow()
        processing.acknowledged_by = 0  # 系统用户
        
        # 记录历史
        await self._add_history_record(
            session,
            processing.id,
            0,  # 系统用户
            ProcessingActionType.ACKNOWLEDGE,
            notes=action.get("message", "系统自动确认"),
            new_status=AlarmProcessingStatus.ACKNOWLEDGED
        )
        
        # 更新告警状态
        alarm.status = AlarmStatus.ACKNOWLEDGED
        
        self.logger.info(f"告警 {alarm.id} 自动确认完成")
    
    async def _auto_escalate(
        self,
        session,
        alarm: AlarmTable,
        processing: Optional[AlarmProcessing],
        action: Dict[str, Any]
    ):
        """自动升级告警"""
        escalation_policy = action.get("escalation_policy")
        if not escalation_policy or escalation_policy not in self.escalation_policies:
            return
        
        levels = self.escalation_policies[escalation_policy]
        
        # 确定当前升级级别
        current_level = processing.escalation_level if processing else 0
        next_level = current_level + 1
        
        # 查找下一个升级级别
        escalation_level = None
        for level in levels:
            if level.level == next_level:
                escalation_level = level
                break
        
        if not escalation_level:
            self.logger.warning(f"未找到升级级别 {next_level}")
            return
        
        # 获取值班人员
        targets = await self._get_escalation_targets(escalation_level)
        
        if not targets:
            self.logger.warning(f"未找到升级目标用户")
            return
        
        # 更新处理记录
        if not processing:
            # 创建处理记录
            from src.models.alarm_processing import AlarmProcessingCreate
            processing_data = AlarmProcessingCreate(
                priority=self._get_auto_priority(alarm.severity),
                estimated_effort_hours=2
            )
            
            from src.services.alarm_processing_service import AlarmProcessingService
            service = AlarmProcessingService()
            processing = await service.create_processing(alarm.id, 0, processing_data)
        
        # 升级告警
        processing.escalation_level = next_level
        processing.escalated_at = datetime.utcnow()
        processing.escalated_by = 0  # 系统用户
        
        # 分配给第一个目标用户
        if escalation_level.auto_assign and targets:
            processing.assigned_to = targets[0]
            processing.assigned_by = 0
            processing.assigned_at = datetime.utcnow()
        
        # 记录历史
        await self._add_history_record(
            session,
            processing.id,
            0,
            ProcessingActionType.ESCALATE,
            notes=f"自动升级到级别 {next_level}",
            new_escalation_level=next_level,
            new_assigned_to=targets[0] if escalation_level.auto_assign and targets else None
        )
        
        # 发送通知
        await self._send_escalation_notifications(alarm, processing, escalation_level, targets)
        
        self.logger.info(f"告警 {alarm.id} 自动升级到级别 {next_level}")
    
    async def _send_sla_warning(
        self,
        alarm: AlarmTable,
        processing: Optional[AlarmProcessing],
        action: Dict[str, Any]
    ):
        """发送SLA预警"""
        if not processing or not processing.sla_deadline:
            return
        
        # 计算剩余时间
        remaining_time = processing.sla_deadline - datetime.utcnow()
        
        # 构建通知消息
        message = f"告警 {alarm.title} 即将超过SLA，剩余时间: {remaining_time}"
        
        # 发送通知
        notify_targets = action.get("notify", [])
        for target in notify_targets:
            if target == "assigned_user" and processing.assigned_to:
                await self.notification_service.send_notification(
                    processing.assigned_to,
                    "SLA预警",
                    message,
                    channels=["email", "slack"]
                )
            elif target == "manager":
                # 发送给管理员
                managers = await self._get_managers()
                for manager_id in managers:
                    await self.notification_service.send_notification(
                        manager_id,
                        "SLA预警",
                        message,
                        channels=["email"]
                    )
        
        self.logger.info(f"告警 {alarm.id} SLA预警已发送")
    
    async def _auto_close(
        self,
        session,
        alarm: AlarmTable,
        processing: Optional[AlarmProcessing],
        action: Dict[str, Any]
    ):
        """自动关闭告警"""
        if processing:
            processing.status = AlarmProcessingStatus.CLOSED
            processing.closed_at = datetime.utcnow()
            processing.closed_by = 0  # 系统用户
            
            # 记录历史
            await self._add_history_record(
                session,
                processing.id,
                0,
                ProcessingActionType.CLOSE,
                notes=action.get("message", "系统自动关闭"),
                new_status=AlarmProcessingStatus.CLOSED
            )
        
        # 更新告警状态
        alarm.status = AlarmStatus.CLOSED
        
        self.logger.info(f"告警 {alarm.id} 自动关闭完成")
    
    async def _auto_assign(
        self,
        session,
        alarm: AlarmTable,
        processing: Optional[AlarmProcessing],
        action: Dict[str, Any]
    ):
        """自动分配告警"""
        # 获取值班人员
        oncall_user = await self.oncall_manager.get_current_oncall_user()
        if not oncall_user:
            self.logger.warning("未找到当前值班人员，无法自动分配")
            return
        
        if not processing:
            # 创建处理记录
            from src.models.alarm_processing import AlarmProcessingCreate
            processing_data = AlarmProcessingCreate(
                priority=self._get_auto_priority(alarm.severity),
                assigned_to=oncall_user.id,
                estimated_effort_hours=1
            )
            
            from src.services.alarm_processing_service import AlarmProcessingService
            service = AlarmProcessingService()
            processing = await service.create_processing(alarm.id, 0, processing_data)
        else:
            # 更新分配
            processing.assigned_to = oncall_user.id
            processing.assigned_by = 0
            processing.assigned_at = datetime.utcnow()
            
            # 记录历史
            await self._add_history_record(
                session,
                processing.id,
                0,
                ProcessingActionType.ASSIGN,
                notes=f"自动分配给值班人员 {oncall_user.username}",
                new_assigned_to=oncall_user.id
            )
        
        self.logger.info(f"告警 {alarm.id} 自动分配给用户 {oncall_user.id}")
    
    async def _get_last_activity_time(self, processing_id: int) -> Optional[datetime]:
        """获取最后活动时间"""
        async with async_session_maker() as session:
            from sqlalchemy import select, desc
            
            query = select(AlarmProcessingHistory.action_at).where(
                AlarmProcessingHistory.processing_id == processing_id
            ).order_by(desc(AlarmProcessingHistory.action_at)).limit(1)
            
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    async def _get_escalation_targets(self, escalation_level: EscalationLevel) -> List[int]:
        """获取升级目标用户"""
        if escalation_level.targets:
            return escalation_level.targets
        
        # 获取当前值班人员
        oncall_users = await self.oncall_manager.get_oncall_users_by_level(escalation_level.level)
        return [user.id for user in oncall_users]
    
    async def _send_escalation_notifications(
        self,
        alarm: AlarmTable,
        processing: AlarmProcessing,
        escalation_level: EscalationLevel,
        targets: List[int]
    ):
        """发送升级通知"""
        message = f"告警已升级到级别 {escalation_level.level}: {alarm.title}"
        
        for user_id in targets:
            await self.notification_service.send_notification(
                user_id,
                f"告警升级 - 级别 {escalation_level.level}",
                message,
                channels=escalation_level.notification_channels
            )
    
    async def _get_managers(self) -> List[int]:
        """获取管理员列表"""
        # 简化实现，返回管理员用户ID列表
        return [1, 2]  # TODO: 从数据库获取实际管理员
    
    def _get_auto_priority(self, severity: str) -> AlarmPriority:
        """根据严重程度获取自动优先级"""
        severity_to_priority = {
            "critical": AlarmPriority.CRITICAL,
            "high": AlarmPriority.HIGH,
            "medium": AlarmPriority.MEDIUM,
            "low": AlarmPriority.LOW,
            "info": AlarmPriority.LOW
        }
        return severity_to_priority.get(severity, AlarmPriority.MEDIUM)
    
    async def _add_history_record(
        self,
        session,
        processing_id: int,
        user_id: int,
        action_type: str,
        notes: str = None,
        **kwargs
    ):
        """添加历史记录"""
        history = AlarmProcessingHistory(
            processing_id=processing_id,
            action_type=action_type,
            action_by=user_id,
            action_at=datetime.utcnow(),
            notes=notes,
            **kwargs
        )
        session.add(history)
    
    # 公共接口方法
    async def trigger_lifecycle_event(
        self,
        alarm_id: int,
        event_type: LifecycleEventType,
        context: Dict[str, Any] = None
    ):
        """触发生命周期事件"""
        self.logger.info(f"触发告警 {alarm_id} 生命周期事件: {event_type.value}")
        
        # 根据事件类型执行相应操作
        if event_type == LifecycleEventType.CREATED:
            await self._handle_alarm_created(alarm_id, context)
        elif event_type == LifecycleEventType.SLA_WARNING:
            await self._handle_sla_warning(alarm_id, context)
        elif event_type == LifecycleEventType.SLA_BREACH:
            await self._handle_sla_breach(alarm_id, context)
    
    async def _handle_alarm_created(self, alarm_id: int, context: Dict[str, Any]):
        """处理告警创建事件"""
        async with async_session_maker() as session:
            alarm = await session.get(AlarmTable, alarm_id)
            if not alarm:
                return
            
            # 根据严重程度自动分配
            if alarm.severity in ["critical", "high"]:
                await self._auto_assign(session, alarm, None, {})
            
            await session.commit()
    
    async def _handle_sla_warning(self, alarm_id: int, context: Dict[str, Any]):
        """处理SLA预警事件"""
        async with async_session_maker() as session:
            alarm = await session.get(AlarmTable, alarm_id)
            processing = alarm.processing[0] if alarm and alarm.processing else None
            
            if alarm and processing:
                await self._send_sla_warning(alarm, processing, {
                    "notify": ["assigned_user", "manager"]
                })
    
    async def _handle_sla_breach(self, alarm_id: int, context: Dict[str, Any]):
        """处理SLA违约事件"""
        async with async_session_maker() as session:
            alarm = await session.get(AlarmTable, alarm_id)
            processing = alarm.processing[0] if alarm and alarm.processing else None
            
            if alarm and processing:
                # 标记SLA违约
                processing.sla_breached = True
                processing.sla_breach_at = datetime.utcnow()
                
                # 自动升级
                await self._auto_escalate(session, alarm, processing, {
                    "escalation_policy": "critical_alerts"
                })
                
                await session.commit()
    
    async def get_lifecycle_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取生命周期统计"""
        async with async_session_maker() as session:
            from sqlalchemy import select, func, and_
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 统计自动化操作
            auto_actions = await session.execute(
                select(
                    AlarmProcessingHistory.action_type,
                    func.count().label('count')
                ).where(
                    and_(
                        AlarmProcessingHistory.action_at >= start_date,
                        AlarmProcessingHistory.action_by == 0  # 系统用户
                    )
                ).group_by(AlarmProcessingHistory.action_type)
            )
            
            automation_stats = {row.action_type: row.count for row in auto_actions}
            
            # SLA统计
            sla_stats = await session.execute(
                select(
                    func.count().label('total'),
                    func.sum(func.case((AlarmProcessing.sla_breached == True, 1), else_=0)).label('breached'),
                    func.avg(
                        func.extract('epoch', AlarmProcessing.sla_deadline - AlarmTable.created_at) / 3600
                    ).label('avg_sla_hours')
                ).select_from(
                    AlarmTable.__table__.join(AlarmProcessing.__table__)
                ).where(
                    AlarmTable.created_at >= start_date
                )
            )
            
            sla_row = sla_stats.first()
            
            return {
                "automation_stats": automation_stats,
                "sla_stats": {
                    "total": sla_row.total or 0,
                    "breached": sla_row.breached or 0,
                    "breach_rate": (sla_row.breached / sla_row.total * 100) if sla_row.total else 0,
                    "avg_sla_hours": sla_row.avg_sla_hours
                },
                "rules_count": len(self.rules),
                "escalation_policies_count": len(self.escalation_policies)
            }


# 全局实例
lifecycle_manager = AlarmLifecycleManager()