"""
通知管理器
统一管理多种通知渠道，支持通知策略和模板管理
"""

import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from enum import Enum
import logging

from .feishu_webhook import FeishuWebhookNotifier
from .email_notifier import EmailNotifier
from src.models.alarm import AlarmTable
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationChannel(Enum):
    """通知渠道枚举"""
    EMAIL = "email"
    FEISHU = "feishu"
    WEBHOOK = "webhook"
    SMS = "sms"  # 预留扩展


class NotificationPriority(Enum):
    """通知优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class NotificationTemplate:
    """通知模板"""
    
    def __init__(
        self,
        template_id: str,
        name: str,
        channels: List[NotificationChannel],
        conditions: Dict[str, Any],
        config: Dict[str, Any]
    ):
        self.template_id = template_id
        self.name = name
        self.channels = channels
        self.conditions = conditions  # 触发条件
        self.config = config  # 通知配置


class NotificationManager:
    """通知管理器"""
    
    def __init__(self):
        self.notifiers: Dict[NotificationChannel, Any] = {}
        self.templates: Dict[str, NotificationTemplate] = {}
        self.notification_history: List[Dict[str, Any]] = []
        self.rate_limiter: Dict[str, List[datetime]] = {}
        
    def register_notifier(self, channel: NotificationChannel, notifier: Any):
        """注册通知器"""
        self.notifiers[channel] = notifier
        logger.info(f"Registered notifier for channel: {channel.value}")
    
    def register_email_notifier(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        use_tls: bool = True,
        from_email: str = "",
        from_name: str = "告警系统"
    ):
        """注册邮件通知器"""
        notifier = EmailNotifier(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            username=username,
            password=password,
            use_tls=use_tls,
            from_email=from_email,
            from_name=from_name
        )
        self.register_notifier(NotificationChannel.EMAIL, notifier)
    
    def register_feishu_notifier(self, webhook_url: str, secret: Optional[str] = None):
        """注册飞书通知器"""
        notifier = FeishuWebhookNotifier(webhook_url=webhook_url, secret=secret)
        self.register_notifier(NotificationChannel.FEISHU, notifier)
    
    def add_template(self, template: NotificationTemplate):
        """添加通知模板"""
        self.templates[template.template_id] = template
        logger.info(f"Added notification template: {template.name}")
    
    def create_severity_template(
        self,
        template_id: str,
        name: str,
        severities: List[str],
        channels: List[NotificationChannel],
        config: Dict[str, Any] = None
    ) -> NotificationTemplate:
        """创建基于严重程度的通知模板"""
        conditions = {
            "severity": {"in": severities}
        }
        
        template = NotificationTemplate(
            template_id=template_id,
            name=name,
            channels=channels,
            conditions=conditions,
            config=config or {}
        )
        
        self.add_template(template)
        return template
    
    def create_source_template(
        self,
        template_id: str,
        name: str,
        sources: List[str],
        channels: List[NotificationChannel],
        config: Dict[str, Any] = None
    ) -> NotificationTemplate:
        """创建基于来源的通知模板"""
        conditions = {
            "source": {"in": sources}
        }
        
        template = NotificationTemplate(
            template_id=template_id,
            name=name,
            channels=channels,
            conditions=conditions,
            config=config or {}
        )
        
        self.add_template(template)
        return template
    
    def create_time_based_template(
        self,
        template_id: str,
        name: str,
        time_range: Dict[str, str],
        channels: List[NotificationChannel],
        config: Dict[str, Any] = None
    ) -> NotificationTemplate:
        """创建基于时间的通知模板"""
        conditions = {
            "time_range": time_range
        }
        
        template = NotificationTemplate(
            template_id=template_id,
            name=name,
            channels=channels,
            conditions=conditions,
            config=config or {}
        )
        
        self.add_template(template)
        return template
    
    async def send_notification(
        self,
        alarm: AlarmTable,
        recipients: Dict[NotificationChannel, List[str]],
        template_id: Optional[str] = None,
        user_info: Optional[Dict[str, Any]] = None,
        rule_name: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> Dict[NotificationChannel, bool]:
        """
        发送通知
        
        Args:
            alarm: 告警对象
            recipients: 接收者信息 {channel: [recipient_list]}
            template_id: 通知模板ID
            user_info: 用户信息
            rule_name: 规则名称
            priority: 通知优先级
            
        Returns:
            Dict[NotificationChannel, bool]: 各渠道发送结果
        """
        results = {}
        
        # 检查是否符合模板条件
        if template_id and template_id in self.templates:
            template = self.templates[template_id]
            if not self._matches_template_conditions(alarm, template):
                logger.info(f"Alarm does not match template conditions: {template_id}")
                return results
        
        # 检查频率限制
        if not self._check_rate_limit(alarm, priority):
            logger.warning(f"Rate limit exceeded for alarm: {alarm.id}")
            return results
        
        # 并发发送通知
        tasks = []
        for channel, recipient_list in recipients.items():
            if channel in self.notifiers and recipient_list:
                task = self._send_channel_notification(
                    channel, alarm, recipient_list, user_info, rule_name
                )
                tasks.append((channel, task))
        
        # 等待所有任务完成
        for channel, task in tasks:
            try:
                success = await task
                results[channel] = success
            except Exception as e:
                logger.error(f"Error sending notification via {channel.value}: {e}")
                results[channel] = False
        
        # 记录通知历史
        self._record_notification_history(alarm, recipients, results, template_id)
        
        return results
    
    async def _send_channel_notification(
        self,
        channel: NotificationChannel,
        alarm: AlarmTable,
        recipients: List[str],
        user_info: Optional[Dict[str, Any]] = None,
        rule_name: Optional[str] = None
    ) -> bool:
        """发送单个渠道的通知"""
        notifier = self.notifiers[channel]
        
        try:
            if channel == NotificationChannel.EMAIL:
                return await notifier.send_alarm_notification(
                    alarm, recipients, user_info, rule_name
                )
            elif channel == NotificationChannel.FEISHU:
                async with notifier:
                    return await notifier.send_alarm_notification(
                        alarm, user_info, rule_name
                    )
            else:
                logger.warning(f"Unsupported notification channel: {channel.value}")
                return False
                
        except Exception as e:
            logger.error(f"Error in {channel.value} notification: {e}")
            return False
    
    def _matches_template_conditions(self, alarm: AlarmTable, template: NotificationTemplate) -> bool:
        """检查告警是否符合模板条件"""
        conditions = template.conditions
        
        # 检查严重程度条件
        if "severity" in conditions:
            severity_condition = conditions["severity"]
            if "in" in severity_condition:
                if alarm.severity not in severity_condition["in"]:
                    return False
            elif "equals" in severity_condition:
                if alarm.severity != severity_condition["equals"]:
                    return False
        
        # 检查来源条件
        if "source" in conditions:
            source_condition = conditions["source"]
            if "in" in source_condition:
                if alarm.source not in source_condition["in"]:
                    return False
            elif "equals" in source_condition:
                if alarm.source != source_condition["equals"]:
                    return False
        
        # 检查时间条件
        if "time_range" in conditions:
            time_condition = conditions["time_range"]
            if not self._check_time_condition(time_condition):
                return False
        
        # 检查标签条件
        if "tags" in conditions and alarm.tags:
            tag_conditions = conditions["tags"]
            for tag_key, tag_condition in tag_conditions.items():
                if tag_key not in alarm.tags:
                    return False
                
                tag_value = alarm.tags[tag_key]
                if "in" in tag_condition:
                    if tag_value not in tag_condition["in"]:
                        return False
                elif "equals" in tag_condition:
                    if tag_value != tag_condition["equals"]:
                        return False
        
        return True
    
    def _check_time_condition(self, time_condition: Dict[str, Any]) -> bool:
        """检查时间条件"""
        now = datetime.now()
        
        # 检查工作日
        if "weekdays" in time_condition:
            weekdays = time_condition["weekdays"]
            if now.weekday() not in weekdays:
                return False
        
        # 检查时间范围
        if "start_time" in time_condition and "end_time" in time_condition:
            start_time = time_condition["start_time"]
            end_time = time_condition["end_time"]
            current_time = now.strftime("%H:%M")
            
            if start_time <= end_time:
                if not (start_time <= current_time <= end_time):
                    return False
            else:
                if not (current_time >= start_time or current_time <= end_time):
                    return False
        
        return True
    
    def _check_rate_limit(self, alarm: AlarmTable, priority: NotificationPriority) -> bool:
        """检查频率限制"""
        # 根据优先级设置不同的限制
        rate_limits = {
            NotificationPriority.LOW: {"max_per_hour": 5, "min_interval": 300},  # 5次/小时，5分钟间隔
            NotificationPriority.NORMAL: {"max_per_hour": 10, "min_interval": 120},  # 10次/小时，2分钟间隔
            NotificationPriority.HIGH: {"max_per_hour": 20, "min_interval": 60},  # 20次/小时，1分钟间隔
            NotificationPriority.URGENT: {"max_per_hour": 100, "min_interval": 30}  # 100次/小时，30秒间隔
        }
        
        limit_config = rate_limits.get(priority, rate_limits[NotificationPriority.NORMAL])
        
        # 使用告警指纹作为限制键
        rate_key = f"{alarm.fingerprint}:{priority.value}"
        now = datetime.now()
        
        if rate_key not in self.rate_limiter:
            self.rate_limiter[rate_key] = []
        
        # 清理过期记录
        cutoff_time = now - timedelta(hours=1)
        self.rate_limiter[rate_key] = [
            ts for ts in self.rate_limiter[rate_key] if ts > cutoff_time
        ]
        
        # 检查频率限制
        recent_notifications = self.rate_limiter[rate_key]
        
        # 检查小时内通知次数
        if len(recent_notifications) >= limit_config["max_per_hour"]:
            return False
        
        # 检查最小间隔
        if recent_notifications:
            last_notification = max(recent_notifications)
            min_interval = timedelta(seconds=limit_config["min_interval"])
            if now - last_notification < min_interval:
                return False
        
        # 记录本次通知
        self.rate_limiter[rate_key].append(now)
        return True
    
    def _record_notification_history(
        self,
        alarm: AlarmTable,
        recipients: Dict[NotificationChannel, List[str]],
        results: Dict[NotificationChannel, bool],
        template_id: Optional[str] = None
    ):
        """记录通知历史"""
        history_entry = {
            "timestamp": datetime.now(),
            "alarm_id": alarm.id,
            "alarm_title": alarm.title,
            "alarm_severity": alarm.severity,
            "recipients": recipients,
            "results": results,
            "template_id": template_id,
            "success_count": sum(1 for success in results.values() if success),
            "total_count": len(results)
        }
        
        self.notification_history.append(history_entry)
        
        # 保持历史记录在合理范围内
        if len(self.notification_history) > 1000:
            self.notification_history = self.notification_history[-1000:]
    
    async def send_batch_notifications(
        self,
        alarms: List[AlarmTable],
        recipients: Dict[NotificationChannel, List[str]],
        template_id: Optional[str] = None,
        user_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[NotificationChannel, bool]]:
        """批量发送通知"""
        results = {}
        
        # 限制并发数量
        semaphore = asyncio.Semaphore(5)
        
        async def send_single(alarm):
            async with semaphore:
                result = await self.send_notification(
                    alarm, recipients, template_id, user_info
                )
                results[str(alarm.id)] = result
                # 避免频率限制
                await asyncio.sleep(0.5)
        
        # 并发发送
        tasks = [send_single(alarm) for alarm in alarms]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def send_summary_notifications(
        self,
        alarms: List[AlarmTable],
        recipients: Dict[NotificationChannel, List[str]],
        summary_type: str = "daily",
        user_info: Optional[Dict[str, Any]] = None
    ) -> Dict[NotificationChannel, bool]:
        """发送汇总通知"""
        results = {}
        
        # 发送邮件汇总
        if NotificationChannel.EMAIL in recipients and NotificationChannel.EMAIL in self.notifiers:
            email_notifier = self.notifiers[NotificationChannel.EMAIL]
            email_recipients = recipients[NotificationChannel.EMAIL]
            
            try:
                success = await email_notifier.send_summary_notification(
                    alarms, email_recipients, summary_type, user_info
                )
                results[NotificationChannel.EMAIL] = success
            except Exception as e:
                logger.error(f"Error sending email summary: {e}")
                results[NotificationChannel.EMAIL] = False
        
        # 发送飞书汇总
        if NotificationChannel.FEISHU in recipients and NotificationChannel.FEISHU in self.notifiers:
            feishu_notifier = self.notifiers[NotificationChannel.FEISHU]
            
            try:
                async with feishu_notifier:
                    success = await feishu_notifier.send_summary_notification(
                        alarms, summary_type, user_info
                    )
                    results[NotificationChannel.FEISHU] = success
            except Exception as e:
                logger.error(f"Error sending Feishu summary: {e}")
                results[NotificationChannel.FEISHU] = False
        
        return results
    
    async def test_all_channels(self, test_config: Dict[NotificationChannel, Dict[str, Any]]) -> Dict[NotificationChannel, bool]:
        """测试所有通知渠道"""
        results = {}
        
        for channel, config in test_config.items():
            if channel in self.notifiers:
                notifier = self.notifiers[channel]
                try:
                    if channel == NotificationChannel.EMAIL:
                        test_email = config.get("test_email")
                        if test_email:
                            success = await notifier.test_connection(test_email)
                            results[channel] = success
                    elif channel == NotificationChannel.FEISHU:
                        async with notifier:
                            success = await notifier.test_connection()
                            results[channel] = success
                except Exception as e:
                    logger.error(f"Error testing {channel.value} channel: {e}")
                    results[channel] = False
        
        return results
    
    def get_notification_statistics(self) -> Dict[str, Any]:
        """获取通知统计信息"""
        if not self.notification_history:
            return {
                "total_notifications": 0,
                "success_rate": 0,
                "channel_stats": {},
                "recent_notifications": []
            }
        
        # 计算统计信息
        total_notifications = len(self.notification_history)
        successful_notifications = sum(
            1 for entry in self.notification_history 
            if entry["success_count"] > 0
        )
        success_rate = successful_notifications / total_notifications if total_notifications > 0 else 0
        
        # 按渠道统计
        channel_stats = {}
        for entry in self.notification_history:
            for channel, success in entry["results"].items():
                channel_name = channel.value
                if channel_name not in channel_stats:
                    channel_stats[channel_name] = {"total": 0, "success": 0}
                
                channel_stats[channel_name]["total"] += 1
                if success:
                    channel_stats[channel_name]["success"] += 1
        
        # 计算各渠道成功率
        for channel_name, stats in channel_stats.items():
            stats["success_rate"] = stats["success"] / stats["total"] if stats["total"] > 0 else 0
        
        # 获取最近的通知记录
        recent_notifications = self.notification_history[-10:]
        
        return {
            "total_notifications": total_notifications,
            "success_rate": success_rate,
            "channel_stats": channel_stats,
            "recent_notifications": [
                {
                    "timestamp": entry["timestamp"].isoformat(),
                    "alarm_title": entry["alarm_title"],
                    "alarm_severity": entry["alarm_severity"],
                    "success_count": entry["success_count"],
                    "total_count": entry["total_count"]
                }
                for entry in recent_notifications
            ]
        }