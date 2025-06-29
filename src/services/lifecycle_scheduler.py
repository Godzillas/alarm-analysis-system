"""
告警生命周期事件调度器
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from src.core.logging import get_logger
from src.services.alarm_lifecycle_manager import lifecycle_manager

logger = get_logger(__name__)


class LifecycleScheduler:
    """生命周期事件调度器"""
    
    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.logger = logger
    
    async def start(self):
        """启动调度器"""
        if self.running:
            self.logger.warning("生命周期调度器已在运行")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        self.logger.info(f"生命周期调度器已启动，处理间隔: {self.interval_seconds}秒")
    
    async def stop(self):
        """停止调度器"""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("生命周期调度器已停止")
    
    async def _run_scheduler(self):
        """运行调度器主循环"""
        while self.running:
            try:
                start_time = datetime.utcnow()
                
                # 处理生命周期事件
                await lifecycle_manager.process_lifecycle_events()
                
                # 计算处理时间
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                
                self.logger.debug(
                    f"生命周期事件处理完成，耗时: {processing_time:.2f}秒"
                )
                
                # 等待下一次处理
                await asyncio.sleep(self.interval_seconds)
                
            except asyncio.CancelledError:
                # 调度器被取消
                break
            except Exception as e:
                self.logger.error(f"生命周期事件处理失败: {str(e)}")
                # 发生错误时，等待较短时间后重试
                await asyncio.sleep(min(30, self.interval_seconds))
    
    async def trigger_immediate_processing(self):
        """立即触发一次生命周期事件处理"""
        try:
            start_time = datetime.utcnow()
            await lifecycle_manager.process_lifecycle_events()
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(f"立即处理生命周期事件完成，耗时: {processing_time:.2f}秒")
            
        except Exception as e:
            self.logger.error(f"立即处理生命周期事件失败: {str(e)}")
            raise


# 全局调度器实例
lifecycle_scheduler = LifecycleScheduler(interval_seconds=60)