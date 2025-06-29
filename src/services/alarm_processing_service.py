"""
告警处理服务
负责告警的确认、分配、处理、解决等全流程管理
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from src.core.database import async_session_maker
from src.core.logging import get_logger
from src.services.alarm_lifecycle_manager import lifecycle_manager, LifecycleEventType
from src.core.exceptions import (
    DatabaseException, ValidationException, 
    ResourceNotFoundException, AuthorizationException
)
from src.models.alarm import AlarmTable, AlarmStatus
from src.models.alarm_processing import (
    AlarmProcessing, AlarmProcessingHistory, AlarmProcessingComment,
    AlarmSLA, ProcessingSolution,
    AlarmProcessingStatus, AlarmPriority, ProcessingActionType, ResolutionMethod,
    AlarmProcessingCreate, AlarmProcessingUpdate, AlarmProcessingAction,
    CommentCreate, AlarmProcessingResponse
)

logger = get_logger(__name__)


class AlarmProcessingService:
    """告警处理服务"""
    
    def __init__(self):
        self.logger = logger
    
    async def create_processing(
        self, 
        alarm_id: int, 
        user_id: int,
        processing_data: AlarmProcessingCreate
    ) -> AlarmProcessing:
        """创建告警处理记录"""
        async with async_session_maker() as session:
            try:
                # 验证告警存在
                alarm = await session.get(AlarmTable, alarm_id)
                if not alarm:
                    raise ResourceNotFoundException("Alarm", alarm_id)
                
                # 检查是否已有处理记录
                existing = await session.execute(
                    select(AlarmProcessing).where(AlarmProcessing.alarm_id == alarm_id)
                )
                if existing.scalar_one_or_none():
                    raise ValidationException(
                        "Alarm processing already exists", 
                        details={"alarm_id": alarm_id}
                    )
                
                # 计算SLA截止时间
                sla_deadline = await self._calculate_sla_deadline(
                    processing_data.priority, 
                    alarm.severity
                )
                
                # 创建处理记录
                processing = AlarmProcessing(
                    alarm_id=alarm_id,
                    status=AlarmProcessingStatus.PENDING,
                    priority=processing_data.priority,
                    assigned_to=processing_data.assigned_to,
                    assigned_by=user_id if processing_data.assigned_to else None,
                    assigned_at=datetime.utcnow() if processing_data.assigned_to else None,
                    estimated_effort_hours=processing_data.estimated_effort_hours,
                    impact_level=processing_data.impact_level,
                    business_impact=processing_data.business_impact,
                    sla_deadline=sla_deadline,
                    tags=processing_data.tags,
                    processing_metadata={
                        "created_by": user_id,
                        "initial_severity": alarm.severity,
                        "initial_status": alarm.status
                    }
                )
                
                session.add(processing)
                await session.flush()
                
                # 记录处理历史
                await self._add_history_record(
                    session, 
                    processing.id, 
                    user_id,
                    ProcessingActionType.ASSIGN if processing_data.assigned_to else "create",
                    notes=f"创建处理记录，优先级: {processing_data.priority}",
                    new_status=AlarmProcessingStatus.PENDING,
                    new_assigned_to=processing_data.assigned_to
                )
                
                # 更新告警状态
                if alarm.status == AlarmStatus.ACTIVE:
                    alarm.status = AlarmStatus.ACKNOWLEDGED
                    alarm.acknowledged_at = datetime.utcnow()
                
                await session.commit()
                
                # 触发生命周期事件
                await lifecycle_manager.trigger_lifecycle_event(
                    alarm_id, 
                    LifecycleEventType.CREATED,
                    {"processing_id": processing.id, "priority": processing_data.priority}
                )
                
                self.logger.info(
                    f"Created alarm processing for alarm {alarm_id}",
                    extra={
                        "alarm_id": alarm_id,
                        "processing_id": processing.id,
                        "user_id": user_id,
                        "priority": processing_data.priority
                    }
                )
                
                return processing
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, (ValidationException, ResourceNotFoundException)):
                    raise
                raise DatabaseException(f"Failed to create alarm processing: {str(e)}")
    
    async def acknowledge_alarm(
        self, 
        processing_id: int, 
        user_id: int, 
        note: Optional[str] = None
    ) -> AlarmProcessing:
        """确认告警"""
        async with async_session_maker() as session:
            try:
                processing = await self._get_processing_with_check(session, processing_id, user_id)
                
                if processing.status != AlarmProcessingStatus.PENDING:
                    raise ValidationException(
                        "Alarm can only be acknowledged when pending",
                        details={"current_status": processing.status}
                    )
                
                # 更新处理状态
                processing.status = AlarmProcessingStatus.ACKNOWLEDGED
                processing.acknowledged_by = user_id
                processing.acknowledged_at = datetime.utcnow()
                processing.acknowledgment_note = note
                processing.response_time_minutes = self._calculate_response_time(processing)
                
                # 记录历史
                await self._add_history_record(
                    session,
                    processing_id,
                    user_id,
                    ProcessingActionType.ACKNOWLEDGE,
                    old_status=AlarmProcessingStatus.PENDING,
                    new_status=AlarmProcessingStatus.ACKNOWLEDGED,
                    notes=note
                )
                
                # 更新告警状态
                alarm = await session.get(AlarmTable, processing.alarm_id)
                if alarm:
                    alarm.status = AlarmStatus.ACKNOWLEDGED
                    alarm.acknowledged_at = processing.acknowledged_at
                
                await session.commit()
                
                # 触发生命周期事件
                await lifecycle_manager.trigger_lifecycle_event(
                    processing.alarm_id,
                    LifecycleEventType.ACKNOWLEDGED,
                    {"processing_id": processing_id, "response_time": processing.response_time_minutes}
                )
                
                self.logger.info(
                    f"Acknowledged alarm processing {processing_id}",
                    extra={
                        "processing_id": processing_id,
                        "user_id": user_id,
                        "response_time": processing.response_time_minutes
                    }
                )
                
                return processing
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, (ValidationException, ResourceNotFoundException, AuthorizationException)):
                    raise
                raise DatabaseException(f"Failed to acknowledge alarm: {str(e)}")
    
    async def assign_alarm(
        self, 
        processing_id: int, 
        user_id: int, 
        assigned_to: int,
        notes: Optional[str] = None
    ) -> AlarmProcessing:
        """分配告警"""
        async with async_session_maker() as session:
            try:
                processing = await self._get_processing_with_check(session, processing_id, user_id)
                
                old_assigned_to = processing.assigned_to
                
                # 更新分配信息
                processing.assigned_to = assigned_to
                processing.assigned_by = user_id
                processing.assigned_at = datetime.utcnow()
                
                # 如果状态还是待处理，自动设为已确认
                if processing.status == AlarmProcessingStatus.PENDING:
                    processing.status = AlarmProcessingStatus.ACKNOWLEDGED
                    processing.acknowledged_by = user_id
                    processing.acknowledged_at = datetime.utcnow()
                
                # 记录历史
                await self._add_history_record(
                    session,
                    processing_id,
                    user_id,
                    ProcessingActionType.ASSIGN,
                    old_assigned_to=old_assigned_to,
                    new_assigned_to=assigned_to,
                    notes=notes or f"分配给用户 ID: {assigned_to}"
                )
                
                await session.commit()
                
                # 触发生命周期事件
                await lifecycle_manager.trigger_lifecycle_event(
                    processing.alarm_id,
                    LifecycleEventType.ASSIGNED,
                    {"processing_id": processing_id, "assigned_to": assigned_to}
                )
                
                self.logger.info(
                    f"Assigned alarm processing {processing_id} to user {assigned_to}",
                    extra={
                        "processing_id": processing_id,
                        "assigned_by": user_id,
                        "assigned_to": assigned_to
                    }
                )
                
                return processing
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, (ValidationException, ResourceNotFoundException, AuthorizationException)):
                    raise
                raise DatabaseException(f"Failed to assign alarm: {str(e)}")
    
    async def update_status(
        self, 
        processing_id: int, 
        user_id: int, 
        new_status: AlarmProcessingStatus,
        notes: Optional[str] = None
    ) -> AlarmProcessing:
        """更新处理状态"""
        async with async_session_maker() as session:
            try:
                processing = await self._get_processing_with_check(session, processing_id, user_id)
                
                old_status = processing.status
                
                # 验证状态转换的合法性
                if not self._is_valid_status_transition(old_status, new_status):
                    raise ValidationException(
                        f"Invalid status transition from {old_status} to {new_status}",
                        details={"old_status": old_status, "new_status": new_status}
                    )
                
                # 更新状态
                processing.status = new_status
                
                # 如果状态变为处理中，记录开始时间
                if new_status == AlarmProcessingStatus.IN_PROGRESS and not processing.acknowledged_at:
                    processing.acknowledged_by = user_id
                    processing.acknowledged_at = datetime.utcnow()
                
                # 记录历史
                await self._add_history_record(
                    session,
                    processing_id,
                    user_id,
                    ProcessingActionType.UPDATE_STATUS,
                    old_status=old_status,
                    new_status=new_status,
                    notes=notes
                )
                
                await session.commit()
                
                # 触发生命周期事件
                if new_status == AlarmProcessingStatus.IN_PROGRESS:
                    await lifecycle_manager.trigger_lifecycle_event(
                        processing.alarm_id,
                        LifecycleEventType.IN_PROGRESS,
                        {"processing_id": processing_id, "old_status": old_status.value, "new_status": new_status.value}
                    )
                
                self.logger.info(
                    f"Updated status for processing {processing_id}: {old_status} -> {new_status}",
                    extra={
                        "processing_id": processing_id,
                        "user_id": user_id,
                        "old_status": old_status,
                        "new_status": new_status
                    }
                )
                
                return processing
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, (ValidationException, ResourceNotFoundException, AuthorizationException)):
                    raise
                raise DatabaseException(f"Failed to update status: {str(e)}")
    
    async def resolve_alarm(
        self, 
        processing_id: int, 
        user_id: int,
        resolution_method: ResolutionMethod,
        resolution_note: str,
        actual_effort_hours: Optional[int] = None
    ) -> AlarmProcessing:
        """解决告警"""
        async with async_session_maker() as session:
            try:
                processing = await self._get_processing_with_check(session, processing_id, user_id)
                
                if processing.status in [AlarmProcessingStatus.RESOLVED, AlarmProcessingStatus.CLOSED]:
                    raise ValidationException(
                        "Alarm already resolved or closed",
                        details={"current_status": processing.status}
                    )
                
                # 更新解决信息
                processing.status = AlarmProcessingStatus.RESOLVED
                processing.resolved_by = user_id
                processing.resolved_at = datetime.utcnow()
                processing.resolution_method = resolution_method
                processing.resolution_note = resolution_note
                processing.actual_effort_hours = actual_effort_hours
                processing.resolution_time_minutes = self._calculate_resolution_time(processing)
                
                # 记录历史
                await self._add_history_record(
                    session,
                    processing_id,
                    user_id,
                    ProcessingActionType.RESOLVE,
                    new_status=AlarmProcessingStatus.RESOLVED,
                    notes=f"解决方法: {resolution_method}, 说明: {resolution_note}"
                )
                
                # 更新告警状态
                alarm = await session.get(AlarmTable, processing.alarm_id)
                if alarm:
                    alarm.status = AlarmStatus.RESOLVED
                    alarm.resolved_at = processing.resolved_at
                
                await session.commit()
                
                # 触发生命周期事件
                await lifecycle_manager.trigger_lifecycle_event(
                    processing.alarm_id,
                    LifecycleEventType.RESOLVED,
                    {
                        "processing_id": processing_id,
                        "resolution_method": resolution_method.value,
                        "resolution_time": processing.resolution_time_minutes
                    }
                )
                
                self.logger.info(
                    f"Resolved alarm processing {processing_id}",
                    extra={
                        "processing_id": processing_id,
                        "user_id": user_id,
                        "resolution_method": resolution_method,
                        "resolution_time": processing.resolution_time_minutes
                    }
                )
                
                return processing
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, (ValidationException, ResourceNotFoundException, AuthorizationException)):
                    raise
                raise DatabaseException(f"Failed to resolve alarm: {str(e)}")
    
    async def escalate_alarm(
        self, 
        processing_id: int, 
        user_id: int,
        escalated_to: int,
        escalation_reason: str
    ) -> AlarmProcessing:
        """升级告警"""
        async with async_session_maker() as session:
            try:
                processing = await self._get_processing_with_check(session, processing_id, user_id)
                
                # 更新升级信息
                processing.status = AlarmProcessingStatus.ESCALATED
                processing.escalated_to = escalated_to
                processing.escalated_by = user_id
                processing.escalated_at = datetime.utcnow()
                processing.escalation_reason = escalation_reason
                processing.escalation_level += 1
                
                # 重新分配
                processing.assigned_to = escalated_to
                processing.assigned_by = user_id
                processing.assigned_at = datetime.utcnow()
                
                # 提升优先级
                if processing.priority == AlarmPriority.P4:
                    processing.priority = AlarmPriority.P3
                elif processing.priority == AlarmPriority.P3:
                    processing.priority = AlarmPriority.P2
                elif processing.priority == AlarmPriority.P2:
                    processing.priority = AlarmPriority.P1
                
                # 记录历史
                await self._add_history_record(
                    session,
                    processing_id,
                    user_id,
                    ProcessingActionType.ESCALATE,
                    new_status=AlarmProcessingStatus.ESCALATED,
                    new_assigned_to=escalated_to,
                    notes=f"升级原因: {escalation_reason}, 升级级别: {processing.escalation_level}"
                )
                
                await session.commit()
                
                # 触发生命周期事件
                await lifecycle_manager.trigger_lifecycle_event(
                    processing.alarm_id,
                    LifecycleEventType.ESCALATED,
                    {
                        "processing_id": processing_id,
                        "escalated_to": escalated_to,
                        "escalation_level": processing.escalation_level,
                        "reason": escalation_reason
                    }
                )
                
                self.logger.warning(
                    f"Escalated alarm processing {processing_id} to user {escalated_to}",
                    extra={
                        "processing_id": processing_id,
                        "escalated_by": user_id,
                        "escalated_to": escalated_to,
                        "escalation_level": processing.escalation_level,
                        "reason": escalation_reason
                    }
                )
                
                return processing
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, (ValidationException, ResourceNotFoundException, AuthorizationException)):
                    raise
                raise DatabaseException(f"Failed to escalate alarm: {str(e)}")
    
    async def add_comment(
        self, 
        processing_id: int, 
        user_id: int,
        comment_data: CommentCreate
    ) -> AlarmProcessingComment:
        """添加处理评论"""
        async with async_session_maker() as session:
            try:
                # 验证处理记录存在
                processing = await session.get(AlarmProcessing, processing_id)
                if not processing:
                    raise ResourceNotFoundException("AlarmProcessing", processing_id)
                
                # 获取用户信息
                from src.models.alarm import User
                user = await session.get(User, user_id)
                if not user:
                    raise ResourceNotFoundException("User", user_id)
                
                # 创建评论
                comment = AlarmProcessingComment(
                    processing_id=processing_id,
                    content=comment_data.content,
                    comment_type=comment_data.comment_type,
                    author_id=user_id,
                    author_name=user.full_name or user.username,
                    visibility=comment_data.visibility,
                    attachments=comment_data.attachments
                )
                
                session.add(comment)
                
                # 记录历史
                await self._add_history_record(
                    session,
                    processing_id,
                    user_id,
                    ProcessingActionType.COMMENT,
                    notes=f"添加评论: {comment_data.content[:50]}..."
                )
                
                await session.commit()
                
                self.logger.info(
                    f"Added comment to processing {processing_id}",
                    extra={
                        "processing_id": processing_id,
                        "user_id": user_id,
                        "comment_type": comment_data.comment_type
                    }
                )
                
                return comment
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, (ValidationException, ResourceNotFoundException)):
                    raise
                raise DatabaseException(f"Failed to add comment: {str(e)}")
    
    async def get_processing_by_alarm(self, alarm_id: int) -> Optional[AlarmProcessing]:
        """根据告警ID获取处理记录"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(AlarmProcessing)
                    .where(AlarmProcessing.alarm_id == alarm_id)
                    .options(
                        selectinload(AlarmProcessing.processing_history),
                        selectinload(AlarmProcessing.comments)
                    )
                )
                return result.scalar_one_or_none()
            except Exception as e:
                raise DatabaseException(f"Failed to get processing: {str(e)}")
    
    async def get_user_assignments(
        self, 
        user_id: int, 
        status_filter: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AlarmProcessing]:
        """获取用户分配的处理任务"""
        async with async_session_maker() as session:
            try:
                query = select(AlarmProcessing).where(
                    AlarmProcessing.assigned_to == user_id
                )
                
                if status_filter:
                    query = query.where(AlarmProcessing.status.in_(status_filter))
                
                query = query.order_by(desc(AlarmProcessing.created_at))
                query = query.limit(limit).offset(offset)
                
                result = await session.execute(query)
                return result.scalars().all()
            except Exception as e:
                raise DatabaseException(f"Failed to get user assignments: {str(e)}")
    
    # 私有方法
    async def _get_processing_with_check(
        self, 
        session: AsyncSession, 
        processing_id: int, 
        user_id: int
    ) -> AlarmProcessing:
        """获取处理记录并检查权限"""
        processing = await session.get(AlarmProcessing, processing_id)
        if not processing:
            raise ResourceNotFoundException("AlarmProcessing", processing_id)
        
        # 检查用户权限（简化版本：用户可以操作分配给自己的或自己创建的）
        if (processing.assigned_to != user_id and 
            processing.processing_metadata.get("created_by") != user_id):
            # 这里可以添加更复杂的权限检查逻辑
            pass
        
        return processing
    
    async def _add_history_record(
        self,
        session: AsyncSession,
        processing_id: int,
        user_id: int,
        action_type: str,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        old_assigned_to: Optional[int] = None,
        new_assigned_to: Optional[int] = None,
        notes: Optional[str] = None
    ):
        """添加历史记录"""
        history = AlarmProcessingHistory(
            processing_id=processing_id,
            action_type=action_type,
            action_by=user_id,
            old_status=old_status,
            new_status=new_status,
            old_assigned_to=old_assigned_to,
            new_assigned_to=new_assigned_to,
            notes=notes
        )
        session.add(history)
    
    def _is_valid_status_transition(
        self, 
        old_status: AlarmProcessingStatus, 
        new_status: AlarmProcessingStatus
    ) -> bool:
        """验证状态转换是否合法"""
        # 定义合法的状态转换
        valid_transitions = {
            AlarmProcessingStatus.PENDING: [
                AlarmProcessingStatus.ACKNOWLEDGED,
                AlarmProcessingStatus.INVESTIGATING,
                AlarmProcessingStatus.IN_PROGRESS,
                AlarmProcessingStatus.ESCALATED
            ],
            AlarmProcessingStatus.ACKNOWLEDGED: [
                AlarmProcessingStatus.INVESTIGATING,
                AlarmProcessingStatus.IN_PROGRESS,
                AlarmProcessingStatus.WAITING,
                AlarmProcessingStatus.ESCALATED
            ],
            AlarmProcessingStatus.INVESTIGATING: [
                AlarmProcessingStatus.IN_PROGRESS,
                AlarmProcessingStatus.WAITING,
                AlarmProcessingStatus.RESOLVED,
                AlarmProcessingStatus.ESCALATED
            ],
            AlarmProcessingStatus.IN_PROGRESS: [
                AlarmProcessingStatus.WAITING,
                AlarmProcessingStatus.RESOLVED,
                AlarmProcessingStatus.ESCALATED
            ],
            AlarmProcessingStatus.WAITING: [
                AlarmProcessingStatus.IN_PROGRESS,
                AlarmProcessingStatus.RESOLVED,
                AlarmProcessingStatus.ESCALATED
            ],
            AlarmProcessingStatus.RESOLVED: [
                AlarmProcessingStatus.CLOSED,
                AlarmProcessingStatus.IN_PROGRESS  # 可以重新打开
            ],
            AlarmProcessingStatus.ESCALATED: [
                AlarmProcessingStatus.ACKNOWLEDGED,
                AlarmProcessingStatus.IN_PROGRESS,
                AlarmProcessingStatus.RESOLVED
            ]
        }
        
        return new_status in valid_transitions.get(old_status, [])
    
    async def _calculate_sla_deadline(
        self, 
        priority: AlarmPriority, 
        severity: str
    ) -> Optional[datetime]:
        """计算SLA截止时间"""
        # 简化的SLA计算逻辑
        sla_hours = {
            AlarmPriority.P1: 1,   # 1小时
            AlarmPriority.P2: 4,   # 4小时
            AlarmPriority.P3: 24,  # 24小时
            AlarmPriority.P4: 72   # 72小时
        }
        
        hours = sla_hours.get(priority, 24)
        return datetime.utcnow() + timedelta(hours=hours)
    
    def _calculate_response_time(self, processing: AlarmProcessing) -> Optional[int]:
        """计算响应时间（分钟）"""
        if processing.acknowledged_at and processing.created_at:
            delta = processing.acknowledged_at - processing.created_at
            return int(delta.total_seconds() / 60)
        return None
    
    def _calculate_resolution_time(self, processing: AlarmProcessing) -> Optional[int]:
        """计算解决时间（分钟）"""
        if processing.resolved_at and processing.created_at:
            delta = processing.resolved_at - processing.created_at
            return int(delta.total_seconds() / 60)
        return None