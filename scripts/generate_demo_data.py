#!/usr/bin/env python3
"""
告警分析系统 - 模拟数据生成脚本
生成真实的告警数据用于演示和测试
"""

import os
import sys
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import aiosqlite
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.models.alarm import AlarmTable
from src.core.database import Base

# 数据库配置
DATABASE_URL = "sqlite+aiosqlite:///./alarm_system.db"

# 模拟数据配置
SYSTEMS = [
    "payment-service", "user-service", "order-service", "inventory-service",
    "notification-service", "auth-service", "gateway-service", "analytics-service",
    "search-service", "recommendation-service"
]

COMPONENTS = {
    "payment-service": ["payment-api", "payment-db", "payment-queue", "risk-engine"],
    "user-service": ["user-api", "user-db", "user-cache", "session-manager"],
    "order-service": ["order-api", "order-db", "order-processor", "inventory-check"],
    "inventory-service": ["inventory-api", "inventory-db", "stock-updater"],
    "notification-service": ["email-sender", "sms-sender", "push-notifier"],
    "auth-service": ["auth-api", "token-service", "ldap-connector"],
    "gateway-service": ["api-gateway", "load-balancer", "rate-limiter"],
    "analytics-service": ["data-collector", "report-generator", "ml-engine"],
    "search-service": ["search-api", "elasticsearch", "indexer"],
    "recommendation-service": ["rec-api", "rec-model", "feature-store"]
}

ENVIRONMENTS = ["production", "staging", "test", "development"]

TEAMS = [
    "platform-team", "payment-team", "user-team", "order-team", 
    "infra-team", "security-team", "data-team", "mobile-team"
]

METRICS = [
    "cpu_usage", "memory_usage", "disk_usage", "response_time", 
    "error_rate", "throughput", "database_connections", "queue_size",
    "network_latency", "cache_hit_rate", "api_success_rate", "disk_io"
]

SEVERITIES = ["critical", "high", "medium", "low", "info"]
STATUSES = ["active", "acknowledged", "resolved"]

ALARM_TEMPLATES = [
    {
        "title_template": "High CPU usage on {component}",
        "description_template": "CPU usage is {value}% on {component} in {environment}",
        "metric": "cpu_usage",
        "severity_weights": {"critical": 0.3, "high": 0.4, "medium": 0.2, "low": 0.1}
    },
    {
        "title_template": "Memory usage exceeded on {component}",
        "description_template": "Memory usage is {value}% on {component}, threshold exceeded",
        "metric": "memory_usage", 
        "severity_weights": {"critical": 0.25, "high": 0.35, "medium": 0.3, "low": 0.1}
    },
    {
        "title_template": "High error rate in {component}",
        "description_template": "Error rate is {value}% in {component} service",
        "metric": "error_rate",
        "severity_weights": {"critical": 0.4, "high": 0.3, "medium": 0.2, "low": 0.1}
    },
    {
        "title_template": "Slow response time for {component}",
        "description_template": "Response time is {value}ms for {component} API",
        "metric": "response_time",
        "severity_weights": {"critical": 0.2, "high": 0.3, "medium": 0.4, "low": 0.1}
    },
    {
        "title_template": "Database connection pool exhausted",
        "description_template": "Database connections: {value}/{max_connections} on {component}",
        "metric": "database_connections",
        "severity_weights": {"critical": 0.5, "high": 0.3, "medium": 0.15, "low": 0.05}
    },
    {
        "title_template": "Disk space low on {component}",
        "description_template": "Disk usage is {value}% on {component} server",
        "metric": "disk_usage",
        "severity_weights": {"critical": 0.35, "high": 0.35, "medium": 0.25, "low": 0.05}
    }
]

def weighted_choice(choices: Dict[str, float]) -> str:
    """根据权重随机选择"""
    total = sum(choices.values())
    r = random.uniform(0, total)
    upto = 0
    for choice, weight in choices.items():
        if upto + weight >= r:
            return choice
        upto += weight
    return list(choices.keys())[-1]

