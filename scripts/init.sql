-- 初始化告警系统数据库

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS alarm_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE alarm_system;

-- 创建默认管理员用户（密码：admin123456）
-- 密码哈希: $2b$12$LQv3c1yqBWVHxkd0LQ7lqOu5TdVQrn3IrNq6lWZHzQS9uJE9rMNBC
INSERT IGNORE INTO users (id, username, email, password_hash, full_name, is_active, is_admin, created_at) 
VALUES (1, 'admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LQ7lqOu5TdVQrn3IrNq6lWZHzQS9uJE9rMNBC', '系统管理员', true, true, NOW());

-- 创建默认系统
INSERT IGNORE INTO systems (id, name, description, code, owner, enabled, created_at)
VALUES (1, '演示系统', '告警系统演示', 'DEMO', 'admin', true, NOW());

-- 创建默认接入点
INSERT IGNORE INTO endpoints (id, name, description, endpoint_type, config, enabled, system_id, api_token, webhook_url, created_at)
VALUES (1, 'Webhook接入点', 'Webhook告警接入', 'webhook', '{"url": "/api/webhook/alarm/demo-token"}', true, 1, 'demo-token', '/api/webhook/alarm/demo-token', NOW());

-- 创建默认联络点
INSERT IGNORE INTO contact_points (id, name, description, contact_type, config, enabled, system_id, created_at)
VALUES (1, '测试邮件通知', '测试邮件通知联络点', 'email', '{"smtp_host": "smtp.qq.com", "smtp_port": 587, "username": "test@qq.com", "password": "test", "from_addr": "test@qq.com", "to_addrs": ["admin@example.com"]}', false, 1, NOW());

-- 创建默认告警模板
INSERT IGNORE INTO alert_templates (id, name, description, category, template_type, title_template, content_template, enabled, is_default, system_id, created_at)
VALUES (1, '默认告警模板', '系统默认告警通知模板', 'system', 'simple', '【{{severity}}】{{title}}', '告警详情:\n标题: {{title}}\n描述: {{description}}\n级别: {{severity}}\n状态: {{status}}\n来源: {{source}}\n时间: {{created_at}}', true, true, 1, NOW());

-- 用户系统关联
INSERT IGNORE INTO user_systems (user_id, system_id, created_at)
VALUES (1, 1, NOW());