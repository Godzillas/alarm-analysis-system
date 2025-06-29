"""
通知发送服务
支持多种通知渠道的统一发送接口
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from abc import ABC, abstractmethod
import aiohttp
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.core.database import async_session_maker
from src.core.logging import get_logger
from src.core.exceptions import (
    DatabaseException, ValidationException,
    ServiceUnavailableException
)
from src.models.alarm import (
    NotificationLog, NotificationTemplate
)

logger = get_logger(__name__)


class NotificationSender(ABC):
    """通知发送器基类"""
    
    def __init__(self, channel_config: Dict[str, Any]):
        self.config = channel_config
        self.logger = logger
    
    @abstractmethod
    async def send(self, notification: NotificationLog) -> Dict[str, Any]:
        """发送通知"""
        pass
    
    @abstractmethod
    async def validate_config(self) -> bool:
        """验证配置"""
        pass


class EmailSender(NotificationSender):
    """邮件发送器"""
    
    async def send(self, notification: NotificationLog) -> Dict[str, Any]:
        """发送邮件"""
        try:
            import aiosmtplib
            
            # 构建邮件
            msg = MIMEMultipart()
            msg['From'] = self.config['smtp_user']
            msg['To'] = notification.recipient
            msg['Subject'] = notification.subject or "告警通知"
            
            # 添加文本内容
            msg.attach(MIMEText(notification.content, 'plain', 'utf-8'))
            
            # 如果有HTML内容，添加HTML部分
            if notification.html_content:
                msg.attach(MIMEText(notification.html_content, 'html', 'utf-8'))
            
            # 发送邮件
            await aiosmtplib.send(
                msg,
                hostname=self.config['smtp_host'],
                port=self.config.get('smtp_port', 587),
                username=self.config['smtp_user'],
                password=self.config['smtp_password'],
                use_tls=self.config.get('use_tls', True)
            )
            
            return {
                "success": True,
                "external_id": f"email_{notification.id}_{datetime.utcnow().timestamp()}",
                "delivery_time": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "EMAIL_SEND_FAILED"
            }
    
    async def validate_config(self) -> bool:
        """验证邮件配置"""
        required_fields = ['smtp_host', 'smtp_user', 'smtp_password']
        return all(field in self.config for field in required_fields)


class WebhookSender(NotificationSender):
    """Webhook发送器"""
    
    async def send(self, notification: NotificationLog) -> Dict[str, Any]:
        """发送Webhook"""
        try:
            # 构建payload
            payload = {
                "notification_id": notification.id,
                "alarm_id": notification.alarm_id,
                "type": notification.notification_type,
                "recipient": notification.recipient,
                "subject": notification.subject,
                "content": notification.content,
                "priority": notification.priority,
                "timestamp": notification.created_at.isoformat()
            }
            
            # 如果有自定义payload格式，使用自定义格式
            if 'payload_template' in self.config:
                payload = self._render_payload_template(payload)
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'AlarmSystem/1.0'
            }
            
            # 添加认证头
            if 'auth_header' in self.config:
                headers[self.config['auth_header']] = self.config['auth_token']
            
            timeout = aiohttp.ClientTimeout(total=self.config.get('timeout', 30))
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.config['webhook_url'],
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        response_data = await response.text()
                        return {
                            "success": True,
                            "external_id": f"webhook_{notification.id}_{response.headers.get('X-Request-ID', '')}",
                            "response_status": response.status,
                            "response_data": response_data[:500]  # 限制响应数据长度
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "error_code": f"HTTP_{response.status}"
                        }
                        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Webhook request timeout",
                "error_code": "TIMEOUT"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "WEBHOOK_SEND_FAILED"
            }
    
    async def validate_config(self) -> bool:
        """验证Webhook配置"""
        return 'webhook_url' in self.config
    
    def _render_payload_template(self, default_payload: Dict[str, Any]) -> Dict[str, Any]:
        """渲染自定义payload模板"""
        try:
            import jinja2
            template_str = self.config['payload_template']
            template = jinja2.Template(template_str)
            rendered = template.render(**default_payload)
            return json.loads(rendered)
        except Exception:
            return default_payload


class SlackSender(NotificationSender):
    """Slack发送器"""
    
    async def send(self, notification: NotificationLog) -> Dict[str, Any]:
        """发送Slack消息"""
        try:
            # 构建Slack消息格式
            payload = {
                "channel": self.config.get('channel', notification.recipient),
                "username": self.config.get('username', '告警系统'),
                "icon_emoji": self._get_severity_emoji(notification),
                "attachments": [
                    {
                        "color": self._get_severity_color(notification),
                        "title": notification.subject,
                        "text": notification.content,
                        "footer": "告警系统",
                        "ts": int(notification.created_at.timestamp())
                    }
                ]
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {self.config['bot_token']}"
            }
            
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    'https://slack.com/api/chat.postMessage',
                    json=payload,
                    headers=headers
                ) as response:
                    data = await response.json()
                    
                    if data.get('ok'):
                        return {
                            "success": True,
                            "external_id": data.get('ts'),
                            "channel": data.get('channel')
                        }
                    else:
                        return {
                            "success": False,
                            "error": data.get('error', 'Unknown Slack error'),
                            "error_code": "SLACK_API_ERROR"
                        }
                        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "SLACK_SEND_FAILED"
            }
    
    async def validate_config(self) -> bool:
        """验证Slack配置"""
        return 'bot_token' in self.config
    
    def _get_severity_emoji(self, notification: NotificationLog) -> str:
        """根据优先级获取emoji"""
        priority_emoji = {
            "urgent": ":rotating_light:",
            "high": ":warning:",
            "normal": ":information_source:",
            "low": ":white_circle:"
        }
        return priority_emoji.get(notification.priority, ":information_source:")
    
    def _get_severity_color(self, notification: NotificationLog) -> str:
        """根据优先级获取颜色"""
        priority_colors = {
            "urgent": "danger",
            "high": "warning", 
            "normal": "good",
            "low": "#36a64f"
        }
        return priority_colors.get(notification.priority, "good")


class FeishuSender(NotificationSender):
    """飞书机器人发送器"""
    
    async def send(self, notification: NotificationLog) -> Dict[str, Any]:
        """发送飞书消息"""
        try:
            webhook_url = self.config.get('webhook_url')
            if not webhook_url:
                return {
                    "success": False,
                    "error": "Missing webhook_url in configuration",
                    "error_code": "MISSING_WEBHOOK_URL"
                }
            
            # 构建飞书消息
            message = self._build_feishu_message(notification)
            
            timeout = aiohttp.ClientTimeout(total=self.config.get('timeout', 30))
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(webhook_url, json=message) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('StatusCode') == 0:
                            return {
                                "success": True,
                                "external_id": f"feishu_{notification.id}_{datetime.utcnow().timestamp()}",
                                "response_status": response.status
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"Feishu API error: {result.get('StatusMessage', 'Unknown error')}",
                                "error_code": "FEISHU_API_ERROR"
                            }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "error_code": f"HTTP_{response.status}"
                        }
                        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Feishu request timeout",
                "error_code": "TIMEOUT"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "FEISHU_SEND_FAILED"
            }
    
    def _build_feishu_message(self, notification: NotificationLog) -> Dict[str, Any]:
        """构建飞书消息体"""
        message_type = self.config.get('message_type', 'interactive')
        
        if message_type == 'text':
            return {
                "msg_type": "text",
                "content": {
                    "text": f"{notification.subject}\n\n{notification.content}"
                }
            }
        elif message_type == 'rich_text':
            return {
                "msg_type": "rich_text",
                "content": {
                    "rich_text": notification.html_content or notification.content
                }
            }
        else:  # interactive card
            return {
                "msg_type": "interactive",
                "card": self._build_interactive_card(notification)
            }
    
    def _build_interactive_card(self, notification: NotificationLog) -> Dict[str, Any]:
        """构建飞书交互式卡片"""
        # 根据优先级确定颜色
        priority_colors = {
            "urgent": "red",
            "high": "orange",
            "normal": "blue", 
            "low": "grey"
        }
        color = priority_colors.get(notification.priority, "blue")
        
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": color,
                "title": {
                    "content": notification.subject or "告警通知",
                    "tag": "plain_text"
                }
            },
            "elements": []
        }
        
        # 添加基本信息字段
        info_fields = [
            {
                "is_short": True,
                "text": {
                    "content": f"**优先级:** {notification.priority}",
                    "tag": "lark_md"
                }
            },
            {
                "is_short": True,
                "text": {
                    "content": f"**通知ID:** {notification.id}",
                    "tag": "lark_md"
                }
            }
        ]
        
        if hasattr(notification, 'alarm_id') and notification.alarm_id:
            info_fields.append({
                "is_short": True,
                "text": {
                    "content": f"**告警ID:** {notification.alarm_id}",
                    "tag": "lark_md"
                }
            })
        
        card["elements"].append({
            "tag": "div",
            "fields": info_fields
        })
        
        # 添加通知内容
        if notification.content:
            card["elements"].append({
                "tag": "div",
                "text": {
                    "content": notification.content,
                    "tag": "lark_md"
                }
            })
        
        # 添加时间信息
        card["elements"].append({
            "tag": "div",
            "text": {
                "content": f"**发送时间:** {notification.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                "tag": "lark_md"
            }
        })
        
        # 添加操作按钮（如果启用）
        if self.config.get('add_action_buttons', True) and hasattr(notification, 'alarm_id') and notification.alarm_id:
            card["elements"].append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "content": "确认告警",
                            "tag": "plain_text"
                        },
                        "type": "primary",
                        "value": {
                            "action": "acknowledge",
                            "alarm_id": notification.alarm_id
                        }
                    },
                    {
                        "tag": "button",
                        "text": {
                            "content": "解决告警",
                            "tag": "plain_text"
                        },
                        "type": "danger",
                        "value": {
                            "action": "resolve",
                            "alarm_id": notification.alarm_id
                        }
                    }
                ]
            })
        
        return card
    
    async def validate_config(self) -> bool:
        """验证飞书配置"""
        return 'webhook_url' in self.config


class SMSSender(NotificationSender):
    """短信发送器"""
    
    async def send(self, notification: NotificationLog) -> Dict[str, Any]:
        """发送短信"""
        try:
            # 这里需要集成具体的短信服务商API
            # 例如阿里云短信、腾讯云短信等
            
            # 简化的示例实现
            sms_content = f"【告警系统】{notification.subject}: {notification.content[:50]}..."
            
            # 模拟发送
            await asyncio.sleep(0.1)
            
            return {
                "success": True,
                "external_id": f"sms_{notification.id}_{datetime.utcnow().timestamp()}",
                "content": sms_content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "SMS_SEND_FAILED"
            }
    
    async def validate_config(self) -> bool:
        """验证短信配置"""
        required_fields = ['api_key', 'api_secret', 'sign_name']
        return all(field in self.config for field in required_fields)


class NotificationService:
    """通知服务主类"""
    
    def __init__(self):
        self.logger = logger
        self.senders = {
            "email": EmailSender,
            "webhook": WebhookSender,
            "slack": SlackSender,
            "feishu": FeishuSender,
            "sms": SMSSender
        }
    
    async def send_notification(self, notification_id: int) -> bool:
        """发送单个通知"""
        async with async_session_maker() as session:
            try:
                # 获取通知记录
                notification = await session.get(NotificationLog, notification_id)
                if not notification:
                    self.logger.error(f"Notification {notification_id} not found")
                    return False
                
                # 检查状态
                if notification.status != "pending":
                    self.logger.warning(f"Notification {notification_id} status is {notification.status}")
                    return False
                
                # 更新状态为发送中
                notification.status = "sending"
                await session.commit()
                
                # 获取发送器
                sender_class = self.senders.get(notification.channel)
                if not sender_class:
                    await self._mark_failed(session, notification, "Unsupported channel type")
                    return False
                
                # 获取渠道配置
                channel_config = notification.notification_config or {}
                sender = sender_class(channel_config)
                
                # 验证配置
                if not await sender.validate_config():
                    await self._mark_failed(session, notification, "Invalid channel configuration")
                    return False
                
                # 发送通知
                start_time = datetime.utcnow()
                result = await sender.send(notification)
                end_time = datetime.utcnow()
                
                # 更新通知状态
                notification.processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
                
                if result["success"]:
                    notification.status = NotificationStatus.SENT
                    notification.sent_at = end_time
                    notification.external_id = result.get("external_id")
                    
                    # 更新订阅统计
                    await self._update_subscription_stats(session, notification.subscription_id, True)
                    
                    self.logger.info(
                        f"Notification {notification_id} sent successfully",
                        extra={
                            "notification_id": notification_id,
                            "channel": notification.channel,
                            "recipient": notification.recipient,
                            "processing_time": notification.processing_time_ms
                        }
                    )
                    
                else:
                    await self._handle_send_failure(session, notification, result)
                
                await session.commit()
                return result["success"]
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error sending notification {notification_id}: {str(e)}")
                
                # 尝试标记为失败
                try:
                    notification = await session.get(NotificationLog, notification_id)
                    if notification:
                        await self._mark_failed(session, notification, str(e))
                        await session.commit()
                except:
                    pass
                
                return False
    
    async def send_batch_notifications(self, notification_ids: List[int]) -> Dict[str, int]:
        """批量发送通知"""
        results = {"success": 0, "failed": 0}
        
        # 并发发送，但限制并发数
        semaphore = asyncio.Semaphore(10)  # 最多10个并发
        
        async def send_with_semaphore(notification_id: int):
            async with semaphore:
                success = await self.send_notification(notification_id)
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
        
        # 创建任务并等待完成
        tasks = [send_with_semaphore(nid) for nid in notification_ids]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.logger.info(
            f"Batch notification sending completed: {results['success']} success, {results['failed']} failed",
            extra={"total": len(notification_ids), "results": results}
        )
        
        return results
    
    async def retry_failed_notifications(self, max_age_hours: int = 24) -> int:
        """重试失败的通知"""
        async with async_session_maker() as session:
            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
                
                # 查找需要重试的通知
                from sqlalchemy import select, and_
                query = select(NotificationLog).where(
                    and_(
                        NotificationLog.status == NotificationStatus.FAILED,
                        NotificationLog.retry_count < NotificationLog.max_retries,
                        NotificationLog.created_at >= cutoff_time,
                        or_(
                            NotificationLog.next_retry_at.is_(None),
                            NotificationLog.next_retry_at <= datetime.utcnow()
                        )
                    )
                )
                
                result = await session.execute(query)
                failed_notifications = result.scalars().all()
                
                self.logger.info(f"Found {len(failed_notifications)} notifications to retry")
                
                retry_count = 0
                for notification in failed_notifications:
                    # 重置状态为待发送
                    notification.status = NotificationStatus.PENDING
                    notification.retry_count += 1
                    notification.next_retry_at = None
                    retry_count += 1
                
                await session.commit()
                
                # 发送重试的通知
                if retry_count > 0:
                    retry_ids = [n.id for n in failed_notifications]
                    await self.send_batch_notifications(retry_ids)
                
                return retry_count
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error retrying failed notifications: {str(e)}")
                return 0
    
    async def get_notification_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取通知统计信息"""
        async with async_session_maker() as session:
            try:
                from sqlalchemy import select, func, and_
                start_date = datetime.utcnow() - timedelta(days=days)
                
                # 总体统计
                total_query = select(func.count(NotificationLog.id)).where(
                    NotificationLog.created_at >= start_date
                )
                total_result = await session.execute(total_query)
                total_notifications = total_result.scalar()
                
                # 按状态统计
                status_query = select(
                    NotificationLog.status,
                    func.count(NotificationLog.id).label('count')
                ).where(
                    NotificationLog.created_at >= start_date
                ).group_by(NotificationLog.status)
                
                status_result = await session.execute(status_query)
                status_stats = {row.status: row.count for row in status_result}
                
                # 按渠道统计
                channel_query = select(
                    NotificationLog.channel,
                    func.count(NotificationLog.id).label('count'),
                    func.avg(NotificationLog.processing_time_ms).label('avg_processing_time')
                ).where(
                    NotificationLog.created_at >= start_date
                ).group_by(NotificationLog.channel)
                
                channel_result = await session.execute(channel_query)
                channel_stats = [
                    {
                        "channel": row.channel,
                        "count": row.count,
                        "avg_processing_time": row.avg_processing_time
                    }
                    for row in channel_result
                ]
                
                # 成功率计算
                success_rate = (
                    status_stats.get("sent", 0) / total_notifications * 100
                    if total_notifications > 0 else 0
                )
                
                return {
                    "total_notifications": total_notifications,
                    "success_rate": round(success_rate, 2),
                    "by_status": status_stats,
                    "by_channel": channel_stats,
                    "period_days": days
                }
                
            except Exception as e:
                raise DatabaseException(f"Failed to get notification statistics: {str(e)}")
    
    # 私有方法
    
    async def _mark_failed(
        self, 
        session,
        notification: NotificationLog, 
        error_message: str
    ):
        """标记通知为失败"""
        notification.status = NotificationStatus.FAILED
        notification.error_message = error_message
        
        # 计算下次重试时间
        if notification.retry_count < notification.max_retries:
            retry_delay = min(300 * (2 ** notification.retry_count), 3600)  # 指数退避，最大1小时
            notification.next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)
        
        # 更新订阅统计
        await self._update_subscription_stats(session, notification.subscription_id, False)
    
    async def _handle_send_failure(
        self,
        session,
        notification: NotificationLog,
        result: Dict[str, Any]
    ):
        """处理发送失败"""
        notification.error_message = result.get("error", "Unknown error")
        notification.error_code = result.get("error_code")
        
        if notification.retry_count < notification.max_retries:
            notification.status = NotificationStatus.FAILED
            # 计算重试时间
            retry_delay = min(300 * (2 ** notification.retry_count), 3600)
            notification.next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)
        else:
            notification.status = NotificationStatus.EXPIRED
            notification.next_retry_at = None
        
        # 更新订阅统计
        await self._update_subscription_stats(session, notification.subscription_id, False)
        
        self.logger.error(
            f"Notification {notification.id} failed: {notification.error_message}",
            extra={
                "notification_id": notification.id,
                "channel": notification.channel,
                "error_code": notification.error_code,
                "retry_count": notification.retry_count
            }
        )
    
    async def _update_subscription_stats(
        self,
        session,
        subscription_id: int,
        success: bool
    ):
        """更新订阅统计"""
        try:
            from src.models.subscription import AlarmSubscription
            subscription = await session.get(AlarmSubscription, subscription_id)
            if subscription:
                if success:
                    subscription.successful_notifications += 1
                else:
                    subscription.failed_notifications += 1
        except Exception as e:
            self.logger.error(f"Error updating subscription stats: {str(e)}")


# 全局通知服务实例
notification_service = NotificationService()