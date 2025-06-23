#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复图表数据 - 生成分布在24小时内的告警数据
"""

import asyncio
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from src.core.database import async_session_maker
from src.models.alarm import AlarmTable
from src.services.collector import AlarmCollector
from sqlalchemy import delete


async def clear_and_regenerate_data():
    """清除现有数据并重新生成分布式时间数据"""
    print("🗑️ 清除现有告警数据...")
    
    # 清除现有数据
    async with async_session_maker() as session:
        await session.execute(delete(AlarmTable))
        await session.commit()
        print("✅ 现有告警数据已清除")
    
    print("📊 生成分布在24小时内的新告警数据...")
    
    collector = AlarmCollector()
    await collector.start()
    
    # 预定义的告警模板
    alarm_templates = [
        {
            "source": "prometheus",
            "title": "CPU使用率过高",
            "description": "服务器CPU使用率超过90%",
            "severity": "high",
            "category": "system",
            "host": "web-server-01",
            "service": "webapp",
            "tags": {"env": "production", "team": "devops"}
        },
        {
            "source": "grafana", 
            "title": "内存使用率告警",
            "description": "内存使用率超过85%",
            "severity": "medium",
            "category": "system", 
            "host": "db-server-01",
            "service": "database",
            "tags": {"env": "production", "team": "dba"}
        },
        {
            "source": "zabbix",
            "title": "磁盘空间不足", 
            "description": "磁盘使用率超过90%",
            "severity": "critical",
            "category": "storage",
            "host": "file-server-01",
            "service": "storage",
            "tags": {"env": "production", "team": "ops"}
        },
        {
            "source": "elasticsearch",
            "title": "搜索响应慢",
            "description": "搜索响应时间超过2秒",
            "severity": "medium",
            "category": "performance",
            "host": "search-server-01",
            "service": "search",
            "tags": {"env": "production", "team": "backend"}
        },
        {
            "source": "nginx",
            "title": "HTTP错误率高",
            "description": "5xx错误率超过5%",
            "severity": "high", 
            "category": "application",
            "host": "lb-01",
            "service": "loadbalancer",
            "tags": {"env": "production", "team": "devops"}
        },
        {
            "source": "mysql",
            "title": "数据库连接多",
            "description": "活跃连接数超过阈值",
            "severity": "medium",
            "category": "database",
            "host": "db-server-02", 
            "service": "mysql",
            "tags": {"env": "production", "team": "dba"}
        },
        {
            "source": "redis",
            "title": "缓存命中率低",
            "description": "缓存命中率低于90%",
            "severity": "low",
            "category": "cache",
            "host": "cache-server-01",
            "service": "redis",
            "tags": {"env": "production", "team": "backend"}
        },
        {
            "source": "kubernetes",
            "title": "Pod重启频繁",
            "description": "Pod重启次数超过阈值",
            "severity": "medium",
            "category": "container", 
            "host": "k8s-node-01",
            "service": "user-service",
            "tags": {"env": "production", "team": "devops"}
        }
    ]
    
    hosts = ["web-server-01", "web-server-02", "web-server-03", "db-server-01", "db-server-02", 
             "cache-server-01", "cache-server-02", "api-server-01", "api-server-02", "lb-01", "monitor-01"]
    
    services = ["webapp", "database", "cache", "api", "loadbalancer", "monitoring", 
                "search", "auth", "payment", "analytics"]
    
    severities = ["critical", "high", "medium", "low", "info"]
    
    # 生成24小时内分布的告警数据
    now = datetime.utcnow()
    success_count = 0
    
    # 每小时生成不同数量的告警（模拟真实的告警分布）
    hourly_patterns = [
        2, 1, 1, 1, 2, 3, 4, 6, 8, 10, 12, 15,  # 0-11点，逐渐增多
        18, 20, 22, 20, 18, 15, 12, 10, 8, 6, 4, 3   # 12-23点，白天多晚上少
    ]
    
    for hour_offset in range(24):
        # 计算这个小时的时间
        hour_time = now - timedelta(hours=23-hour_offset)  # 从24小时前开始
        alarm_count = hourly_patterns[hour_offset]
        
        print(f"⏰ 生成 {hour_time.strftime('%Y-%m-%d %H')}:xx 的 {alarm_count} 个告警")
        
        for i in range(alarm_count):
            # 在这个小时内随机分布
            minute_offset = random.randint(0, 59)
            second_offset = random.randint(0, 59)
            exact_time = hour_time.replace(minute=minute_offset, second=second_offset, microsecond=0)
            
            # 选择告警模板并随机化
            template = random.choice(alarm_templates)
            alarm_data = template.copy()
            
            # 随机化字段
            alarm_data["host"] = random.choice(hosts)
            alarm_data["service"] = random.choice(services) 
            alarm_data["severity"] = random.choice(severities)
            alarm_data["title"] = f"{template['title']} - {alarm_data['host']}"
            
            # 设置状态 - 大部分是活跃的，一些已解决
            if random.random() < 0.7:
                alarm_data["status"] = "active"
            elif random.random() < 0.2:
                alarm_data["status"] = "resolved"
                alarm_data["resolved_at"] = exact_time + timedelta(minutes=random.randint(10, 120))
            else:
                alarm_data["status"] = "acknowledged"
                alarm_data["acknowledged_at"] = exact_time + timedelta(minutes=random.randint(5, 60))
            
            # 移除created_at，让数据库自动设置，然后手动覆盖
            if "created_at" in alarm_data:
                del alarm_data["created_at"]
            
            try:
                # 直接插入数据库而不是通过collector（避免时间被覆盖）
                async with async_session_maker() as session:
                    alarm = AlarmTable(**alarm_data)
                    alarm.created_at = exact_time  # 确保时间正确
                    session.add(alarm)
                    await session.commit()
                    success_count += 1
                    
            except Exception as e:
                print(f"❌ 告警创建失败: {str(e)}")
    
    # 生成当前时间附近的一些新告警（确保有最新数据）
    print("⚡ 生成最近的告警数据...")
    for i in range(10):
        recent_time = now - timedelta(minutes=random.randint(1, 30))
        template = random.choice(alarm_templates)
        alarm_data = template.copy()
        
        alarm_data["host"] = random.choice(hosts)
        alarm_data["service"] = random.choice(services)
        alarm_data["severity"] = random.choice(["critical", "high", "medium"])  # 确保有严重告警
        alarm_data["status"] = "active"  # 确保是活跃状态
        alarm_data["title"] = f"🚨 {template['title']} - {alarm_data['host']}"
        
        try:
            async with async_session_maker() as session:
                alarm = AlarmTable(**alarm_data)
                alarm.created_at = recent_time
                session.add(alarm)
                await session.commit()
                success_count += 1
        except Exception as e:
            print(f"❌ 最近告警创建失败: {str(e)}")
    
    await collector.stop()
    
    print(f"\n✅ 数据重新生成完成!")
    print(f"   📊 成功创建: {success_count} 个告警")
    print(f"   ⏰ 时间跨度: 最近24小时")
    print(f"   📈 现在应该能看到图表数据了!")
    

async def verify_data():
    """验证生成的数据"""
    print("\n🔍 验证生成的数据...")
    
    async with async_session_maker() as session:
        from sqlalchemy import select, func
        
        # 检查总数
        total_result = await session.execute(select(func.count(AlarmTable.id)))
        total = total_result.scalar()
        
        # 检查24小时内的数据
        start_time = datetime.utcnow() - timedelta(hours=24)
        recent_result = await session.execute(
            select(func.count(AlarmTable.id))
            .where(AlarmTable.created_at >= start_time)
        )
        recent_count = recent_result.scalar()
        
        # 检查各状态数量
        status_result = await session.execute(
            select(
                AlarmTable.status,
                func.count(AlarmTable.id).label('count')
            ).group_by(AlarmTable.status)
        )
        status_counts = {row.status: row.count for row in status_result.all()}
        
        # 检查各严重程度数量
        severity_result = await session.execute(
            select(
                AlarmTable.severity,
                func.count(AlarmTable.id).label('count')
            ).group_by(AlarmTable.severity)
        )
        severity_counts = {row.severity: row.count for row in severity_result.all()}
        
        print(f"📊 总告警数量: {total}")
        print(f"⏰ 24小时内: {recent_count}")
        print(f"📋 状态分布: {status_counts}")
        print(f"⚠️ 严重程度分布: {severity_counts}")
        

if __name__ == "__main__":
    asyncio.run(clear_and_regenerate_data())
    asyncio.run(verify_data())