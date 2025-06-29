"""
通知发送引擎
负责告警匹配、通知创建和发送的核心引擎
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_maker
from src.core.logging import get_logger
from src.core.exceptions import DatabaseException
from src.models.alarm import AlarmTable, UserSubscription, NotificationLog
from src.services.notification_service import notification_service

logger = get_logger(__name__)


class NotificationEngine:
    """通知发送引擎"""
    
    def __init__(self):
        self.logger = logger
        self.notification_service = notification_service
        self.is_running = False
        self.processing_queue = asyncio.Queue()
        self.worker_tasks = []
    
    async def start(self, worker_count: int = 3):
        """启动通知引擎"""
        if self.is_running:
            self.logger.warning("Notification engine is already running")
            return
        
        self.is_running = True
        
        # 启动工作器
        self.worker_tasks = [
            asyncio.create_task(self._notification_worker(f"worker-{i}"))
            for i in range(worker_count)
        ]
        
        # 启动重试任务
        retry_task = asyncio.create_task(self._retry_worker())
        self.worker_tasks.append(retry_task)
        
        self.logger.info(f"Notification engine started with {worker_count} workers")
    
    async def stop(self):
        """停止通知引擎"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 取消所有工作器任务
        for task in self.worker_tasks:
            task.cancel()
        
        # 等待任务完成
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        self.worker_tasks.clear()
        
        self.logger.info("Notification engine stopped")
    
    async def process_alarm(self, alarm: AlarmTable):
        """处理新告警，触发通知"""
        try:
            # 将告警放入处理队列
            await self.processing_queue.put({
                "type": "alarm",
                "alarm_id": alarm.id,
                "timestamp": datetime.utcnow()
            })
            
            self.logger.debug(
                f"Alarm {alarm.id} queued for notification processing",
                extra={"alarm_id": alarm.id, "severity": alarm.severity}
            )
            
        except Exception as e:
            self.logger.error(f"Error queuing alarm {alarm.id}: {str(e)}")
    
    async def send_test_notification(
        self,
        user_id: int,
        channel_config: Dict[str, Any],
        test_message: str
    ) -> bool:
        """发送测试通知"""
        try:
            async with async_session_maker() as session:
                # 创建测试通知记录
                test_notification = NotificationLog(
                    subscription_id=0,  # 测试用的虚拟订阅ID
                    alarm_id=0,  # 测试用的虚拟告警ID
                    contact_point_id=0,  # 测试用的虚拟联系点ID
                    status="pending",
                    notification_content={
                        "subject": "测试通知",
                        "content": test_message,
                        "channel_type": channel_config.get("channel_type", "test"),
                        "recipient": channel_config.get("recipient", "test@example.com")
                    }
                )
                
                session.add(test_notification)
                await session.commit()
                
                self.logger.info(
                    f"Test notification created",
                    extra={
                        "user_id": user_id,
                        "channel": channel_config.get("channel_type", "test"),
                        "notification_id": test_notification.id
                    }
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error sending test notification: {str(e)}")
            return False
    
    async def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        queue_size = self.processing_queue.qsize()
        
        return {
            "is_running": self.is_running,
            "worker_count": len(self.worker_tasks),
            "queue_size": queue_size,
            "workers_status": [
                {
                    "name": task.get_name(),
                    "done": task.done(),
                    "cancelled": task.cancelled()
                }
                for task in self.worker_tasks
            ]
        }
    
    # 私有方法
    
    async def _notification_worker(self, worker_name: str):
        """通知处理工作器"""
        self.logger.info(f"Notification worker {worker_name} started")
        
        try:
            while self.is_running:
                try:
                    # 从队列获取任务，设置超时避免阻塞
                    task = await asyncio.wait_for(
                        self.processing_queue.get(),
                        timeout=1.0
                    )
                    
                    await self._process_notification_task(task, worker_name)
                    
                except asyncio.TimeoutError:
                    # 超时是正常的，继续循环
                    continue
                except Exception as e:
                    self.logger.error(
                        f"Error in notification worker {worker_name}: {str(e)}",
                        extra={"worker": worker_name}
                    )
                    # 短暂休息后继续
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            self.logger.info(f"Notification worker {worker_name} cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Notification worker {worker_name} crashed: {str(e)}")
        finally:
            self.logger.info(f"Notification worker {worker_name} stopped")
    
    async def _process_notification_task(self, task: Dict[str, Any], worker_name: str):
        """处理单个通知任务"""
        task_type = task.get("type")
        
        if task_type == "alarm":
            await self._process_alarm_notification(task["alarm_id"], worker_name)
        elif task_type == "retry":
            await self._process_retry_notifications(worker_name)
        else:
            self.logger.warning(f"Unknown task type: {task_type}")
    
    async def _process_alarm_notification(self, alarm_id: int, worker_name: str):
        """处理告警通知"""
        try:
            # 使用新的告警分发服务
            from src.services.alarm_dispatch import alarm_dispatch_service
            await alarm_dispatch_service.dispatch_alarm(alarm_id, is_update=False)
            
            self.logger.debug(
                f"Alarm {alarm_id} dispatched for notification processing",
                extra={"alarm_id": alarm_id, "worker": worker_name}
            )
                
        except Exception as e:
            self.logger.error(
                f"Error processing alarm {alarm_id} in {worker_name}: {str(e)}",
                extra={"alarm_id": alarm_id, "worker": worker_name}
            )
    
    async def _retry_worker(self):
        """重试失败通知的工作器"""
        self.logger.info("Retry worker started")
        
        try:
            while self.is_running:
                try:
                    # 每5分钟检查一次需要重试的通知
                    await asyncio.sleep(300)
                    
                    if not self.is_running:
                        break
                    
                    retry_count = await self.notification_service.retry_failed_notifications()
                    
                    if retry_count > 0:
                        self.logger.info(f"Retried {retry_count} failed notifications")
                    
                except Exception as e:
                    self.logger.error(f"Error in retry worker: {str(e)}")
                    await asyncio.sleep(60)  # 出错后等待更长时间
                    
        except asyncio.CancelledError:
            self.logger.info("Retry worker cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Retry worker crashed: {str(e)}")
        finally:
            self.logger.info("Retry worker stopped")
    
    async def _process_retry_notifications(self, worker_name: str):
        """处理重试通知任务"""
        try:
            retry_count = await self.notification_service.retry_failed_notifications(max_age_hours=6)
            
            if retry_count > 0:
                self.logger.info(
                    f"Worker {worker_name} retried {retry_count} notifications",
                    extra={"worker": worker_name, "retry_count": retry_count}
                )
                
        except Exception as e:
            self.logger.error(
                f"Error processing retry notifications in {worker_name}: {str(e)}",
                extra={"worker": worker_name}
            )


# 全局通知引擎实例
notification_engine = NotificationEngine()


async def process_alarm_for_notifications(alarm: AlarmTable):
    """处理告警的通知发送（供外部调用）"""
    await notification_engine.process_alarm(alarm)


async def start_notification_engine():
    """启动通知引擎（供应用启动时调用）"""
    await notification_engine.start()


async def stop_notification_engine():
    """停止通知引擎（供应用关闭时调用）"""
    await notification_engine.stop()


async def get_notification_engine_status():
    """获取通知引擎状态（供监控使用）"""
    return await notification_engine.get_engine_status()