#!/usr/bin/env python3
"""
创建通知相关数据表
手动执行数据库迁移，创建通知模板、联系点、订阅等表
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


async def create_notification_tables():
    """创建通知相关表"""
    try:
        logger.info("开始创建通知相关数据表...")
        
        # 创建所有表
        async with engine.begin() as conn:
            # 只创建通知相关的表
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ 通知相关数据表创建完成")
        
        # 验证表是否创建成功
        import aiomysql
        
        # 使用固定的数据库连接参数
        conn = await aiomysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='123456',
            db='alarm_system'
        )
        
        try:
            cursor = await conn.cursor()
            
            # 检查新创建的表
            tables_to_check = [
                'notification_templates',
                'contact_points', 
                'user_subscriptions',
                'notification_logs'
            ]
            
            for table_name in tables_to_check:
                await cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                result = await cursor.fetchone()
                if result:
                    logger.info(f"✅ 表 {table_name} 创建成功")
                    
                    # 显示表结构
                    await cursor.execute(f"DESCRIBE {table_name}")
                    columns = await cursor.fetchall()
                    logger.info(f"表 {table_name} 的列:")
                    for col in columns:
                        logger.info(f"  - {col[0]}: {col[1]}")
                else:
                    logger.error(f"❌ 表 {table_name} 创建失败")
            
        finally:
            await conn.ensure_closed()
        
        logger.info("🎉 数据库迁移完成")
        
    except Exception as e:
        logger.error(f"❌ 创建数据表失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(create_notification_tables())