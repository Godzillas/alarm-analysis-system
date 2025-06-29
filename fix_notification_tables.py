#!/usr/bin/env python3
"""
修复通知表结构
删除旧的通知表，使用新的模型定义重新创建
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.database import engine, Base
from src.models.alarm import (
    NotificationTemplate, ContactPoint, UserSubscription, NotificationLog
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def fix_notification_tables():
    """修复通知表结构"""
    try:
        logger.info("开始修复通知表结构...")
        
        async with engine.begin() as conn:
            # 删除旧的通知相关表
            logger.info("删除旧的通知表...")
            
            old_tables = [
                'notification_logs',
                'user_subscriptions', 
                'contact_points',
                'notification_templates',
                'alarm_notifications',  # 旧表
                'notification_channels',  # 旧表  
                'notification_digests'   # 旧表
            ]
            
            for table in old_tables:
                try:
                    await conn.execute(f"DROP TABLE IF EXISTS {table}")
                    logger.info(f"删除表: {table}")
                except Exception as e:
                    logger.warning(f"删除表 {table} 时出错: {e}")
            
            logger.info("重新创建通知表...")
            
            # 创建新的表结构
            # 只创建通知相关的表
            tables_to_create = [
                NotificationTemplate.__table__,
                ContactPoint.__table__,
                UserSubscription.__table__,
                NotificationLog.__table__
            ]
            
            for table in tables_to_create:
                await conn.run_sync(table.create)
                logger.info(f"创建表: {table.name}")
        
        logger.info("✅ 通知表结构修复完成")
        
        # 验证新表结构
        logger.info("验证新表结构...")
        
        import subprocess
        import shlex
        
        tables_to_verify = [
            'notification_templates',
            'contact_points',
            'user_subscriptions', 
            'notification_logs'
        ]
        
        for table_name in tables_to_verify:
            try:
                cmd = f"mysql -u root -e 'USE alarm_system; DESCRIBE {table_name};'"
                result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"✅ 表 {table_name} 结构:")
                    for line in result.stdout.strip().split('\n')[1:]:  # 跳过头行
                        if line:
                            logger.info(f"  {line}")
                else:
                    logger.error(f"❌ 无法获取表 {table_name} 结构: {result.stderr}")
            except Exception as e:
                logger.error(f"验证表 {table_name} 时出错: {e}")
        
        logger.info("🎉 数据库表结构修复完成")
        
    except Exception as e:
        logger.error(f"❌ 修复表结构失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(fix_notification_tables())