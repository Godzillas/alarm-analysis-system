#!/usr/bin/env python3
"""
测试通知集成功能
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
from src.services.alarm_dispatch import alarm_dispatch_service
from src.services.default_templates import ensure_default_templates_exist
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def create_test_user(session):
    """创建测试用户"""
    user = User(
        username="test_user",
        email="test@example.com", 
        password_hash="test_hash",
        full_name="Test User",
        is_active=True
    )
    session.add(user)
    await session.flush()
    return user


async def create_test_contact_point(session, template_id):
    """创建测试联系点"""
    contact_point = ContactPoint(
        name="测试飞书机器人",
        description="用于测试的飞书机器人联系点",
        contact_type="feishu",
        config={
            "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/test-webhook-url",
            "message_type": "interactive",
            "add_action_buttons": True
        },
        template_id=template_id,
        enabled=True,
        created_by=1
    )
    session.add(contact_point)
    await session.flush()
    return contact_point


async def create_test_subscription(session, user_id, contact_point_id):
    """创建测试订阅"""
    subscription = UserSubscription(
        name="测试告警订阅",
        description="用于测试的告警订阅",
        user_id=user_id,
        subscription_type="real_time",
        filters={
            "or": [
                {"field": "severity", "operator": "in", "value": ["critical", "high"]},
                {"field": "source", "operator": "contains", "value": "test"}
            ]
        },
        contact_points=[contact_point_id],
        notification_schedule={},
        cooldown_minutes=0,
        max_notifications_per_hour=0,
        enabled=True
    )
    session.add(subscription)
    await session.flush()
    return subscription


async def create_test_alarm(session):
    """创建测试告警"""
    alarm = AlarmTable(
        source="test_system",
        title="测试告警 - 系统CPU使用率过高",
        description="系统CPU使用率达到95%，超过阈值",
        severity="critical",
        status="active",
        category="performance",
        host="test-server-01",
        service="cpu-monitor",
        environment="production",
        tags={"team": "ops", "app": "monitoring"}
    )
    session.add(alarm)
    await session.flush()
    return alarm


async def test_notification_system():
    """测试通知系统"""
    try:
        # 初始化数据库
        await init_db()
        logger.info("✅ 数据库初始化完成")
        
        async with async_session_maker() as session:
            # 1. 创建默认模板
            await ensure_default_templates_exist(session)
            logger.info("✅ 默认模板创建完成")
            
            # 2. 获取飞书模板
            from sqlalchemy import select
            query = select(NotificationTemplate).where(
                NotificationTemplate.content_type == "feishu"
            )
            result = await session.execute(query)
            feishu_template = result.scalars().first()
            
            if not feishu_template:
                logger.error("❌ 没有找到飞书模板")
                return
            
            logger.info(f"✅ 找到飞书模板: {feishu_template.name}")
            
            # 3. 创建测试用户
            user = await create_test_user(session)
            logger.info(f"✅ 创建测试用户: {user.username}")
            
            # 4. 创建测试联系点
            contact_point = await create_test_contact_point(session, feishu_template.id)
            logger.info(f"✅ 创建测试联系点: {contact_point.name}")
            
            # 5. 创建测试订阅
            subscription = await create_test_subscription(session, user.id, contact_point.id)
            logger.info(f"✅ 创建测试订阅: {subscription.name}")
            
            # 6. 创建测试告警
            alarm = await create_test_alarm(session)
            logger.info(f"✅ 创建测试告警: {alarm.title}")
            
            await session.commit()
            
            # 7. 启动分发服务
            await alarm_dispatch_service.start()
            logger.info("✅ 告警分发服务启动")
            
            # 8. 分发告警
            await alarm_dispatch_service.dispatch_alarm(alarm.id, is_update=False)
            logger.info("✅ 告警已分发")
            
            # 9. 等待处理完成
            await asyncio.sleep(2)
            
            # 10. 检查通知日志
            query = select(NotificationLog).where(NotificationLog.alarm_id == alarm.id)
            result = await session.execute(query)
            notifications = result.scalars().all()
            
            if notifications:
                logger.info(f"✅ 创建了 {len(notifications)} 个通知")
                for notif in notifications:
                    logger.info(f"  - 通知ID: {notif.id}, 状态: {notif.status}")
            else:
                logger.warning("⚠️  没有创建通知")
            
            # 11. 停止分发服务
            await alarm_dispatch_service.stop()
            logger.info("✅ 告警分发服务停止")
            
        logger.info("🎉 通知系统测试完成")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_notification_system())