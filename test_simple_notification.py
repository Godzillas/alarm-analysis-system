#!/usr/bin/env python3
"""
简单通知测试 - 测试飞书通知功能
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.database import init_db, async_session_maker
from src.models.alarm import (
    AlarmTable, NotificationTemplate, ContactPoint, UserSubscription,
    NotificationLog, User
)
from src.services.notification_service import FeishuSender
from src.services.default_templates import ensure_default_templates_exist
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_feishu_notification():
    """测试飞书通知发送"""
    try:
        # 初始化数据库
        await init_db()
        logger.info("✅ 数据库初始化完成")
        
        # 测试飞书发送器
        feishu_config = {
            "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/test-webhook-url",
            "message_type": "interactive",
            "add_action_buttons": True
        }
        
        # 创建临时通知对象
        class MockNotification:
            def __init__(self):
                self.id = 1
                self.subscription_id = 1
                self.alarm_id = 1
                self.contact_point_id = 1
                self.status = "pending"
                self.priority = "urgent"
                self.subject = "测试告警通知"
                self.content = """
**告警详情:**
- **严重程度:** critical
- **状态:** active
- **来源:** test_system
- **描述:** 这是一个测试告警
- **主机:** test-server-01
- **服务:** test-service
- **环境:** production
- **创建时间:** 2024-01-01 12:00:00

**订阅信息:**
- **订阅名称:** 测试订阅
                """.strip()
                self.notification_content = {
                    "subject": self.subject,
                    "content": self.content,
                    "priority": self.priority
                }
                from datetime import datetime
                self.created_at = datetime.utcnow()
        
        mock_notification = MockNotification()
        
        # 创建飞书发送器
        feishu_sender = FeishuSender(feishu_config)
        
        # 验证配置
        config_valid = await feishu_sender.validate_config()
        logger.info(f"✅ 飞书配置验证: {'有效' if config_valid else '无效'}")
        
        # 构建消息
        message = feishu_sender._build_feishu_message(mock_notification)
        logger.info("✅ 飞书消息构建完成")
        logger.info(f"消息类型: {message.get('msg_type')}")
        
        if message.get('msg_type') == 'interactive' and 'card' in message:
            card = message['card']
            logger.info(f"卡片标题: {card.get('header', {}).get('title', {}).get('content', 'N/A')}")
            logger.info(f"卡片元素数量: {len(card.get('elements', []))}")
        
        # 注意：这里不实际发送到飞书，因为webhook URL是测试用的
        logger.info("✅ 飞书通知测试完成（未实际发送）")
        
        # 测试创建默认模板
        async with async_session_maker() as session:
            await ensure_default_templates_exist(session)
            logger.info("✅ 默认模板检查完成")
            
            # 检查模板
            from sqlalchemy import select
            query = select(NotificationTemplate).where(
                NotificationTemplate.content_type == "feishu"
            )
            result = await session.execute(query)
            feishu_template = result.scalars().first()
            
            if feishu_template:
                logger.info(f"✅ 找到飞书模板: {feishu_template.name}")
            else:
                logger.warning("⚠️  没有找到飞书模板")
        
        logger.info("🎉 简单通知测试完成")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_feishu_notification())