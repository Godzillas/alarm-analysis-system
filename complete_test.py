#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的测试验证脚本
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from src.core.database import async_session_maker
from src.models.alarm import Endpoint
from sqlalchemy import select


async def get_endpoints():
    """获取所有接入点信息"""
    async with async_session_maker() as session:
        result = await session.execute(select(Endpoint))
        return result.scalars().all()


def test_api_endpoints():
    """测试API端点（使用curl）"""
    print("🔍 生成API测试命令...")
    
    base_url = "http://localhost:8000"
    
    test_commands = [
        "echo '🔍 测试API端点...'",
        f"curl -s {base_url}/api/alarms/stats/summary | jq '.'",
        f"curl -s {base_url}/api/analytics/summary?time_range=24h | jq '.by_severity'",
        f"curl -s {base_url}/api/endpoints/ | jq 'length'",
        f"curl -s {base_url}/api/users/ | jq 'length'"
    ]
    
    print("✅ API测试命令已准备")
    return test_commands


def generate_curl_commands(endpoints):
    """生成curl测试命令"""
    print(f"\n📝 生成curl测试命令...")
    
    base_url = "http://localhost:8000"
    commands = []
    
    # 添加标题
    commands.append("#!/bin/bash")
    commands.append("# 告警系统接入点测试脚本")
    commands.append("echo '🚀 开始测试告警系统接入点...'")
    commands.append("echo ''")
    commands.append("")
    
    for endpoint in endpoints:
        api_token = endpoint.api_token
        webhook_url = f"{base_url}{endpoint.webhook_url}"
        
        # 根据接入点类型生成测试数据
        if "prometheus" in endpoint.name.lower():
            test_data = {
                "alertname": "HighCPUUsage",
                "summary": "CPU使用率过高警告",
                "severity": "critical",
                "instance": "web-server-01:9090",
                "job": "webapp",
                "labels": {
                    "env": "production",
                    "team": "devops",
                    "alertname": "HighCPUUsage"
                },
                "annotations": {
                    "description": "CPU使用率已达到95%，超过阈值90%",
                    "runbook_url": "https://wiki.company.com/runbooks/cpu"
                },
                "startsAt": "2025-06-23T11:00:00Z"
            }
        elif "grafana" in endpoint.name.lower():
            test_data = {
                "title": "磁盘空间不足警告",
                "message": "服务器磁盘使用率超过85%，需要立即处理",
                "state": "alerting",
                "tags": {
                    "instance": "db-server-02",
                    "service": "database",
                    "env": "production"
                },
                "evalMatches": [
                    {
                        "value": 88.5,
                        "metric": "disk_usage_percent",
                        "tags": {"device": "/dev/sda1"}
                    }
                ]
            }
        elif "zabbix" in endpoint.name.lower():
            test_data = {
                "trigger_name": "内存使用率过高",
                "trigger_description": "系统内存使用率超过80%，当前值：85.2%",
                "trigger_severity": "4",  # Zabbix严重级别
                "host_name": "cache-server-01",
                "item_name": "memory.util",
                "item_value": "85.2",
                "trigger_status": "PROBLEM",
                "event_time": "2025-06-23 11:30:00"
            }
        elif "elk" in endpoint.name.lower():
            test_data = {
                "alert_name": "应用错误日志激增",
                "alert_description": "过去5分钟内应用错误日志数量超过100条",
                "level": "high",
                "hostname": "api-server-01",
                "service_name": "user-service",
                "log_count": 157,
                "time_window": "5m",
                "query": "level:ERROR AND service:user-service"
            }
        else:  # custom-api
            test_data = {
                "name": "网络连接超时",
                "desc": "与外部支付API连接超时次数过多",
                "level": "medium",
                "server": "gateway-01", 
                "app": "payment-gateway",
                "timeout_count": 25,
                "threshold": 20
            }
        
        # 单个告警测试
        commands.append(f"# 测试 {endpoint.name} 接入点")
        commands.append(f"echo '🧪 测试 {endpoint.name} 单个告警接收...'")
        curl_cmd = f"""curl -X POST "{webhook_url}" \\
  -H "Content-Type: application/json" \\
  -H "User-Agent: {endpoint.name}-monitor/1.0" \\
  -d '{json.dumps(test_data, ensure_ascii=False, indent=2)}'"""
        commands.append(curl_cmd)
        commands.append("echo ''")
        commands.append("")
        
        # 批量告警测试
        batch_data = [test_data]
        if "prometheus" in endpoint.name.lower():
            batch_data.append({
                "alertname": "HighMemoryUsage",
                "summary": "内存使用率过高",
                "severity": "warning", 
                "instance": "web-server-02:9090",
                "job": "webapp"
            })
        
        batch_url = f"{base_url}/api/webhook/batch/{api_token}"
        commands.append(f"echo '📦 测试 {endpoint.name} 批量告警接收...'")
        batch_curl = f"""curl -X POST "{batch_url}" \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(batch_data, ensure_ascii=False, indent=2)}'"""
        commands.append(batch_curl)
        commands.append("echo ''")
        commands.append("")
        
        # 测试接入点验证
        test_url = f"{base_url}/api/webhook/test/{api_token}"
        commands.append(f"echo '🔍 验证 {endpoint.name} 接入点状态...'")
        commands.append(f"curl -X GET \"{test_url}\"")
        commands.append("echo ''")
        commands.append("")
    
    # 添加结尾
    commands.append("echo '✅ 接入点测试完成！'")
    commands.append("echo ''")
    commands.append("echo '📊 查看数据:'")
    commands.append("echo '  - 管理后台: http://localhost:8000/admin'")
    commands.append("echo '  - API文档: http://localhost:8000/docs'")
    commands.append("echo '  - 告警统计: http://localhost:8000/api/alarms/stats/summary'")
    
    # 写入脚本文件
    script_content = "\n".join(commands)
    with open("test_webhook_endpoints.sh", "w", encoding="utf-8") as f:
        f.write(script_content)
    
    # 使脚本可执行
    import os
    os.chmod("test_webhook_endpoints.sh", 0o755)
    
    print(f"📄 已生成测试脚本: test_webhook_endpoints.sh")
    print(f"🚀 运行测试: ./test_webhook_endpoints.sh")


async def main():
    """主函数"""
    print("🔧 完整系统测试")
    print("=" * 50)
    
    # 生成API测试命令
    api_commands = test_api_endpoints()
    
    # 获取接入点
    print(f"\n📡 获取接入点信息...")
    endpoints = await get_endpoints()
    
    if endpoints:
        print(f"✅ 找到 {len(endpoints)} 个接入点:")
        for ep in endpoints:
            print(f"   🔌 {ep.name} ({ep.endpoint_type}) - Token: {ep.api_token[:20]}...")
        
        # 生成curl测试命令
        generate_curl_commands(endpoints)
        
    else:
        print("❌ 没有找到接入点，请先运行 create_endpoints_and_test.py")
    
    print(f"\n🎉 测试准备完成！")
    print(f"💡 现在可以:")
    print(f"   1. 访问管理后台: http://localhost:8000/admin")
    print(f"   2. 运行接入点测试: ./test_webhook_endpoints.sh")
    print(f"   3. 查看API文档: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())