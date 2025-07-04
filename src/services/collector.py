"""
告警收集服务
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import deque

import redis.asyncio as redis
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from src.core.config import settings
from src.core.database import async_session_maker
from src.core.logging import get_logger
from src.core.exceptions import DatabaseException, ServiceUnavailableException
from src.models.alarm import AlarmTable, AlarmCreate, AlarmSeverity, AlarmStatus

logger = get_logger(__name__)


@dataclass
class AlarmEvent:
    source: str
    title: str
    description: Optional[str] = None
    severity: str = "medium"
    category: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    host: Optional[str] = None
    service: Optional[str] = None
    environment: Optional[str] = None
    timestamp: Optional[datetime] = None


class AlarmCollector:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.buffer: deque = deque(maxlen=1000)
        self.is_running = False
        self.batch_size = settings.COLLECTOR_BATCH_SIZE
        self.flush_interval = settings.COLLECTOR_FLUSH_INTERVAL
        
    async def start(self):
        if not settings.COLLECTOR_ENABLED:
            logger.info("告警收集器已禁用")
            return
            
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL)
            await self.redis_client.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.warning(f"Redis连接失败: {e}, 使用内存缓冲区")
            self.redis_client = None
            
        self.is_running = True
        asyncio.create_task(self._flush_worker())
        asyncio.create_task(self._redis_consumer())
        logger.info("告警收集器启动成功")
        
    async def stop(self):
        self.is_running = False
        if self.redis_client:
            await self.redis_client.close()
        logger.info("告警收集器已停止")
        
    async def collect_alarm(self, alarm_event: AlarmEvent) -> bool:
        try:
            if self.redis_client:
                await self._send_to_redis(alarm_event)
            else:
                await self._add_to_buffer(alarm_event)
            return True
        except Exception as e:
            logger.error(f"收集告警失败: {e}")
            return False
            
    async def collect_alarm_dict(self, alarm_data: Dict[str, Any]) -> bool:
        try:
            # 告警去重检查
            is_duplicate, original_id = await self._check_deduplication(alarm_data)
            
            if is_duplicate and original_id:
                logger.info(f"检测到重复告警，已更新原始告警 {original_id} 的计数")
                return True  # 重复告警也算处理成功
            
            alarm_event = AlarmEvent(
                source=alarm_data.get("source", "unknown"),
                title=alarm_data.get("title", "未知告警"),
                description=alarm_data.get("description"),
                severity=alarm_data.get("severity", "medium"),
                category=alarm_data.get("category"),
                tags=alarm_data.get("tags"),
                metadata=alarm_data.get("metadata"),
                host=alarm_data.get("host"),
                service=alarm_data.get("service"),
                environment=alarm_data.get("environment"),
                timestamp=alarm_data.get("timestamp")
            )
            
            # 触发关联分析
            await self._trigger_correlation_analysis(alarm_event)
            
            # 触发升级检查
            await self._trigger_escalation_check(alarm_event)
            
            return await self.collect_alarm(alarm_event)
        except Exception as e:
            logger.error(f"解析告警数据失败: {e}")
            return False
            
    async def _send_to_redis(self, alarm_event: AlarmEvent):
        try:
            alarm_data = {
                "source": alarm_event.source,
                "title": alarm_event.title,
                "description": alarm_event.description,
                "severity": alarm_event.severity,
                "category": alarm_event.category,
                "tags": alarm_event.tags,
                "metadata": alarm_event.metadata,
                "host": alarm_event.host,
                "service": alarm_event.service,
                "environment": alarm_event.environment,
                "timestamp": alarm_event.timestamp.isoformat() if alarm_event.timestamp else datetime.utcnow().isoformat()
            }
            await self.redis_client.lpush("alarm_queue", json.dumps(alarm_data))
        except redis.ConnectionError as e:
            logger.warning(f"Redis发送失败，切换到内存缓冲: {e}")
            await self._add_to_buffer(alarm_event)
            await self._reconnect_redis()
        
    async def _add_to_buffer(self, alarm_event: AlarmEvent):
        self.buffer.append(alarm_event)
        
    async def _redis_consumer(self):
        if not self.redis_client:
            return
            
        while self.is_running:
            try:
                # 检查连接状态
                await self.redis_client.ping()
                
                result = await self.redis_client.brpop("alarm_queue", timeout=1)
                if result:
                    _, alarm_data = result
                    alarm_dict = json.loads(alarm_data)
                    
                    if alarm_dict.get("timestamp"):
                        alarm_dict["timestamp"] = datetime.fromisoformat(alarm_dict["timestamp"])
                        
                    alarm_event = AlarmEvent(**alarm_dict)
                    self.buffer.append(alarm_event)
                    
            except redis.ConnectionError as e:
                logger.warning(f"Redis连接错误: {e}, 尝试重连...")
                await self._reconnect_redis()
                await asyncio.sleep(5)
            except redis.TimeoutError:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                logger.error(f"Redis消费者错误: {e}")
                await asyncio.sleep(1)
    
    async def _reconnect_redis(self):
        """重新连接Redis"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            
            self.redis_client = redis.from_url(settings.REDIS_URL)
            await self.redis_client.ping()
            logger.info("Redis重连成功")
        except Exception as e:
            logger.error(f"Redis重连失败: {e}")
            self.redis_client = None
                
    async def _flush_worker(self):
        while self.is_running:
            try:
                if len(self.buffer) >= self.batch_size or len(self.buffer) > 0:
                    await self._flush_buffer()
                await asyncio.sleep(self.flush_interval)
            except Exception as e:
                logger.error(f"刷新缓冲区错误: {e}")
                await asyncio.sleep(1)
                
    async def _flush_buffer(self):
        if not self.buffer:
            return
            
        batch = []
        while self.buffer and len(batch) < self.batch_size:
            batch.append(self.buffer.popleft())
            
        if batch:
            await self._save_alarms(batch)
            
    async def _save_alarms(self, alarm_events: List[AlarmEvent]):
        async with async_session_maker() as session:
            try:
                saved_count = 0
                for alarm_event in alarm_events:
                    existing_alarm = await self._find_similar_alarm(session, alarm_event)
                    
                    if existing_alarm:
                        existing_alarm.count += 1
                        existing_alarm.last_occurrence = datetime.utcnow()
                        existing_alarm.updated_at = datetime.utcnow()
                        
                        if existing_alarm.status == AlarmStatus.RESOLVED:
                            existing_alarm.status = AlarmStatus.ACTIVE
                            existing_alarm.resolved_at = None
                    else:
                        new_alarm = AlarmTable(
                            source=alarm_event.source,
                            title=alarm_event.title,
                            description=alarm_event.description,
                            severity=alarm_event.severity,
                            category=alarm_event.category,
                            tags=alarm_event.tags,
                            metadata=alarm_event.metadata,
                            host=alarm_event.host,
                            service=alarm_event.service,
                            environment=alarm_event.environment,
                            created_at=alarm_event.timestamp or datetime.utcnow(),
                            first_occurrence=alarm_event.timestamp or datetime.utcnow(),
                            last_occurrence=alarm_event.timestamp or datetime.utcnow()
                        )
                        session.add(new_alarm)
                        await session.flush()  # 确保新告警有ID
                        
                        # 为新告警触发升级检查
                        await self._trigger_escalation_for_alarm(new_alarm.id)
                        
                        # 触发通知处理
                        await self._trigger_notification_processing(new_alarm)
                        
                    saved_count += 1
                    
                await session.commit()
                logger.info(f"成功保存 {saved_count} 个告警")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"保存告警失败: {e}")
                
    async def _find_similar_alarm(self, session, alarm_event: AlarmEvent) -> Optional[AlarmTable]:
        try:
            result = await session.execute(
                select(AlarmTable).where(
                    AlarmTable.source == alarm_event.source,
                    AlarmTable.title == alarm_event.title,
                    AlarmTable.host == alarm_event.host,
                    AlarmTable.service == alarm_event.service,
                    AlarmTable.status.in_([AlarmStatus.ACTIVE, AlarmStatus.ACKNOWLEDGED])
                ).order_by(AlarmTable.created_at.desc())
            )
            return result.scalars().first()
        except Exception as e:
            logger.error(f"查找相似告警失败: {e}")
            return None
            
    async def _trigger_correlation_analysis(self, alarm_event: AlarmEvent):
        """触发关联分析"""
        try:
            from src.services.correlation_engine import correlation_engine
            # 异步启动关联分析，不阻塞告警收集
            try:
                asyncio.create_task(correlation_engine.analyze_correlations())
            except RuntimeError:
                # 如果没有运行的事件循环，跳过关联分析
                logger.warning("No event loop running, skipping correlation analysis")
        except Exception as e:
            logger.error(f"触发关联分析失败: {e}")
    
    async def _trigger_escalation_check(self, alarm_event: AlarmEvent):
        """触发升级检查"""
        try:
            # 对于高严重级别的告警，检查是否需要立即升级
            if alarm_event.severity in ['critical', 'high']:
                from src.services.escalation_engine import escalation_engine
                # 这里可以添加自动升级逻辑
                logger.info(f"高严重级别告警: {alarm_event.title}, 可能需要升级")
        except Exception as e:
            logger.error(f"触发升级检查失败: {e}")
    
    async def _check_deduplication(self, alarm_data: Dict[str, Any]) -> Tuple[bool, Optional[int]]:
        """检查告警去重"""
        try:
            from src.services.deduplication_engine import process_alarm_deduplication
            return await process_alarm_deduplication(alarm_data)
        except Exception as e:
            logger.error(f"去重检查失败: {e}")
            return False, None
    
    async def _trigger_escalation_for_alarm(self, alarm_id: int):
        """为特定告警触发升级"""
        try:
            from src.services.escalation_engine import escalation_engine
            # 异步触发升级，不阻塞告警保存
            asyncio.create_task(escalation_engine.trigger_escalation(alarm_id))
        except Exception as e:
            logger.error(f"为告警 {alarm_id} 触发升级失败: {e}")
    
    async def _trigger_notification_processing(self, alarm: AlarmTable):
        """触发通知处理"""
        try:
            from src.services.notification_engine import process_alarm_for_notifications
            # 异步触发通知处理，不阻塞告警保存
            asyncio.create_task(process_alarm_for_notifications(alarm))
            logger.debug(f"已触发告警 {alarm.id} 的通知处理")
        except Exception as e:
            logger.error(f"为告警 {alarm.id} 触发通知处理失败: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        return {
            "buffer_size": len(self.buffer),
            "is_running": self.is_running,
            "redis_connected": self.redis_client is not None,
            "batch_size": self.batch_size,
            "flush_interval": self.flush_interval
        }