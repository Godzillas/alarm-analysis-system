"""
任务调度服务
"""

import asyncio
import logging
from datetime import datetime, timedelta
import schedule
import time
import threading

from src.core.database import async_session_maker
from src.models.alarm import AlarmTable, AlarmStatus
from sqlalchemy import select, update

logger = logging.getLogger(__name__)


def start_scheduler():
    """启动调度器"""
    schedule.every(10).minutes.do(cleanup_old_alarms)
    schedule.every(1).hours.do(generate_reports)
    schedule.every(1).days.do(archive_old_alarms)
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("调度器启动成功")


def cleanup_old_alarms():
    """清理旧告警"""
    asyncio.create_task(_cleanup_old_alarms())


def generate_reports():
    """生成报告"""
    asyncio.create_task(_generate_reports())


def archive_old_alarms():
    """归档旧告警"""
    asyncio.create_task(_archive_old_alarms())


async def _cleanup_old_alarms():
    """清理已解决的旧告警"""
    async with async_session_maker() as session:
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=7)
            
            result = await session.execute(
                select(AlarmTable).where(
                    AlarmTable.status == AlarmStatus.RESOLVED,
                    AlarmTable.resolved_at < cutoff_time
                )
            )
            
            old_alarms = result.scalars().all()
            
            for alarm in old_alarms:
                await session.delete(alarm)
                
            await session.commit()
            
            if old_alarms:
                logger.info(f"清理了 {len(old_alarms)} 个旧告警")
                
        except Exception as e:
            await session.rollback()
            logger.error(f"清理旧告警失败: {e}")


async def _generate_reports():
    """生成定期报告"""
    try:
        logger.info("生成定期报告")
        
    except Exception as e:
        logger.error(f"生成报告失败: {e}")


async def _archive_old_alarms():
    """归档旧告警"""
    try:
        logger.info("归档旧告警")
        
    except Exception as e:
        logger.error(f"归档告警失败: {e}")