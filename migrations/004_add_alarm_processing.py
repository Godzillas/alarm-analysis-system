"""
添加告警处理流程相关表
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.core.database import engine


async def upgrade():
    """创建告警处理相关表"""
    
    statements = [
        # 告警处理主表
        """
        CREATE TABLE IF NOT EXISTS alarm_processing (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            alarm_id INTEGER NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            priority VARCHAR(10) DEFAULT 'p3',
            assigned_to INTEGER NULL,
            assigned_by INTEGER NULL,
            assigned_at DATETIME NULL,
            acknowledged_by INTEGER NULL,
            acknowledged_at DATETIME NULL,
            acknowledgment_note TEXT NULL,
            resolved_by INTEGER NULL,
            resolved_at DATETIME NULL,
            resolution_method VARCHAR(20) NULL,
            resolution_note TEXT NULL,
            resolution_time_minutes INTEGER NULL,
            closed_by INTEGER NULL,
            closed_at DATETIME NULL,
            close_note TEXT NULL,
            escalated_to INTEGER NULL,
            escalated_by INTEGER NULL,
            escalated_at DATETIME NULL,
            escalation_reason TEXT NULL,
            escalation_level INTEGER DEFAULT 0,
            sla_deadline DATETIME NULL,
            sla_breached BOOLEAN DEFAULT FALSE,
            response_time_minutes INTEGER NULL,
            estimated_effort_hours INTEGER NULL,
            actual_effort_hours INTEGER NULL,
            impact_level VARCHAR(10) NULL,
            affected_users INTEGER NULL,
            business_impact TEXT NULL,
            processing_metadata JSON NULL,
            tags JSON NULL,
            parent_processing_id INTEGER NULL,
            related_alarm_ids JSON NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            INDEX idx_alarm_processing_alarm_id (alarm_id),
            INDEX idx_alarm_processing_status (status),
            INDEX idx_alarm_processing_priority (priority),
            INDEX idx_alarm_processing_assigned_to (assigned_to),
            INDEX idx_alarm_processing_created_at (created_at),
            
            FOREIGN KEY (alarm_id) REFERENCES alarms(id) ON DELETE CASCADE,
            FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (acknowledged_by) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (resolved_by) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (closed_by) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (escalated_to) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (escalated_by) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (parent_processing_id) REFERENCES alarm_processing(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        # 告警处理历史表
        """
        CREATE TABLE IF NOT EXISTS alarm_processing_history (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            processing_id INTEGER NOT NULL,
            action_type VARCHAR(20) NOT NULL,
            action_by INTEGER NOT NULL,
            action_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            old_status VARCHAR(20) NULL,
            new_status VARCHAR(20) NULL,
            old_assigned_to INTEGER NULL,
            new_assigned_to INTEGER NULL,
            action_details JSON NULL,
            notes TEXT NULL,
            ip_address VARCHAR(45) NULL,
            user_agent VARCHAR(500) NULL,
            
            INDEX idx_processing_history_processing_id (processing_id),
            INDEX idx_processing_history_action_type (action_type),
            INDEX idx_processing_history_action_at (action_at),
            
            FOREIGN KEY (processing_id) REFERENCES alarm_processing(id) ON DELETE CASCADE,
            FOREIGN KEY (action_by) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        # 告警处理评论表
        """
        CREATE TABLE IF NOT EXISTS alarm_processing_comments (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            processing_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            comment_type VARCHAR(20) DEFAULT 'general',
            author_id INTEGER NOT NULL,
            author_name VARCHAR(100) NOT NULL,
            visibility VARCHAR(20) DEFAULT 'public',
            attachments JSON NULL,
            metadata JSON NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            INDEX idx_processing_comments_processing_id (processing_id),
            INDEX idx_processing_comments_author_id (author_id),
            INDEX idx_processing_comments_created_at (created_at),
            
            FOREIGN KEY (processing_id) REFERENCES alarm_processing(id) ON DELETE CASCADE,
            FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        # 告警SLA配置表
        """
        CREATE TABLE IF NOT EXISTS alarm_sla (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT NULL,
            severity_mapping JSON NOT NULL,
            priority_sla JSON NOT NULL,
            business_hours_only BOOLEAN DEFAULT FALSE,
            conditions JSON NULL,
            escalation_rules JSON NULL,
            enabled BOOLEAN DEFAULT TRUE,
            priority INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        # 处理解决方案库表
        """
        CREATE TABLE IF NOT EXISTS processing_solutions (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            title VARCHAR(200) NOT NULL,
            description TEXT NOT NULL,
            category VARCHAR(50) NOT NULL,
            tags JSON NULL,
            solution_steps JSON NOT NULL,
            required_tools JSON NULL,
            required_permissions JSON NULL,
            estimated_time_minutes INTEGER NULL,
            applicable_conditions JSON NULL,
            severity_filter JSON NULL,
            source_filter JSON NULL,
            usage_count INTEGER DEFAULT 0,
            success_rate INTEGER DEFAULT 0,
            avg_resolution_time INTEGER NULL,
            version VARCHAR(20) DEFAULT '1.0',
            is_approved BOOLEAN DEFAULT FALSE,
            approved_by INTEGER NULL,
            approved_at DATETIME NULL,
            created_by INTEGER NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            INDEX idx_processing_solutions_category (category),
            INDEX idx_processing_solutions_enabled (enabled),
            INDEX idx_processing_solutions_approved (is_approved),
            INDEX idx_processing_solutions_usage (usage_count),
            
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT,
            FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
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
    
    print("✅ 告警处理流程表创建完成")


async def downgrade():
    """删除告警处理相关表"""
    
    drop_statements = [
        "DROP TABLE IF EXISTS processing_solutions",
        "DROP TABLE IF EXISTS alarm_sla", 
        "DROP TABLE IF EXISTS alarm_processing_comments",
        "DROP TABLE IF EXISTS alarm_processing_history",
        "DROP TABLE IF EXISTS alarm_processing"
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
        print("开始创建告警处理流程表...")
        await upgrade()
        print("告警处理流程表创建完成!")
    
    asyncio.run(main())