#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单生成图表数据 - 使用SQL直接插入
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
from sqlalchemy import delete


async def generate_chart_data():
    """生成图表数据"""
    print("🗑️ 清除现有数据...")
    
    # 清除现有数据
    async with async_session_maker() as session:
        await session.execute(delete(AlarmTable))
        await session.commit()
        print("✅ 现有数据已清除")
    
    print("📊 生成24小时内的告警数据...")
    
    now = datetime.utcnow()
    sources = ["prometheus", "grafana", "zabbix", "elasticsearch", "nginx", "mysql", "redis", "kubernetes"]
    hosts = ["web-01", "web-02", "db-01", "db-02", "cache-01", "api-01", "lb-01"]
    services = ["webapp", "database", "cache", "api", "loadbalancer"]
    severities = ["critical", "high", "medium", "low", "info"]
    statuses = ["active", "resolved", "acknowledged"]
    
    success_count = 0
    
    # 每小时生成不同数量的告警
    hourly_counts = [2, 1, 1, 2, 3, 4, 6, 8, 10, 12, 15, 18, 20, 22, 20, 18, 15, 12, 10, 8, 6, 4, 3, 2]
    
    for hour_offset in range(24):
        hour_time = now - timedelta(hours=23-hour_offset)
        count = hourly_counts[hour_offset]
        
        print(f"⏰ {hour_time.strftime('%H:00')} - 生成 {count} 个告警")
        
        for i in range(count):
            # 在这个小时内随机分布
            random_time = hour_time + timedelta(
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            
            # 创建告警对象
            alarm = AlarmTable(
                source=random.choice(sources),
                title=f"告警 #{hour_offset}-{i}",
                description=f"在{random_time.strftime('%H:%M')}发生的告警",
                severity=random.choice(severities),
                status=random.choice(statuses),
                category="system",
                host=random.choice(hosts),
                service=random.choice(services),
                environment="production",
                created_at=random_time,
                updated_at=random_time,
                tags={"auto": "true"},
                count=1
            )
            
            # 设置解决或确认时间
            if alarm.status == "resolved":
                alarm.resolved_at = random_time + timedelta(minutes=random.randint(10, 120))
            elif alarm.status == "acknowledged":
                alarm.acknowledged_at = random_time + timedelta(minutes=random.randint(5, 60))
            
            try:
                async with async_session_maker() as session:
                    session.add(alarm)
                    await session.commit()
                    success_count += 1
            except Exception as e:
                print(f"❌ 创建失败: {str(e)}")
    
    print(f"\n✅ 生成完成!")
    print(f"   📊 成功: {success_count}")
    print(f"   📈 现在图表应该有数据了!")
    

async def test_api():
    """测试API返回"""
    print("\n🔍 测试API数据...")
    
    async with async_session_maker() as session:
        from sqlalchemy import select, func
        
        # 检查总数
        total_result = await session.execute(select(func.count(AlarmTable.id)))
        total = total_result.scalar()
        
        # 检查24小时内数据
        start_time = datetime.utcnow() - timedelta(hours=24)
        recent_result = await session.execute(
            select(func.count(AlarmTable.id))
            .where(AlarmTable.created_at >= start_time)
        )
        recent = recent_result.scalar()
        
        # 检查严重程度分布
        severity_result = await session.execute(
            select(
                AlarmTable.severity,
                func.count(AlarmTable.id).label('count')
            ).group_by(AlarmTable.severity)
        )
        severity_dist = {row.severity: row.count for row in severity_result.all()}
        
        # 检查状态分布
        status_result = await session.execute(
            select(
                AlarmTable.status,
                func.count(AlarmTable.id).label('count')
            ).group_by(AlarmTable.status)
        )
        status_dist = {row.status: row.count for row in status_result.all()}
        
        print(f"📊 总告警: {total}")
        print(f"⏰ 24小时内: {recent}")
        print(f"⚠️ 严重程度: {severity_dist}")
        print(f"📋 状态分布: {status_dist}")


if __name__ == "__main__":
    asyncio.run(generate_chart_data())
    asyncio.run(test_api())