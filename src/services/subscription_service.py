"""
告警订阅管理服务
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from src.core.database import async_session_maker
from src.core.logging import get_logger
from src.core.exceptions import (
    DatabaseException, ValidationException,
    ResourceNotFoundException, AuthorizationException
)
from src.models.alarm import (
    AlarmTable, UserSubscription, NotificationTemplate, NotificationLog
)

logger = get_logger(__name__)


class SubscriptionService:
    """订阅管理服务"""
    
    def __init__(self):
        self.logger = logger
    
    async def create_subscription(
        self, 
        user_id: int,
        subscription_data: SubscriptionCreate
    ) -> AlarmSubscription:
        """创建告警订阅"""
        async with async_session_maker() as session:
            try:
                # 验证过滤条件格式
                self._validate_filter_conditions(subscription_data.filter_conditions)
                
                # 验证通知渠道配置
                await self._validate_notification_channels(session, subscription_data.notification_channels)
                
                # 创建订阅
                subscription = AlarmSubscription(
                    name=subscription_data.name,
                    description=subscription_data.description,
                    user_id=user_id,
                    subscription_type=subscription_data.subscription_type,
                    filter_conditions=subscription_data.filter_conditions,
                    notification_channels=subscription_data.notification_channels,
                    notification_template_id=subscription_data.notification_template_id,
                    schedule_config=subscription_data.schedule_config,
                    quiet_hours=subscription_data.quiet_hours,
                    rate_limit_config=subscription_data.rate_limit_config,
                    tags=subscription_data.tags
                )
                
                session.add(subscription)
                await session.commit()
                
                self.logger.info(
                    f"Created subscription: {subscription.name}",
                    extra={
                        "subscription_id": subscription.id,
                        "user_id": user_id,
                        "subscription_type": subscription_data.subscription_type
                    }
                )
                
                return subscription
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, ValidationException):
                    raise
                raise DatabaseException(f"Failed to create subscription: {str(e)}")
    
    async def update_subscription(
        self,
        subscription_id: int,
        user_id: int,
        update_data: SubscriptionUpdate
    ) -> AlarmSubscription:
        """更新订阅"""
        async with async_session_maker() as session:
            try:
                subscription = await self._get_subscription_with_permission(
                    session, subscription_id, user_id
                )
                
                # 更新字段
                if update_data.name is not None:
                    subscription.name = update_data.name
                if update_data.description is not None:
                    subscription.description = update_data.description
                if update_data.subscription_type is not None:
                    subscription.subscription_type = update_data.subscription_type
                if update_data.filter_conditions is not None:
                    self._validate_filter_conditions(update_data.filter_conditions)
                    subscription.filter_conditions = update_data.filter_conditions
                if update_data.notification_channels is not None:
                    await self._validate_notification_channels(session, update_data.notification_channels)
                    subscription.notification_channels = update_data.notification_channels
                if update_data.notification_template_id is not None:
                    subscription.notification_template_id = update_data.notification_template_id
                if update_data.schedule_config is not None:
                    subscription.schedule_config = update_data.schedule_config
                if update_data.quiet_hours is not None:
                    subscription.quiet_hours = update_data.quiet_hours
                if update_data.rate_limit_config is not None:
                    subscription.rate_limit_config = update_data.rate_limit_config
                if update_data.enabled is not None:
                    subscription.enabled = update_data.enabled
                if update_data.tags is not None:
                    subscription.tags = update_data.tags
                
                subscription.updated_at = datetime.utcnow()
                
                await session.commit()
                
                self.logger.info(
                    f"Updated subscription {subscription_id}",
                    extra={"subscription_id": subscription_id, "user_id": user_id}
                )
                
                return subscription
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, (ValidationException, ResourceNotFoundException, AuthorizationException)):
                    raise
                raise DatabaseException(f"Failed to update subscription: {str(e)}")
    
    async def delete_subscription(self, subscription_id: int, user_id: int):
        """删除订阅"""
        async with async_session_maker() as session:
            try:
                subscription = await self._get_subscription_with_permission(
                    session, subscription_id, user_id
                )
                
                await session.delete(subscription)
                await session.commit()
                
                self.logger.info(
                    f"Deleted subscription {subscription_id}",
                    extra={"subscription_id": subscription_id, "user_id": user_id}
                )
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, (ResourceNotFoundException, AuthorizationException)):
                    raise
                raise DatabaseException(f"Failed to delete subscription: {str(e)}")
    
    async def get_user_subscriptions(
        self,
        user_id: int,
        enabled_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[AlarmSubscription]:
        """获取用户订阅列表"""
        async with async_session_maker() as session:
            try:
                query = select(AlarmSubscription).where(
                    AlarmSubscription.user_id == user_id
                )
                
                if enabled_only:
                    query = query.where(AlarmSubscription.enabled == True)
                
                query = query.order_by(desc(AlarmSubscription.created_at))
                query = query.limit(limit).offset(offset)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                raise DatabaseException(f"Failed to get user subscriptions: {str(e)}")
    
    async def test_subscription_filter(
        self,
        filter_conditions: Dict[str, Any],
        alarm_data: Dict[str, Any]
    ) -> bool:
        """测试订阅过滤条件"""
        try:
            return self._match_filter_conditions(filter_conditions, alarm_data)
        except Exception as e:
            self.logger.error(f"Error testing filter conditions: {str(e)}")
            return False
    
    async def find_matching_subscriptions(
        self,
        alarm: AlarmTable
    ) -> List[AlarmSubscription]:
        """查找匹配告警的订阅"""
        async with async_session_maker() as session:
            try:
                # 获取所有启用的订阅
                query = select(AlarmSubscription).where(
                    AlarmSubscription.enabled == True
                ).options(selectinload(AlarmSubscription.user))
                
                result = await session.execute(query)
                all_subscriptions = result.scalars().all()
                
                # 转换告警为字典用于匹配
                alarm_data = {
                    "id": alarm.id,
                    "source": alarm.source,
                    "title": alarm.title,
                    "description": alarm.description,
                    "severity": alarm.severity,
                    "status": alarm.status,
                    "category": alarm.category,
                    "host": alarm.host,
                    "service": alarm.service,
                    "environment": alarm.environment,
                    "tags": alarm.tags or {},
                    "created_at": alarm.created_at.isoformat()
                }
                
                # 过滤匹配的订阅
                matching_subscriptions = []
                for subscription in all_subscriptions:
                    try:
                        if self._match_filter_conditions(subscription.filter_conditions, alarm_data):
                            # 检查静默时段
                            if not self._is_in_quiet_hours(subscription):
                                # 检查限流
                                if await self._check_rate_limit(session, subscription):
                                    matching_subscriptions.append(subscription)
                    except Exception as e:
                        self.logger.error(
                            f"Error checking subscription {subscription.id}: {str(e)}",
                            extra={"subscription_id": subscription.id}
                        )
                        continue
                
                self.logger.info(
                    f"Found {len(matching_subscriptions)} matching subscriptions for alarm {alarm.id}",
                    extra={"alarm_id": alarm.id, "matches": len(matching_subscriptions)}
                )
                
                return matching_subscriptions
                
            except Exception as e:
                raise DatabaseException(f"Failed to find matching subscriptions: {str(e)}")
    
    async def create_notifications(
        self,
        alarm: AlarmTable,
        subscriptions: List[AlarmSubscription]
    ) -> List[AlarmNotification]:
        """为匹配的订阅创建通知"""
        async with async_session_maker() as session:
            try:
                notifications = []
                
                for subscription in subscriptions:
                    # 根据订阅类型处理
                    if subscription.subscription_type == SubscriptionType.IMMEDIATE:
                        # 立即通知
                        for channel_config in subscription.notification_channels:
                            notification = await self._create_immediate_notification(
                                session, alarm, subscription, channel_config
                            )
                            if notification:
                                notifications.append(notification)
                    
                    elif subscription.subscription_type == SubscriptionType.DIGEST:
                        # 摘要通知 - 稍后由调度器处理
                        await self._schedule_digest_notification(session, alarm, subscription)
                    
                    # 更新订阅统计
                    subscription.total_notifications += len([n for n in notifications if n.subscription_id == subscription.id])
                    subscription.last_notification_at = datetime.utcnow()
                
                await session.commit()
                
                self.logger.info(
                    f"Created {len(notifications)} notifications for alarm {alarm.id}",
                    extra={"alarm_id": alarm.id, "notification_count": len(notifications)}
                )
                
                return notifications
                
            except Exception as e:
                await session.rollback()
                raise DatabaseException(f"Failed to create notifications: {str(e)}")
    
    async def get_notification_history(
        self,
        user_id: int,
        days: int = 30,
        status_filter: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AlarmNotification]:
        """获取通知历史"""
        async with async_session_maker() as session:
            try:
                start_date = datetime.utcnow() - timedelta(days=days)
                
                query = select(AlarmNotification).where(
                    and_(
                        AlarmNotification.user_id == user_id,
                        AlarmNotification.created_at >= start_date
                    )
                ).options(
                    selectinload(AlarmNotification.alarm),
                    selectinload(AlarmNotification.subscription)
                )
                
                if status_filter:
                    query = query.where(AlarmNotification.status.in_(status_filter))
                
                query = query.order_by(desc(AlarmNotification.created_at))
                query = query.limit(limit).offset(offset)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                raise DatabaseException(f"Failed to get notification history: {str(e)}")
    
    # 私有方法
    
    def _validate_filter_conditions(self, conditions: Dict[str, Any]):
        """验证过滤条件格式"""
        required_fields = ["field", "operator", "value"]
        
        if not isinstance(conditions, dict):
            raise ValidationException("Filter conditions must be a dictionary")
        
        # 这里可以添加更复杂的验证逻辑
        # 例如验证字段名、操作符等是否合法
    
    async def _validate_notification_channels(
        self, 
        session: AsyncSession,
        channels: List[Dict[str, Any]]
    ):
        """验证通知渠道配置"""
        for channel in channels:
            if "channel_type" not in channel:
                raise ValidationException("Channel type is required")
            
            if "recipient" not in channel:
                raise ValidationException("Recipient is required")
    
    async def _get_subscription_with_permission(
        self,
        session: AsyncSession,
        subscription_id: int,
        user_id: int
    ) -> AlarmSubscription:
        """获取订阅并检查权限"""
        subscription = await session.get(AlarmSubscription, subscription_id)
        if not subscription:
            raise ResourceNotFoundException("AlarmSubscription", subscription_id)
        
        # 检查权限：用户只能操作自己的订阅
        if subscription.user_id != user_id:
            raise AuthorizationException("You can only access your own subscriptions")
        
        return subscription
    
    def _match_filter_conditions(
        self, 
        conditions: Dict[str, Any], 
        alarm_data: Dict[str, Any]
    ) -> bool:
        """匹配过滤条件"""
        try:
            # 简化的匹配逻辑
            # 实际实现可以支持更复杂的条件组合
            
            if "operator" in conditions:
                # 单个条件
                return self._evaluate_condition(conditions, alarm_data)
            
            if "and" in conditions:
                # AND 条件组合
                return all(
                    self._match_filter_conditions(cond, alarm_data)
                    for cond in conditions["and"]
                )
            
            if "or" in conditions:
                # OR 条件组合
                return any(
                    self._match_filter_conditions(cond, alarm_data)
                    for cond in conditions["or"]
                )
            
            # 默认匹配所有
            return True
            
        except Exception as e:
            self.logger.error(f"Error matching filter conditions: {str(e)}")
            return False
    
    def _evaluate_condition(
        self, 
        condition: Dict[str, Any], 
        alarm_data: Dict[str, Any]
    ) -> bool:
        """评估单个条件"""
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        
        if not all([field, operator, value is not None]):
            return False
        
        alarm_value = alarm_data.get(field)
        if alarm_value is None:
            return False
        
        # 根据操作符进行匹配
        if operator == "equals":
            return alarm_value == value
        elif operator == "not_equals":
            return alarm_value != value
        elif operator == "contains":
            return str(value).lower() in str(alarm_value).lower()
        elif operator == "not_contains":
            return str(value).lower() not in str(alarm_value).lower()
        elif operator == "in":
            return alarm_value in value if isinstance(value, list) else False
        elif operator == "not_in":
            return alarm_value not in value if isinstance(value, list) else True
        elif operator == "regex":
            import re
            try:
                return bool(re.search(str(value), str(alarm_value), re.IGNORECASE))
            except:
                return False
        elif operator == "greater_than":
            try:
                return float(alarm_value) > float(value)
            except:
                return False
        elif operator == "less_than":
            try:
                return float(alarm_value) < float(value)
            except:
                return False
        
        return False
    
    def _is_in_quiet_hours(self, subscription: AlarmSubscription) -> bool:
        """检查是否在静默时段"""
        if not subscription.quiet_hours:
            return False
        
        # 这里可以实现复杂的静默时段逻辑
        # 例如工作时间、节假日等
        current_time = datetime.utcnow()
        
        # 简化实现：检查每日静默时段
        if "daily" in subscription.quiet_hours:
            daily_config = subscription.quiet_hours["daily"]
            start_hour = daily_config.get("start_hour", 0)
            end_hour = daily_config.get("end_hour", 0)
            
            current_hour = current_time.hour
            if start_hour <= end_hour:
                return start_hour <= current_hour <= end_hour
            else:  # 跨日情况
                return current_hour >= start_hour or current_hour <= end_hour
        
        return False
    
    async def _check_rate_limit(
        self, 
        session: AsyncSession,
        subscription: AlarmSubscription
    ) -> bool:
        """检查限流"""
        if not subscription.rate_limit_config:
            return True
        
        # 简化的限流检查
        limit_per_hour = subscription.rate_limit_config.get("per_hour", 100)
        
        # 查询最近一小时的通知数量
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        count_query = select(func.count(AlarmNotification.id)).where(
            and_(
                AlarmNotification.subscription_id == subscription.id,
                AlarmNotification.created_at >= one_hour_ago
            )
        )
        
        result = await session.execute(count_query)
        recent_count = result.scalar()
        
        return recent_count < limit_per_hour
    
    async def _create_immediate_notification(
        self,
        session: AsyncSession,
        alarm: AlarmTable,
        subscription: AlarmSubscription,
        channel_config: Dict[str, Any]
    ) -> Optional[AlarmNotification]:
        """创建立即通知"""
        try:
            # 确定优先级
            priority = self._determine_priority(alarm.severity)
            
            # 创建通知记录
            notification = AlarmNotification(
                alarm_id=alarm.id,
                subscription_id=subscription.id,
                user_id=subscription.user_id,
                notification_type="immediate",
                channel=channel_config["channel_type"],
                recipient=channel_config["recipient"],
                subject=f"告警通知: {alarm.title}",
                content=f"告警详情:\n标题: {alarm.title}\n严重程度: {alarm.severity}\n描述: {alarm.description}",
                status=NotificationStatus.PENDING,
                priority=priority,
                scheduled_at=datetime.utcnow(),
                notification_config=channel_config
            )
            
            session.add(notification)
            return notification
            
        except Exception as e:
            self.logger.error(f"Error creating immediate notification: {str(e)}")
            return None
    
    async def _schedule_digest_notification(
        self,
        session: AsyncSession,
        alarm: AlarmTable,
        subscription: AlarmSubscription
    ):
        """安排摘要通知"""
        # 这里可以实现摘要通知的调度逻辑
        # 例如将告警添加到待处理的摘要队列中
        pass
    
    def _determine_priority(self, severity: str) -> str:
        """根据严重程度确定通知优先级"""
        severity_priority_map = {
            "critical": NotificationPriority.URGENT,
            "high": NotificationPriority.HIGH,
            "medium": NotificationPriority.NORMAL,
            "low": NotificationPriority.LOW,
            "info": NotificationPriority.LOW
        }
        return severity_priority_map.get(severity, NotificationPriority.NORMAL)