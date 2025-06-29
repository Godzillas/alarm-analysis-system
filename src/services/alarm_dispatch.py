"""
告警分发服务
负责将新创建的告警分发给匹配的订阅，并触发通知
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import async_session_maker
from src.utils.logger import get_logger
from src.models.alarm import AlarmTable, UserSubscription, NotificationLog
# from src.services.subscription_service import subscription_service  # Not needed, using direct model access
from src.services.notification_service import notification_service

logger = get_logger(__name__)


class AlarmDispatchService:
    """告警分发服务"""
    
    def __init__(self):
        self.logger = logger
        self._running = False
        self._dispatch_queue = asyncio.Queue()
        self._worker_task = None
    
    async def start(self):
        """启动分发服务"""
        if self._running:
            return
        
        self._running = True
        self._worker_task = asyncio.create_task(self._dispatch_worker())
        self.logger.info("告警分发服务已启动")
    
    async def stop(self):
        """停止分发服务"""
        if not self._running:
            return
        
        self._running = False
        
        # 等待队列处理完成
        await self._dispatch_queue.join()
        
        # 取消工作任务
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("告警分发服务已停止")
    
    async def dispatch_alarm(self, alarm_id: int, is_update: bool = False):
        """分发告警到订阅队列"""
        await self._dispatch_queue.put((alarm_id, is_update))
        self.logger.debug(f"告警 {alarm_id} 已加入分发队列")
    
    async def _dispatch_worker(self):
        """分发工作协程"""
        while self._running:
            try:
                # 等待队列中的告警
                alarm_id, is_update = await asyncio.wait_for(
                    self._dispatch_queue.get(), 
                    timeout=1.0
                )
                
                # 处理告警分发
                await self._process_alarm_dispatch(alarm_id, is_update)
                
                # 标记任务完成
                self._dispatch_queue.task_done()
                
            except asyncio.TimeoutError:
                # 超时继续循环
                continue
            except Exception as e:
                self.logger.error(f"告警分发处理错误: {str(e)}")
                # 如果有待处理的任务，标记为完成
                try:
                    self._dispatch_queue.task_done()
                except ValueError:
                    pass
    
    async def _process_alarm_dispatch(self, alarm_id: int, is_update: bool):
        """处理单个告警的分发"""
        async with async_session_maker() as session:
            try:
                # 获取告警信息
                alarm = await session.get(AlarmTable, alarm_id)
                if not alarm:
                    self.logger.warning(f"告警 {alarm_id} 不存在")
                    return
                
                # 如果是更新且状态已解决，可能需要发送解决通知
                if is_update and alarm.status == "resolved":
                    await self._handle_resolved_alarm(session, alarm)
                    return
                
                # 查找匹配的订阅
                matching_subscriptions = await self._find_matching_subscriptions(session, alarm)
                
                if not matching_subscriptions:
                    self.logger.debug(f"告警 {alarm_id} 没有找到匹配的订阅")
                    return
                
                # 为每个匹配的订阅创建通知
                notifications_created = 0
                for subscription in matching_subscriptions:
                    success = await self._create_subscription_notifications(session, alarm, subscription)
                    if success:
                        notifications_created += 1
                
                await session.commit()
                
                self.logger.info(
                    f"告警 {alarm_id} 分发完成: {len(matching_subscriptions)} 个订阅, {notifications_created} 个通知已创建",
                    extra={
                        "alarm_id": alarm_id,
                        "subscriptions_matched": len(matching_subscriptions),
                        "notifications_created": notifications_created
                    }
                )
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"处理告警 {alarm_id} 分发时出错: {str(e)}")
    
    async def _find_matching_subscriptions(
        self, 
        session: AsyncSession, 
        alarm: AlarmTable
    ) -> List[UserSubscription]:
        """查找匹配告警的订阅"""
        try:
            # 获取所有启用的订阅
            query = select(UserSubscription).where(UserSubscription.enabled == True)
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
                "created_at": alarm.created_at.isoformat() if alarm.created_at else None,
                "updated_at": alarm.updated_at.isoformat() if alarm.updated_at else None
            }
            
            # 过滤匹配的订阅
            matching_subscriptions = []
            for subscription in all_subscriptions:
                try:
                    if self._match_subscription_filters(subscription.filters, alarm_data):
                        # 检查冷却时间
                        if await self._check_cooldown(session, subscription, alarm):
                            # 检查频率限制
                            if await self._check_rate_limit(session, subscription):
                                matching_subscriptions.append(subscription)
                except Exception as e:
                    self.logger.error(f"检查订阅 {subscription.id} 时出错: {str(e)}")
                    continue
            
            return matching_subscriptions
            
        except Exception as e:
            self.logger.error(f"查找匹配订阅时出错: {str(e)}")
            return []
    
    def _match_subscription_filters(self, filters: Dict[str, Any], alarm_data: Dict[str, Any]) -> bool:
        """检查告警是否匹配订阅过滤条件"""
        try:
            if not filters:
                return True
            
            # 支持 AND/OR 逻辑
            if "and" in filters:
                return all(
                    self._match_subscription_filters(condition, alarm_data)
                    for condition in filters["and"]
                )
            
            if "or" in filters:
                return any(
                    self._match_subscription_filters(condition, alarm_data)
                    for condition in filters["or"]
                )
            
            # 单个条件匹配
            field = filters.get("field")
            operator = filters.get("operator")
            value = filters.get("value")
            
            if not all([field, operator, value is not None]):
                return True
            
            alarm_value = alarm_data.get(field)
            if alarm_value is None:
                return False
            
            return self._evaluate_filter_condition(alarm_value, operator, value)
            
        except Exception as e:
            self.logger.error(f"匹配过滤条件时出错: {str(e)}")
            return False
    
    def _evaluate_filter_condition(self, alarm_value: Any, operator: str, filter_value: Any) -> bool:
        """评估单个过滤条件"""
        try:
            if operator == "equals":
                return alarm_value == filter_value
            elif operator == "not_equals":
                return alarm_value != filter_value
            elif operator == "contains":
                return str(filter_value).lower() in str(alarm_value).lower()
            elif operator == "not_contains":
                return str(filter_value).lower() not in str(alarm_value).lower()
            elif operator == "in":
                return alarm_value in filter_value if isinstance(filter_value, list) else False
            elif operator == "not_in":
                return alarm_value not in filter_value if isinstance(filter_value, list) else True
            elif operator == "regex":
                import re
                try:
                    return bool(re.search(str(filter_value), str(alarm_value), re.IGNORECASE))
                except:
                    return False
            elif operator == "greater_than":
                try:
                    return float(alarm_value) > float(filter_value)
                except:
                    return False
            elif operator == "less_than":
                try:
                    return float(alarm_value) < float(filter_value)
                except:
                    return False
            else:
                return False
        except Exception:
            return False
    
    async def _check_cooldown(
        self, 
        session: AsyncSession, 
        subscription: UserSubscription,
        alarm: AlarmTable
    ) -> bool:
        """检查订阅冷却时间"""
        if subscription.cooldown_minutes <= 0:
            return True
        
        try:
            # 查找最近的通知记录
            from datetime import timedelta
            cooldown_time = datetime.utcnow() - timedelta(minutes=subscription.cooldown_minutes)
            
            query = select(NotificationLog).where(
                NotificationLog.subscription_id == subscription.id,
                NotificationLog.alarm_id == alarm.id,
                NotificationLog.created_at >= cooldown_time
            )
            
            result = await session.execute(query)
            recent_notification = result.scalars().first()
            
            return recent_notification is None
            
        except Exception as e:
            self.logger.error(f"检查冷却时间时出错: {str(e)}")
            return True
    
    async def _check_rate_limit(self, session: AsyncSession, subscription: UserSubscription) -> bool:
        """检查订阅频率限制"""
        if subscription.max_notifications_per_hour <= 0:
            return True
        
        try:
            from datetime import timedelta
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            query = select(NotificationLog).where(
                NotificationLog.subscription_id == subscription.id,
                NotificationLog.created_at >= one_hour_ago
            )
            
            result = await session.execute(query)
            recent_notifications = result.scalars().all()
            
            return len(recent_notifications) < subscription.max_notifications_per_hour
            
        except Exception as e:
            self.logger.error(f"检查频率限制时出错: {str(e)}")
            return True
    
    async def _create_subscription_notifications(
        self, 
        session: AsyncSession,
        alarm: AlarmTable, 
        subscription: UserSubscription
    ) -> bool:
        """为订阅创建通知"""
        try:
            notifications_created = 0
            
            # 为每个联系点创建通知
            for contact_point_id in subscription.contact_points:
                # 获取联系点信息
                from src.models.alarm import ContactPoint
                contact_point = await session.get(ContactPoint, contact_point_id)
                if not contact_point or not contact_point.enabled:
                    continue
                
                # 创建通知日志记录
                notification_log = NotificationLog(
                    subscription_id=subscription.id,
                    alarm_id=alarm.id,
                    contact_point_id=contact_point_id,
                    status="pending",
                    notification_content={
                        "alarm_title": alarm.title,
                        "alarm_severity": alarm.severity,
                        "alarm_description": alarm.description,
                        "alarm_source": alarm.source,
                        "contact_type": contact_point.contact_type,
                        "subscription_name": subscription.name
                    }
                )
                
                session.add(notification_log)
                await session.flush()  # 获取ID
                
                # 异步发送通知（不等待完成）
                asyncio.create_task(
                    self._send_notification_async(notification_log.id, contact_point, alarm, subscription)
                )
                
                notifications_created += 1
            
            # 更新订阅统计
            subscription.last_notification_at = datetime.utcnow()
            subscription.total_notifications_sent += notifications_created
            
            return notifications_created > 0
            
        except Exception as e:
            self.logger.error(f"创建订阅通知时出错: {str(e)}")
            return False
    
    async def _send_notification_async(
        self,
        notification_log_id: int,
        contact_point: Any,
        alarm: AlarmTable,
        subscription: UserSubscription
    ):
        """异步发送通知"""
        try:
            # 构建通知内容
            notification_data = {
                "id": notification_log_id,
                "alarm_id": alarm.id,
                "subscription_id": subscription.id,
                "channel": contact_point.contact_type,
                "recipient": self._get_recipient_from_config(contact_point.config),
                "subject": f"告警通知: {alarm.title}",
                "content": self._build_notification_content(alarm, subscription),
                "priority": self._determine_priority(alarm.severity),
                "notification_config": contact_point.config,
                "created_at": datetime.utcnow()
            }
            
            # 发送通知
            success = await self._send_notification(notification_data)
            
            # 更新通知状态
            await self._update_notification_status(notification_log_id, success)
            
        except Exception as e:
            self.logger.error(f"异步发送通知 {notification_log_id} 时出错: {str(e)}")
            await self._update_notification_status(notification_log_id, False, str(e))
    
    def _get_recipient_from_config(self, config: Dict[str, Any]) -> str:
        """从联系点配置中获取接收者"""
        if "webhook_url" in config:
            return config["webhook_url"]
        elif "email" in config:
            return config["email"]
        elif "channel" in config:
            return config["channel"]
        else:
            return "unknown"
    
    def _build_notification_content(self, alarm: AlarmTable, subscription: UserSubscription) -> str:
        """构建通知内容"""
        return f"""
