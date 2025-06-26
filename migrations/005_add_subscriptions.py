"""
添加告警订阅和通知相关表
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.core.database import engine


async def upgrade():
    """创建订阅和通知相关表"""
    
    statements = [
        # 通知模板表
        """
        CREATE TABLE IF NOT EXISTS notification_templates (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT NULL,
            template_type VARCHAR(20) NOT NULL,
            channel_type VARCHAR(20) NOT NULL,
            subject_template TEXT NULL,
            content_template TEXT NOT NULL,
            html_template TEXT NULL,
            available_variables JSON NULL,
            required_variables JSON NULL,
            format_config JSON NULL,
            applicable_channels JSON NULL,
            severity_filter JSON NULL,
            version VARCHAR(20) DEFAULT '1.0',
            is_default BOOLEAN DEFAULT FALSE,
            is_system BOOLEAN DEFAULT FALSE,
            usage_count INTEGER DEFAULT 0,
            last_used DATETIME NULL,
            enabled BOOLEAN DEFAULT TRUE,
            created_by INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            INDEX idx_notification_templates_type (template_type),
            INDEX idx_notification_templates_channel (channel_type),
            INDEX idx_notification_templates_enabled (enabled),
            INDEX idx_notification_templates_default (is_default),
            
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        # 告警订阅表
        """
        CREATE TABLE IF NOT EXISTS alarm_subscriptions (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT NULL,
            user_id INTEGER NOT NULL,
            team_id INTEGER NULL,
            subscription_type VARCHAR(20) DEFAULT 'immediate',
            enabled BOOLEAN DEFAULT TRUE,
            filter_conditions JSON NOT NULL,
            notification_channels JSON NOT NULL,
            notification_template_id INTEGER NULL,
            schedule_config JSON NULL,
            timezone VARCHAR(50) DEFAULT 'UTC',
            quiet_hours JSON NULL,
            holiday_config JSON NULL,
            rate_limit_config JSON NULL,
            escalation_config JSON NULL,
            total_notifications INTEGER DEFAULT 0,
            successful_notifications INTEGER DEFAULT 0,
            failed_notifications INTEGER DEFAULT 0,
            last_notification_at DATETIME NULL,
            subscription_metadata JSON NULL,
            tags JSON NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            INDEX idx_alarm_subscriptions_user_id (user_id),
            INDEX idx_alarm_subscriptions_type (subscription_type),
            INDEX idx_alarm_subscriptions_enabled (enabled),
            INDEX idx_alarm_subscriptions_created_at (created_at),
            
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (notification_template_id) REFERENCES notification_templates(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        # 告警通知记录表
        """
        CREATE TABLE IF NOT EXISTS alarm_notifications (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            alarm_id INTEGER NOT NULL,
            subscription_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            notification_type VARCHAR(20) NOT NULL,
            channel VARCHAR(20) NOT NULL,
            recipient VARCHAR(255) NOT NULL,
            subject VARCHAR(500) NULL,
            content TEXT NOT NULL,
            html_content TEXT NULL,
            attachments JSON NULL,
            status VARCHAR(20) DEFAULT 'pending',
            priority VARCHAR(20) DEFAULT 'normal',
            scheduled_at DATETIME NULL,
            sent_at DATETIME NULL,
            delivered_at DATETIME NULL,
            read_at DATETIME NULL,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            next_retry_at DATETIME NULL,
            error_message TEXT NULL,
            error_code VARCHAR(50) NULL,
            external_id VARCHAR(255) NULL,
            webhook_url VARCHAR(500) NULL,
            notification_config JSON NULL,
            processing_time_ms INTEGER NULL,
            delivery_time_ms INTEGER NULL,
            notification_metadata JSON NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            INDEX idx_alarm_notifications_alarm_id (alarm_id),
            INDEX idx_alarm_notifications_subscription_id (subscription_id),
            INDEX idx_alarm_notifications_user_id (user_id),
            INDEX idx_alarm_notifications_type (notification_type),
            INDEX idx_alarm_notifications_channel (channel),
            INDEX idx_alarm_notifications_status (status),
            INDEX idx_alarm_notifications_priority (priority),
            INDEX idx_alarm_notifications_created_at (created_at),
            INDEX idx_alarm_notifications_scheduled_at (scheduled_at),
            INDEX idx_alarm_notifications_retry (next_retry_at),
            
            FOREIGN KEY (alarm_id) REFERENCES alarms(id) ON DELETE CASCADE,
            FOREIGN KEY (subscription_id) REFERENCES alarm_subscriptions(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        # 通知渠道配置表
        """
        CREATE TABLE IF NOT EXISTS notification_channels (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT NULL,
            channel_type VARCHAR(20) NOT NULL,
            connection_config JSON NOT NULL,
            auth_config JSON NULL,
            rate_limit_per_minute INTEGER DEFAULT 60,
            rate_limit_per_hour INTEGER DEFAULT 1000,
            rate_limit_per_day INTEGER DEFAULT 10000,
            retry_config JSON NULL,
            health_check_config JSON NULL,
            last_health_check DATETIME NULL,
            is_healthy BOOLEAN DEFAULT TRUE,
            total_sent INTEGER DEFAULT 0,
            successful_sent INTEGER DEFAULT 0,
            failed_sent INTEGER DEFAULT 0,
            last_sent DATETIME NULL,
            cost_per_message VARCHAR(10) NULL,
            enabled BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            INDEX idx_notification_channels_type (channel_type),
            INDEX idx_notification_channels_enabled (enabled),
            INDEX idx_notification_channels_health (is_healthy)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        # 通知摘要表
        """
        CREATE TABLE IF NOT EXISTS notification_digests (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            subscription_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            period_start DATETIME NOT NULL,
            period_end DATETIME NOT NULL,
            digest_type VARCHAR(20) NOT NULL,
            alarm_count INTEGER DEFAULT 0,
            critical_count INTEGER DEFAULT 0,
            high_count INTEGER DEFAULT 0,
            medium_count INTEGER DEFAULT 0,
            low_count INTEGER DEFAULT 0,
            alarm_summary JSON NOT NULL,
            trend_analysis JSON NULL,
            is_sent BOOLEAN DEFAULT FALSE,
            sent_at DATETIME NULL,
            notification_id INTEGER NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            INDEX idx_notification_digests_subscription_id (subscription_id),
            INDEX idx_notification_digests_user_id (user_id),
            INDEX idx_notification_digests_period (period_start, period_end),
            INDEX idx_notification_digests_type (digest_type),
            INDEX idx_notification_digests_sent (is_sent),
            INDEX idx_notification_digests_created_at (created_at),
            
            FOREIGN KEY (subscription_id) REFERENCES alarm_subscriptions(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (notification_id) REFERENCES alarm_notifications(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    ]
    
    async with engine.begin() as conn:
        for statement in statements:
            try:
                await conn.execute(text(statement))
                print(f"✅ 执行成功: {statement.split()[2]}")
            except Exception as e:
                print(f"❌ 执行失败: {statement.split()[2]} - {str(e)}")
                # 继续执行其他语句，不中断
                continue
    
    print("✅ 告警订阅和通知表创建完成")


async def downgrade():
    """删除订阅和通知相关表"""
    
    drop_statements = [
        "DROP TABLE IF EXISTS notification_digests",
        "DROP TABLE IF EXISTS notification_channels",
        "DROP TABLE IF EXISTS alarm_notifications",
        "DROP TABLE IF EXISTS alarm_subscriptions",
        "DROP TABLE IF EXISTS notification_templates"
    ]
    
    async with engine.begin() as conn:
        for statement in drop_statements:
            try:
                await conn.execute(text(statement))
                print(f"✅ 删除成功: {statement}")
            except Exception as e:
                print(f"❌ 删除失败: {statement} - {str(e)}")


if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("开始创建告警订阅和通知表...")
        await upgrade()
        print("告警订阅和通知表创建完成!")
    
    asyncio.run(main())