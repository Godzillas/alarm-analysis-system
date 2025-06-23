#!/usr/bin/env python3
"""
测试数据生成器
"""

import asyncio
import random
import aiohttp
from datetime import datetime, timedelta

ALARM_SOURCES = ["nginx", "mysql", "redis", "elasticsearch", "kubernetes", "application"]
ALARM_TITLES = [
    "CPU使用率过高",
    "内存不足",
    "磁盘空间不足",
    "网络连接超时",
    "数据库连接失败",
    "服务响应缓慢",
    "404错误增多",
    "登录失败次数过多",
    "SSL证书即将过期",
    "备份任务失败"
]
SEVERITIES = ["critical", "high", "medium", "low", "info"]
HOSTS = ["web-01", "web-02", "db-01", "db-02", "cache-01", "lb-01"]
SERVICES = ["nginx", "mysql", "redis", "app", "api", "worker"]
ENVIRONMENTS = ["production", "staging", "development"]


async def generate_alarm():
    """生成随机告警"""
    return {
        "source": random.choice(ALARM_SOURCES),
        "title": random.choice(ALARM_TITLES),
        "description": f"自动生成的测试告警 - {datetime.now()}",
        "severity": random.choice(SEVERITIES),
        "category": "system",
        "tags": {
            "auto_generated": True,
            "test_data": True
        },
        "metadata": {
            "cpu_usage": random.randint(10, 100),
            "memory_usage": random.randint(20, 95)
        },
        "host": random.choice(HOSTS),
        "service": random.choice(SERVICES),
        "environment": random.choice(ENVIRONMENTS)
    }


async def send_alarm(session, alarm_data):
    """发送告警到API"""
    try:
        async with session.post("http://localhost:8000/api/alarms/", json=alarm_data) as response:
            if response.status == 200:
                print(f"✓ 发送告警成功: {alarm_data['title']}")
                return True
            else:
                print(f"✗ 发送告警失败: {response.status}")
                return False
    except Exception as e:
        print(f"✗ 发送告警异常: {e}")
        return False


async def generate_test_data(count=50):
    """生成测试数据"""
    print(f"开始生成 {count} 个测试告警...")
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(count):
            alarm_data = await generate_alarm()
            tasks.append(send_alarm(session, alarm_data))
            
            if len(tasks) >= 10:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                success_count = sum(1 for r in results if r is True)
                print(f"批次完成: {success_count}/{len(tasks)} 成功")
                tasks = []
                await asyncio.sleep(1)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            print(f"最后批次: {success_count}/{len(tasks)} 成功")
    
    print("测试数据生成完成!")


async def generate_continuous_data(interval=5):
    """持续生成告警数据"""
    print(f"开始持续生成告警数据，间隔 {interval} 秒...")
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                alarm_data = await generate_alarm()
                await send_alarm(session, alarm_data)
                await asyncio.sleep(interval)
            except KeyboardInterrupt:
                print("停止生成数据")
                break
            except Exception as e:
                print(f"生成数据异常: {e}")
                await asyncio.sleep(1)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "continuous":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            asyncio.run(generate_continuous_data(interval))
        else:
            count = int(sys.argv[1])
            asyncio.run(generate_test_data(count))
    else:
        asyncio.run(generate_test_data())