告警详情:
- 标题: {alarm.title}
- 严重程度: {alarm.severity}
- 状态: {alarm.status}
- 来源: {alarm.source}
- 描述: {alarm.description or '无'}
- 主机: {alarm.host or '无'}
- 服务: {alarm.service or '无'}
- 环境: {alarm.environment or '无'}
- 创建时间: {alarm.created_at}

订阅信息:
- 订阅名称: {subscription.name}
- 订阅类型: {subscription.subscription_type}
        """.strip()
    
    def _determine_priority(self, severity: str) -> str:
        """根据告警严重程度确定通知优先级"""
        severity_priority_map = {
            "critical": "urgent",
            "high": "high",
            "medium": "normal",
            "low": "low",
            "info": "low"
        }
        return severity_priority_map.get(severity, "normal")
    
    async def _send_notification(self, notification_data: Dict[str, Any]) -> bool:
        """发送通知"""
        try:
            # 使用通知服务发送
            from src.services.notification_service import notification_service
            
            # 创建临时通知对象用于发送
            class TempNotification:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)
            
            temp_notification = TempNotification(notification_data)
            
            # 获取发送器
            sender_class = notification_service.senders.get(notification_data["channel"])
            if not sender_class:
                self.logger.error(f"不支持的通知渠道: {notification_data['channel']}")
                return False
            
            sender = sender_class(notification_data["notification_config"])
            
            # 验证配置
            if not await sender.validate_config():
                self.logger.error(f"通知渠道配置无效: {notification_data['channel']}")
                return False
            
            # 发送通知
            result = await sender.send(temp_notification)
            return result.get("success", False)
            
        except Exception as e:
            self.logger.error(f"发送通知时出错: {str(e)}")
            return False
    
    async def _update_notification_status(self, notification_log_id: int, success: bool, error_message: str = None):
        """更新通知状态"""
        async with async_session_maker() as session:
            try:
                notification_log = await session.get(NotificationLog, notification_log_id)
                if notification_log:
                    notification_log.status = "sent" if success else "failed"
                    if error_message:
                        notification_log.error_message = error_message
                    if success:
                        notification_log.sent_at = datetime.utcnow()
                    
                    await session.commit()
            except Exception as e:
                self.logger.error(f"更新通知状态时出错: {str(e)}")
    
    async def _handle_resolved_alarm(self, session: AsyncSession, alarm: AlarmTable):
        """处理已解决的告警"""
        # 这里可以实现解决通知的逻辑
        # 例如发送告警已解决的通知给相关订阅者
        self.logger.info(f"告警 {alarm.id} 已解决")


# 全局分发服务实例
alarm_dispatch_service = AlarmDispatchService()