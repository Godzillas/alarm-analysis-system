"""
添加统一的通知订阅系统
使用新的模型定义重新创建通知相关表
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.core.database import engine


async def upgrade():
    """创建统一的通知订阅相关表"""
    
    statements = [
        # 通知模板表（新结构）
        """
        CREATE TABLE IF NOT EXISTS notification_templates (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT NULL,
            template_type VARCHAR(20) NOT NULL,
            content_type VARCHAR(20) NOT NULL,
            title_template TEXT NOT NULL,
            content_template TEXT NOT NULL,
            footer_template TEXT NULL,
            variables JSON NULL,
            style_config JSON NULL,
            is_system_template BOOLEAN DEFAULT FALSE,
            enabled BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_by INTEGER NULL,
            
            INDEX idx_notification_templates_type (template_type),
            INDEX idx_notification_templates_content_type (content_type),
            INDEX idx_notification_templates_enabled (enabled),
            INDEX idx_notification_templates_system (is_system_template),
            
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        # 联系点表
        """
        CREATE TABLE IF NOT EXISTS contact_points (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT NULL,
            contact_type VARCHAR(20) NOT NULL,
            config JSON NOT NULL,
            template_id INTEGER NULL,
            retry_count INTEGER DEFAULT 3,
            retry_interval INTEGER DEFAULT 300,
            timeout INTEGER DEFAULT 30,
            last_test_at DATETIME NULL,
            last_test_success BOOLEAN NULL,
            test_error_message TEXT NULL,
            total_sent INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            last_sent DATETIME NULL,
            last_success DATETIME NULL,
            last_failure DATETIME NULL,
            system_id INTEGER NULL,
            enabled BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_by INTEGER NULL,
            
            INDEX idx_contact_points_type (contact_type),
            INDEX idx_contact_points_enabled (enabled),
            INDEX idx_contact_points_system (system_id),
            
            FOREIGN KEY (template_id) REFERENCES notification_templates(id) ON DELETE SET NULL,
            FOREIGN KEY (system_id) REFERENCES systems(id) ON DELETE SET NULL,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        # 用户订阅表
        """
        CREATE TABLE IF NOT EXISTS user_subscriptions (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT NULL,
            user_id INTEGER NOT NULL,
            subscription_type VARCHAR(20) NOT NULL,
            filters JSON NOT NULL,
            contact_points JSON NOT NULL,
            notification_schedule JSON NULL,
            cooldown_minutes INTEGER DEFAULT 0,
            max_notifications_per_hour INTEGER DEFAULT 0,
            escalation_rules JSON NULL,
            enabled BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            last_notification_at DATETIME NULL,
            total_notifications_sent INTEGER DEFAULT 0,
            
            INDEX idx_user_subscriptions_user_id (user_id),
            INDEX idx_user_subscriptions_type (subscription_type),
            INDEX idx_user_subscriptions_enabled (enabled),
            INDEX idx_user_subscriptions_created_at (created_at),
            
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        # 通知日志表
        """
        CREATE TABLE IF NOT EXISTS notification_logs (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            subscription_id INTEGER NOT NULL,
            alarm_id INTEGER NOT NULL,
            contact_point_id INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL,
            error_message TEXT NULL,
            retry_count INTEGER DEFAULT 0,
            notification_content JSON NULL,
            sent_at DATETIME NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            INDEX idx_notification_logs_subscription_id (subscription_id),
            INDEX idx_notification_logs_alarm_id (alarm_id),
            INDEX idx_notification_logs_contact_point_id (contact_point_id),
            INDEX idx_notification_logs_status (status),
            INDEX idx_notification_logs_created_at (created_at),
            
            FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id) ON DELETE CASCADE,
            FOREIGN KEY (alarm_id) REFERENCES alarms(id) ON DELETE CASCADE,
            FOREIGN KEY (contact_point_id) REFERENCES contact_points(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    ]
    
    async with engine.begin() as conn:
        for statement in statements:
            try:
                await conn.execute(text(statement))
                # 提取表名用于日志
                table_name = statement.split("TABLE")[1].split("(")[0].strip().replace("IF NOT EXISTS", "").strip()
                print(f"✅ 创建表成功: {table_name}")
            except Exception as e:
                table_name = statement.split("TABLE")[1].split("(")[0].strip().replace("IF NOT EXISTS", "").strip()
                print(f"❌ 创建表失败: {table_name} - {str(e)}")
                # 继续执行其他语句，不中断
                continue
    
    print("✅ 统一通知订阅表创建完成")


async def downgrade():
    """删除统一的通知订阅相关表"""
    
    drop_statements = [
        "SET FOREIGN_KEY_CHECKS = 0",
        "DROP TABLE IF EXISTS notification_logs",
        "DROP TABLE IF EXISTS user_subscriptions", 
        "DROP TABLE IF EXISTS contact_points",
        "DROP TABLE IF EXISTS notification_templates",
        "SET FOREIGN_KEY_CHECKS = 1"
    ]
    
    async with engine.begin() as conn:
        for statement in drop_statements:
            try:
                await conn.execute(text(statement))
                print(f"✅ 执行成功: {statement}")
            except Exception as e:
                print(f"❌ 执行失败: {statement} - {str(e)}")


if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("开始创建统一通知订阅表...")
        await upgrade()
        print("统一通知订阅表创建完成!")
    
    asyncio.run(main())