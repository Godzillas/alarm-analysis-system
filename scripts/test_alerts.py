#!/usr/bin/env python3
"""
告警系统测试脚本
用于生成测试告警数据，验证系统功能
"""

import asyncio
import aiohttp
import json
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any


class AlertTestGenerator:
    """告警测试数据生成器"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_token: str = "demo-token"):
        self.base_url = base_url
        self.api_token = api_token
        self.webhook_url = f"{base_url}/api/webhook/alarm/{api_token}"
        
        # 测试数据模板
        self.services = ["web-server", "database", "cache", "api-gateway", "message-queue"]
        self.hosts = ["web-01", "web-02", "db-01", "db-02", "cache-01"]
        self.environments = ["production", "staging", "development"]
        self.severities = ["critical", "high", "medium", "low", "info"]
        self.sources = ["prometheus", "grafana", "zabbix", "custom-monitor"]
        
        # 告警模板
        self.alert_templates = [
            {
                "title": "服务响应超时",
                "description": "服务 {service} 在主机 {host} 上响应超时，当前响应时间: {value}ms",
                "category": "performance"
            },
            {
                "title": "内存使用率过高", 
                "description": "主机 {host} 内存使用率达到 {value}%，超过阈值",
                "category": "resource"
            },
            {
                "title": "磁盘空间不足",
                "description": "主机 {host} 磁盘使用率达到 {value}%，剩余空间不足",
                "category": "resource"
            },
            {
                "title": "服务连接失败",
                "description": "无法连接到服务 {service}，连接被拒绝",
                "category": "connectivity"
            },
            {
                "title": "数据库查询缓慢",
                "description": "数据库查询执行时间过长，平均查询时间: {value}s",
                "category": "database"
            }
        ]
    
    def generate_alert(self) -> Dict[str, Any]:
        """生成随机告警数据"""
        template = random.choice(self.alert_templates)
        service = random.choice(self.services)
        host = random.choice(self.hosts)
        environment = random.choice(self.environments)
        severity = random.choice(self.severities)
        source = random.choice(self.sources)
        
        # 生成随机数值
        if "timeout" in template["title"] or "query" in template["title"]:
            value = random.randint(1000, 10000)  # 毫秒或秒
        else:
            value = random.randint(80, 95)  # 百分比
        
        alert = {
            "title": template["title"],
            "description": template["description"].format(
                service=service, 
                host=host, 
                value=value
            ),
            "severity": severity,
            "source": source,
            "host": host,
            "service": service,
            "environment": environment,
            "category": template["category"],
            "tags": {
                "component": service,
                "environment": environment,
                "test": "true",
                "generated": "true"
            },
            "metadata": {
                "value": value,
                "threshold": random.randint(70, 90),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        return alert
    
    async def send_alert(self, session: aiohttp.ClientSession, alert: Dict[str, Any]) -> bool:
        """发送告警"""
        try:
            async with session.post(self.webhook_url, json=alert) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ 告警发送成功: {alert['title']} ({alert['severity']})")
                    return True
                else:
                    print(f"❌ 告警发送失败: {response.status} - {await response.text()}")
                    return False
        except Exception as e:
            print(f"❌ 发送异常: {str(e)}")
            return False
    
    async def send_batch_alerts(self, count: int = 10, interval: float = 1.0):
        """批量发送告警"""
        print(f"🚀 开始发送 {count} 个测试告警...")
        
        async with aiohttp.ClientSession() as session:
            success_count = 0
            for i in range(count):
                alert = self.generate_alert()
                success = await self.send_alert(session, alert)
                if success:
                    success_count += 1
                
                if i < count - 1:  # 最后一个不等待
                    await asyncio.sleep(interval)
            
            print(f"\n📊 发送完成: {success_count}/{count} 成功")
    
    async def send_prometheus_alert(self):
        """发送Prometheus格式的告警"""
        prometheus_alert = {
            "receiver": "webhook",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "HighMemoryUsage",
                        "instance": "web-01:9090",
                        "job": "node-exporter",
                        "severity": "critical"
                    },
                    "annotations": {
                        "description": "Memory usage is above 90%",
                        "summary": "High memory usage detected"
                    },
                    "startsAt": datetime.utcnow().isoformat(),
                    "endsAt": "",
                    "generatorURL": "http://prometheus:9090/graph",
                    "fingerprint": "1234567890abcdef"
                }
            ],
            "groupLabels": {"alertname": "HighMemoryUsage"},
            "commonLabels": {"severity": "critical"},
            "commonAnnotations": {},
            "externalURL": "http://alertmanager:9093",
            "version": "4",
            "groupKey": "{}:{alertname=\"HighMemoryUsage\"}"
        }
        
        prometheus_url = f"{self.base_url}/api/webhook/prometheus"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(prometheus_url, json=prometheus_alert) as response:
                    if response.status == 200:
                        print("✅ Prometheus告警发送成功")
                        return True
                    else:
                        print(f"❌ Prometheus告警发送失败: {response.status}")
                        return False
            except Exception as e:
                print(f"❌ Prometheus告警发送异常: {str(e)}")
                return False
    
    async def test_api_endpoints(self):
        """测试API端点"""
        print("🔍 测试API端点...")
        
        endpoints = [
            "/docs",
            "/api/alarms/stats/summary",
            "/api/systems/",
            "/api/endpoints/",
            "/api/contact-points/"
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                url = f"{self.base_url}{endpoint}"
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            print(f"✅ {endpoint} - OK")
                        else:
                            print(f"❌ {endpoint} - {response.status}")
                except Exception as e:
                    print(f"❌ {endpoint} - 异常: {str(e)}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="告警系统测试工具")
    parser.add_argument("--url", default="http://localhost:8000", help="系统URL")
    parser.add_argument("--token", default="demo-token", help="API Token")
    parser.add_argument("--count", type=int, default=10, help="发送告警数量")
    parser.add_argument("--interval", type=float, default=1.0, help="发送间隔(秒)")
    parser.add_argument("--prometheus", action="store_true", help="发送Prometheus格式告警")
    parser.add_argument("--test-api", action="store_true", help="测试API端点")
    
    args = parser.parse_args()
    
    generator = AlertTestGenerator(args.url, args.token)
    
    print("🎯 智能告警分析系统测试工具")
    print("=" * 50)
    
    if args.test_api:
        await generator.test_api_endpoints()
        print()
    
    if args.prometheus:
        await generator.send_prometheus_alert()
        print()
    
    # 发送测试告警
    await generator.send_batch_alerts(args.count, args.interval)


if __name__ == "__main__":
    asyncio.run(main())