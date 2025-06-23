#!/usr/bin/env python3
"""
创建示例数据
"""

import asyncio
import random
import json
from datetime import datetime, timedelta
from typing import List

# 添加项目路径
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.database import async_session_maker, init_db
from src.models.alarm import (
    AlarmTable, AlarmSeverity, AlarmStatus,
    Endpoint, EndpointType,
    User, UserSubscription,
    RuleGroup, DistributionRule
)


class SampleDataCreator:
    def __init__(self):
        self.sample_sources = [
            "nginx", "redis", "mysql", "mongodb", "elasticsearch", "kafka", 
            "kubernetes", "docker", "jenkins", "prometheus", "grafana", "zabbix"
        ]
        
        self.sample_hosts = [
            "web-01", "web-02", "web-03", "db-01", "db-02", "cache-01", "cache-02",
            "api-01", "api-02", "worker-01", "worker-02", "lb-01", "monitor-01"
        ]
        
        self.sample_services = [
            "frontend", "backend", "database", "cache", "message-queue", "monitoring",
            "logging", "search", "analytics", "payment", "notification", "auth"
        ]
        
        self.sample_environments = ["production", "staging", "development", "testing"]
        
        self.alarm_templates = [
            {
                "title": "CPU使用率过高",
                "description": "服务器CPU使用率超过90%，持续时间超过5分钟",
                "category": "performance"
            },
            {
                "title": "内存使用率告警",
                "description": "内存使用率超过85%，可能影响服务性能",
                "category": "performance"
            },
            {
                "title": "磁盘空间不足",
                "description": "磁盘使用率超过95%，需要清理或扩容",
                "category": "storage"
            },
            {
                "title": "数据库连接异常",
                "description": "数据库连接池耗尽，新连接请求被拒绝",
                "category": "database"
            },
            {
                "title": "API响应时间过长",
                "description": "API平均响应时间超过2秒，用户体验受影响",
                "category": "performance"
            },
            {
                "title": "服务不可用",
                "description": "服务健康检查失败，服务可能已停止",
                "category": "availability"
            },
            {
                "title": "缓存命中率低",
                "description": "Redis缓存命中率低于70%，性能下降",
                "category": "cache"
            },
            {
                "title": "消息队列积压",
                "description": "消息队列中待处理消息数量超过1000",
                "category": "queue"
            },
            {
                "title": "SSL证书即将过期",
                "description": "SSL证书将在7天内过期，请及时更新",
                "category": "security"
            },
            {
                "title": "异常登录尝试",
                "description": "检测到异常IP地址的登录尝试",
                "category": "security"
            },
            {
                "title": "网络连接异常",
                "description": "网络延迟超过500ms，连接不稳定",
                "category": "network"
            },
            {
                "title": "日志错误率上升",
                "description": "错误日志数量在过去1小时内增长200%",
                "category": "logging"
            }
        ]

    async def create_all_sample_data(self):
        """创建所有示例数据"""
        print("🚀 开始创建示例数据...")
        
        await init_db()
        
        # 创建用户
        users = await self.create_sample_users()
        print(f"✅ 创建了 {len(users)} 个用户")
        
        # 创建接入点
        endpoints = await self.create_sample_endpoints()
        print(f"✅ 创建了 {len(endpoints)} 个接入点")
        
        # 创建规则组和规则
        rule_groups = await self.create_sample_rules()
        print(f"✅ 创建了 {len(rule_groups)} 个规则组")
        
        # 创建用户订阅
        subscriptions = await self.create_sample_subscriptions(users)
        print(f"✅ 创建了 {len(subscriptions)} 个用户订阅")
        
        # 创建告警数据
        alarms = await self.create_sample_alarms()
        print(f"✅ 创建了 {len(alarms)} 个告警")
        
        print("\n🎉 示例数据创建完成！")
        print(f"📊 系统概览:")
        print(f"   - 用户数量: {len(users)}")
        print(f"   - 接入点数量: {len(endpoints)}")
        print(f"   - 规则组数量: {len(rule_groups)}")
        print(f"   - 告警数量: {len(alarms)}")
        print(f"   - 订阅数量: {len(subscriptions)}")

    async def create_sample_users(self) -> List[User]:
        """创建示例用户"""
        users_data = [
            {
                "username": "admin",
                "email": "admin@company.com",
                "password_hash": "admin123:hashedpassword",
                "full_name": "系统管理员",
                "is_admin": True,
                "is_active": True
            },
            {
                "username": "ops_manager",
                "email": "ops@company.com",
                "password_hash": "ops123:hashedpassword",
                "full_name": "运维经理",
                "is_admin": False,
                "is_active": True
            },
            {
                "username": "dev_lead",
                "email": "dev@company.com",
                "password_hash": "dev123:hashedpassword",
                "full_name": "开发主管",
                "is_admin": False,
                "is_active": True
            },
            {
                "username": "monitor_user",
                "email": "monitor@company.com",
                "password_hash": "monitor123:hashedpassword",
                "full_name": "监控专员",
                "is_admin": False,
                "is_active": True
            },
            {
                "username": "security_analyst",
                "email": "security@company.com",
                "password_hash": "security123:hashedpassword",
                "full_name": "安全分析师",
                "is_admin": False,
                "is_active": True
            }
        ]
        
        users = []
        async with async_session_maker() as session:
            for user_data in users_data:
                user = User(**user_data)
                session.add(user)
                users.append(user)
            
            await session.commit()
            for user in users:
                await session.refresh(user)
        
        return users

    async def create_sample_endpoints(self) -> List[Endpoint]:
        """创建示例接入点"""
        endpoints_data = [
            {
                "name": "Nginx监控",
                "description": "Nginx服务器监控告警",
                "endpoint_type": EndpointType.HTTP,
                "config": {
                    "url": "http://nginx-monitor.company.com/alerts",
                    "headers": {"Authorization": "Bearer nginx_token"},
                    "field_mapping": {
                        "title": "alert_name",
                        "description": "alert_description",
                        "severity": "alert_level",
                        "host": "server_name"
                    }
                },
                "enabled": True,
                "rate_limit": 500,
                "timeout": 30,
                "auth_token": "nginx_endpoint_token_123"
            },
            {
                "name": "数据库告警",
                "description": "MySQL和Redis数据库告警",
                "endpoint_type": EndpointType.WEBHOOK,
                "config": {
                    "webhook_url": "http://db-monitor.company.com/webhook",
                    "secret": "db_webhook_secret",
                    "field_mapping": {
                        "title": "event_title",
                        "description": "event_message",
                        "severity": "priority",
                        "host": "hostname"
                    }
                },
                "enabled": True,
                "rate_limit": 1000,
                "timeout": 60,
                "auth_token": "db_endpoint_token_456"
            },
            {
                "name": "Kubernetes集群",
                "description": "K8s集群告警接入",
                "endpoint_type": EndpointType.API,
                "config": {
                    "api_endpoint": "https://k8s-api.company.com/api/v1/alerts",
                    "api_key": "k8s_api_key",
                    "namespace": "monitoring",
                    "field_mapping": {
                        "title": "alertname",
                        "description": "annotations.description",
                        "severity": "labels.severity",
                        "host": "labels.instance"
                    }
                },
                "enabled": True,
                "rate_limit": 2000,
                "timeout": 45,
                "auth_token": "k8s_endpoint_token_789"
            },
            {
                "name": "邮件告警",
                "description": "邮件系统告警通知",
                "endpoint_type": EndpointType.EMAIL,
                "config": {
                    "smtp_server": "smtp.company.com",
                    "smtp_port": 587,
                    "username": "alerts@company.com",
                    "use_tls": True,
                    "field_mapping": {
                        "title": "subject",
                        "description": "body",
                        "severity": "priority"
                    }
                },
                "enabled": True,
                "rate_limit": 100,
                "timeout": 60,
                "auth_token": "email_endpoint_token_abc"
            },
            {
                "name": "Syslog服务器",
                "description": "系统日志告警",
                "endpoint_type": EndpointType.SYSLOG,
                "config": {
                    "syslog_server": "syslog.company.com",
                    "syslog_port": 514,
                    "protocol": "UDP",
                    "facility": "local0",
                    "field_mapping": {
                        "title": "message",
                        "severity": "priority",
                        "host": "hostname"
                    }
                },
                "enabled": True,
                "rate_limit": 1000,
                "timeout": 30,
                "auth_token": "syslog_endpoint_token_def"
            }
        ]
        
        endpoints = []
        async with async_session_maker() as session:
            for endpoint_data in endpoints_data:
                endpoint = Endpoint(**endpoint_data)
                session.add(endpoint)
                endpoints.append(endpoint)
            
            await session.commit()
            for endpoint in endpoints:
                await session.refresh(endpoint)
        
        return endpoints

    async def create_sample_rules(self) -> List[RuleGroup]:
        """创建示例规则"""
        rule_groups_data = [
            {
                "name": "生产环境规则",
                "description": "生产环境告警处理规则",
                "priority": 100,
                "enabled": True
            },
            {
                "name": "安全告警规则",
                "description": "安全相关告警处理",
                "priority": 90,
                "enabled": True
            },
            {
                "name": "性能监控规则",
                "description": "性能相关告警处理",
                "priority": 80,
                "enabled": True
            }
        ]
        
        rule_groups = []
        async with async_session_maker() as session:
            for group_data in rule_groups_data:
                group = RuleGroup(**group_data)
                session.add(group)
                rule_groups.append(group)
            
            await session.commit()
            for group in rule_groups:
                await session.refresh(group)
                
            # 为每个规则组创建分发规则
            distribution_rules = [
                {
                    "name": "严重告警立即通知",
                    "rule_group_id": rule_groups[0].id,
                    "conditions": {
                        "and": [
                            {"field": "severity", "operator": "equals", "value": "critical"},
                            {"field": "environment", "operator": "equals", "value": "production"}
                        ]
                    },
                    "actions": {
                        "notify_users": [1, 2],  # 管理员和运维经理
                        "add_tags": {"priority": "urgent", "escalation": "level1"}
                    },
                    "priority": 100,
                    "enabled": True
                },
                {
                    "name": "安全告警通知",
                    "rule_group_id": rule_groups[1].id,
                    "conditions": {
                        "or": [
                            {"field": "category", "operator": "equals", "value": "security"},
                            {"field": "title", "operator": "contains", "value": "登录"}
                        ]
                    },
                    "actions": {
                        "notify_users": [5],  # 安全分析师
                        "add_tags": {"type": "security", "reviewed": "false"}
                    },
                    "priority": 90,
                    "enabled": True
                },
                {
                    "name": "性能告警分发",
                    "rule_group_id": rule_groups[2].id,
                    "conditions": {
                        "and": [
                            {"field": "category", "operator": "equals", "value": "performance"},
                            {"field": "severity", "operator": "in", "value": ["high", "medium"]}
                        ]
                    },
                    "actions": {
                        "notify_users": [3, 4],  # 开发主管和监控专员
                        "add_tags": {"team": "performance", "auto_resolve": "true"}
                    },
                    "priority": 80,
                    "enabled": True
                }
            ]
            
            for rule_data in distribution_rules:
                rule = DistributionRule(**rule_data)
                session.add(rule)
            
            await session.commit()
        
        return rule_groups

    async def create_sample_subscriptions(self, users: List[User]) -> List[UserSubscription]:
        """创建示例用户订阅"""
        subscriptions_data = [
            {
                "user_id": users[1].id,  # 运维经理
                "subscription_type": "severity",
                "filters": {
                    "severity": {"in": ["critical", "high"]},
                    "environment": {"equals": "production"}
                },
                "notification_methods": ["email", "webhook"],
                "enabled": True
            },
            {
                "user_id": users[2].id,  # 开发主管
                "subscription_type": "category",
                "filters": {
                    "category": {"in": ["performance", "database"]},
                    "service": {"in": ["backend", "database"]}
                },
                "notification_methods": ["email"],
                "enabled": True
            },
            {
                "user_id": users[3].id,  # 监控专员
                "subscription_type": "all",
                "filters": {},
                "notification_methods": ["email", "webhook"],
                "enabled": True
            },
            {
                "user_id": users[4].id,  # 安全分析师
                "subscription_type": "category",
                "filters": {
                    "category": {"equals": "security"}
                },
                "notification_methods": ["email", "sms"],
                "enabled": True
            }
        ]
        
        subscriptions = []
        async with async_session_maker() as session:
            for sub_data in subscriptions_data:
                subscription = UserSubscription(**sub_data)
                session.add(subscription)
                subscriptions.append(subscription)
            
            await session.commit()
            for subscription in subscriptions:
                await session.refresh(subscription)
        
        return subscriptions

    async def create_sample_alarms(self) -> List[AlarmTable]:
        """创建示例告警数据"""
        alarms = []
        current_time = datetime.utcnow()
        
        async with async_session_maker() as session:
            # 创建最近7天的告警数据
            for day in range(7):
                day_start = current_time - timedelta(days=day)
                
                # 每天创建不同数量的告警
                daily_alarm_count = random.randint(20, 50)
                
                for i in range(daily_alarm_count):
                    # 随机时间分布
                    alarm_time = day_start - timedelta(
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59),
                        seconds=random.randint(0, 59)
                    )
                    
                    # 选择告警模板
                    template = random.choice(self.alarm_templates)
                    
                    # 随机选择属性
                    source = random.choice(self.sample_sources)
                    host = random.choice(self.sample_hosts)
                    service = random.choice(self.sample_services)
                    environment = random.choice(self.sample_environments)
                    
                    # 根据环境调整严重程度分布
                    if environment == "production":
                        severity_weights = [0.1, 0.3, 0.4, 0.15, 0.05]  # 生产环境更多高严重程度
                    else:
                        severity_weights = [0.05, 0.15, 0.3, 0.3, 0.2]  # 非生产环境更多低严重程度
                    
                    severity = random.choices(
                        [AlarmSeverity.CRITICAL, AlarmSeverity.HIGH, AlarmSeverity.MEDIUM, AlarmSeverity.LOW, AlarmSeverity.INFO],
                        weights=severity_weights
                    )[0]
                    
                    # 根据创建时间决定状态
                    if day < 2:  # 最近2天的告警，部分仍为活跃状态
                        status_weights = [0.6, 0.3, 0.1, 0.0]
                    else:  # 较早的告警，大部分已解决
                        status_weights = [0.1, 0.7, 0.15, 0.05]
                    
                    status = random.choices(
                        [AlarmStatus.ACTIVE, AlarmStatus.RESOLVED, AlarmStatus.ACKNOWLEDGED, AlarmStatus.SUPPRESSED],
                        weights=status_weights
                    )[0]
                    
                    # 设置解决时间
                    resolved_at = None
                    acknowledged_at = None
                    
                    if status == AlarmStatus.RESOLVED:
                        resolved_at = alarm_time + timedelta(
                            hours=random.randint(1, 12),
                            minutes=random.randint(0, 59)
                        )
                    elif status == AlarmStatus.ACKNOWLEDGED:
                        acknowledged_at = alarm_time + timedelta(
                            minutes=random.randint(5, 120)
                        )
                    
                    # 创建告警
                    alarm = AlarmTable(
                        source=source,
                        title=f"{template['title']} - {host}",
                        description=f"{template['description']} 主机: {host}, 服务: {service}",
                        severity=severity,
                        status=status,
                        category=template['category'],
                        tags={
                            "team": random.choice(["ops", "dev", "security", "platform"]),
                            "criticality": random.choice(["high", "medium", "low"]),
                            "auto_generated": True
                        },
                        alarm_metadata={
                            "source_ip": f"10.0.{random.randint(1, 255)}.{random.randint(1, 255)}",
                            "metric_value": round(random.uniform(70, 95), 2),
                            "threshold": random.choice([80, 85, 90, 95]),
                            "duration": f"{random.randint(1, 60)}m"
                        },
                        created_at=alarm_time,
                        updated_at=resolved_at or acknowledged_at or alarm_time,
                        resolved_at=resolved_at,
                        acknowledged_at=acknowledged_at,
                        host=host,
                        service=service,
                        environment=environment,
                        count=random.randint(1, 5),
                        first_occurrence=alarm_time,
                        last_occurrence=alarm_time + timedelta(minutes=random.randint(0, 30)),
                        is_duplicate=random.choice([True, False]) if random.random() < 0.1 else False,
                        similarity_score=round(random.uniform(0.7, 0.95), 2) if random.random() < 0.1 else None
                    )
                    
                    session.add(alarm)
                    alarms.append(alarm)
            
            await session.commit()
            for alarm in alarms:
                await session.refresh(alarm)
        
        return alarms


async def main():
    """主函数"""
    creator = SampleDataCreator()
    await creator.create_all_sample_data()


if __name__ == "__main__":
    asyncio.run(main())