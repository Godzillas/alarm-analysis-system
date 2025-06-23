#!/usr/bin/env python3
"""
测试API和数据
"""

import asyncio
import aiohttp
import json


async def test_api():
    """测试API端点"""
    base_url = "http://localhost:8000"
    
    endpoints = [
        "/api/alarms/stats/summary",
        "/api/alarms/?limit=5",
        "/api/endpoints/",
        "/api/users/",
        "/api/rules/stats",
        "/api/analytics/summary?time_range=24h"
    ]
    
    async with aiohttp.ClientSession() as session:
        print("🔍 测试API端点...")
        
        for endpoint in endpoints:
            try:
                async with session.get(f"{base_url}{endpoint}") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ {endpoint}: {response.status}")
                        
                        # 显示关键数据
                        if "stats/summary" in endpoint:
                            print(f"   📊 告警统计: 总数={data.get('total', 0)}, 活跃={data.get('active', 0)}")
                        elif endpoint.startswith("/api/alarms/"):
                            print(f"   📋 告警数据: {len(data)} 条记录")
                        elif endpoint.startswith("/api/endpoints/"):
                            print(f"   🔌 接入点: {len(data)} 个")
                        elif endpoint.startswith("/api/users/"):
                            print(f"   👥 用户: {len(data)} 个")
                        elif "rules/stats" in endpoint:
                            print(f"   📏 规则: {data.get('active_groups', 0)} 个组, {data.get('active_rules', 0)} 个规则")
                        elif "analytics" in endpoint:
                            print(f"   📈 分析数据: 时间范围={data.get('time_range', 'N/A')}")
                    else:
                        print(f"❌ {endpoint}: {response.status}")
                        
            except Exception as e:
                print(f"❌ {endpoint}: 错误 - {str(e)}")
        
        print(f"\n🌐 可以访问以下地址查看系统:")
        print(f"   - 主页: {base_url}")
        print(f"   - 现代管理后台: {base_url}/admin")
        print(f"   - API文档: {base_url}/docs")


if __name__ == "__main__":
    asyncio.run(test_api())