def generate_alarm_data(days_back: int = 30, alarms_per_day: int = 50) -> List[Dict[str, Any]]:
    """生成告警数据"""
    alarms = []
    
    # 生成过去几天的告警
    for day in range(days_back):
        date = datetime.now() - timedelta(days=day)
        
        # 每天的告警数量有波动
        daily_count = random.randint(int(alarms_per_day * 0.5), int(alarms_per_day * 1.5))
        
        for _ in range(daily_count):
            # 选择系统和组件
            system = random.choice(SYSTEMS)
            component = random.choice(COMPONENTS[system])
            environment = random.choice(ENVIRONMENTS)
            team = random.choice(TEAMS)
            
            # 选择告警模板
            template = random.choice(ALARM_TEMPLATES)
            severity = weighted_choice(template["severity_weights"])
            
            # 生成告警时间（在该天内随机分布）
            alarm_time = date.replace(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            # 生成指标值
            metric_value = None
            if template["metric"] in ["cpu_usage", "memory_usage", "disk_usage"]:
                if severity == "critical":
                    metric_value = random.randint(90, 100)
                elif severity == "high":
                    metric_value = random.randint(80, 89)
                elif severity == "medium":
                    metric_value = random.randint(70, 79)
                else:
                    metric_value = random.randint(50, 69)
            elif template["metric"] == "error_rate":
                if severity == "critical":
                    metric_value = round(random.uniform(10, 50), 2)
                elif severity == "high":
                    metric_value = round(random.uniform(5, 10), 2)
                else:
                    metric_value = round(random.uniform(1, 5), 2)
            elif template["metric"] == "response_time":
                if severity == "critical":
                    metric_value = random.randint(5000, 30000)
                elif severity == "high":
                    metric_value = random.randint(2000, 5000)
                else:
                    metric_value = random.randint(500, 2000)
            elif template["metric"] == "database_connections":
                max_conn = 100
                if severity == "critical":
                    metric_value = random.randint(95, 100)
                elif severity == "high":
                    metric_value = random.randint(85, 94)
                else:
                    metric_value = random.randint(70, 84)
            
            # 生成告警状态
            if day > 7:  # 7天前的告警大部分已解决
                status = random.choices(
                    ["resolved", "acknowledged", "active"],
                    weights=[0.8, 0.15, 0.05]
                )[0]
            elif day > 1:  # 1-7天前的告警部分已处理
                status = random.choices(
                    ["resolved", "acknowledged", "active"], 
                    weights=[0.6, 0.25, 0.15]
                )[0]
            else:  # 最近的告警大部分还是活跃的
                status = random.choices(
                    ["active", "acknowledged", "resolved"],
                    weights=[0.7, 0.2, 0.1]
                )[0]
            
            # 生成告警内容
            title = template["title_template"].format(
                component=component,
                system=system,
                environment=environment
            )
            
            description = template["description_template"].format(
                component=component,
                system=system,
                environment=environment,
                value=metric_value,
                max_connections=100 if template["metric"] == "database_connections" else ""
            )
            
            # 生成标签
            tags = {
                "system": system,
                "component": component,
                "environment": environment,
                "team": team,
                "metric": template["metric"],
                "source": random.choice(["grafana", "prometheus", "cloudwatch", "custom"]),
                "region": random.choice(["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]),
                "cluster": f"{environment}-cluster-{random.randint(1, 3)}"
            }
            
            # 处理时间
            acknowledged_at = None
            resolved_at = None
            
            if status in ["acknowledged", "resolved"]:
                # 确认时间在告警后几分钟到几小时
                ack_delay = timedelta(minutes=random.randint(5, 120))
                acknowledged_at = alarm_time + ack_delay
                
            if status == "resolved":
                # 解决时间在确认后或告警后
                resolve_base = acknowledged_at if acknowledged_at else alarm_time
                resolve_delay = timedelta(minutes=random.randint(10, 480))
                resolved_at = resolve_base + resolve_delay
            
            # 生成告警数据
            alarm = {
                "title": title,
                "description": description,
                "severity": severity,
                "status": status,
                "source": tags["source"],
                "tags": tags,
                "metadata": {
                    "metric_value": metric_value,
                    "threshold": metric_value * 0.8 if metric_value else None,
                    "instance": f"{component}-{random.randint(1, 10)}",
                    "alert_rule": f"{template['metric']}_threshold",
                    "dashboard_url": f"https://grafana.example.com/dashboard/{system}",
                    "runbook_url": f"https://wiki.example.com/runbooks/{system}/{component}"
                },
                "fingerprint": f"{system}_{component}_{template['metric']}_{environment}",
                "created_at": alarm_time,
                "acknowledged_at": acknowledged_at,
                "resolved_at": resolved_at,
                "updated_at": resolved_at or acknowledged_at or alarm_time
            }
            
            alarms.append(alarm)
    
    return alarms

async def clear_existing_data():
    """清空现有数据"""
    print("🗑️  清空现有告警数据...")
    
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("✅ 数据库重置完成")

async def insert_demo_data(alarms: List[Dict[str, Any]]):
    """插入演示数据"""
    print(f"📥 插入 {len(alarms)} 条告警数据...")
    
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    batch_size = 100
    inserted = 0
    
    async with async_session() as session:
        for i in range(0, len(alarms), batch_size):
            batch = alarms[i:i + batch_size]
            
            for alarm_data in batch:
                alarm = AlarmTable(
                    title=alarm_data["title"],
                    description=alarm_data["description"],
                    severity=alarm_data["severity"],
                    status=alarm_data["status"],
                    source=alarm_data["source"],
                    tags=alarm_data["tags"],
                    alarm_metadata=alarm_data["metadata"],
                    created_at=alarm_data["created_at"],
                    acknowledged_at=alarm_data["acknowledged_at"],
                    resolved_at=alarm_data["resolved_at"],
                    updated_at=alarm_data["updated_at"]
                )
                session.add(alarm)
            
            await session.commit()
            inserted += len(batch)
            print(f"  已插入 {inserted}/{len(alarms)} 条记录...")
    
    await engine.dispose()
    print("✅ 数据插入完成")

def print_statistics(alarms: List[Dict[str, Any]]):
    """打印数据统计"""
    print("\n📊 数据统计:")
    print(f"总告警数: {len(alarms)}")
    
    # 按严重程度统计
    severity_stats = {}
    for alarm in alarms:
        severity = alarm["severity"]
        severity_stats[severity] = severity_stats.get(severity, 0) + 1
    
    print("\n严重程度分布:")
    for severity, count in sorted(severity_stats.items()):
        percentage = (count / len(alarms)) * 100
        print(f"  {severity}: {count} ({percentage:.1f}%)")
    
    # 按状态统计
    status_stats = {}
    for alarm in alarms:
        status = alarm["status"]
        status_stats[status] = status_stats.get(status, 0) + 1
    
    print("\n状态分布:")
    for status, count in sorted(status_stats.items()):
        percentage = (count / len(alarms)) * 100
        print(f"  {status}: {count} ({percentage:.1f}%)")
    
    # 按系统统计
    system_stats = {}
    for alarm in alarms:
        system = alarm["tags"]["system"]
        system_stats[system] = system_stats.get(system, 0) + 1
    
    print("\n系统分布 (Top 5):")
    sorted_systems = sorted(system_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    for system, count in sorted_systems:
        percentage = (count / len(alarms)) * 100
        print(f"  {system}: {count} ({percentage:.1f}%)")

async def main():
    """主函数"""
    print("🚀 告警分析系统 - 模拟数据生成器")
    print("=" * 50)
    
    # 配置参数
    days_back = 30  # 生成过去30天的数据
    alarms_per_day = 80  # 每天平均80个告警
    
    print(f"📅 生成时间范围: 过去 {days_back} 天")
    print(f"📈 预期告警数量: ~{days_back * alarms_per_day} 条")
    print()
    
    try:
        # 清空现有数据
        await clear_existing_data()
        
        # 生成模拟数据
        print("🎲 生成模拟告警数据...")
        alarms = generate_alarm_data(days_back, alarms_per_day)
        
        # 按时间排序
        alarms.sort(key=lambda x: x["created_at"])
        
        # 插入数据库
        await insert_demo_data(alarms)
        
        # 打印统计信息
        print_statistics(alarms)
        
        print(f"\n🎉 模拟数据生成完成!")
        print(f"💾 数据库文件: alarm_system.db")
        print(f"🌐 访问系统: http://localhost:8000")
        
    except Exception as e:
        print(f"❌ 生成数据时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())