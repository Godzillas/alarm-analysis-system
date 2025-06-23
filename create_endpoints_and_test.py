#!/usr/bin/env python3
"""
创建接入点并生成测试数据
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from src.core.database import init_db
from src.services.endpoint_manager import EndpointManager
from src.services.user_manager import UserManager


async def create_test_endpoints():
    """创建测试接入点"""
    print("🔧 创建测试接入点...")
    
    # 初始化数据库
    await init_db()
    
    endpoint_manager = EndpointManager()
    user_manager = UserManager()
    
    # 创建测试用户
    user_data = {
        "username": "admin",
        "email": "admin@example.com",
        "password": "admin123",
        "full_name": "系统管理员",
        "is_admin": True
    }
    
    user = await user_manager.create_user(user_data)
    if user:
        print(f"✅ 创建用户: {user.username}")
    
    # 创建不同类型的接入点
    endpoints_config = [
        {
            "name": "prometheus-alerts",
            "description": "Prometheus告警接入点",
            "endpoint_type": "webhook",
            "config": {
                "field_mapping": {
                    "title": "alertname",
                    "description": "summary",
                    "severity": "severity",
                    "host": "instance",
                    "service": "job"
                },
                "default_severity": "medium"
            }
        },
        {
            "name": "grafana-alerts", 
            "description": "Grafana告警接入点",
            "endpoint_type": "webhook",
            "config": {
                "field_mapping": {
                    "title": "title",
                    "description": "message", 
                    "severity": "state",
                    "host": "tags.instance",
                    "service": "tags.service"
                },
                "severity_mapping": {
                    "alerting": "high",
                    "critical": "critical",
                    "warning": "medium"
                }
            }
        },
        {
            "name": "zabbix-alerts",
            "description": "Zabbix告警接入点", 
            "endpoint_type": "webhook",
            "config": {
                "field_mapping": {
                    "title": "trigger_name",
                    "description": "trigger_description",
                    "severity": "trigger_severity",
                    "host": "host_name",
                    "service": "item_name"
                },
                "severity_mapping": {
                    "0": "info",
                    "1": "info", 
                    "2": "low",
                    "3": "medium",
                    "4": "high",
                    "5": "critical"
                }
            }
        },
        {
            "name": "elk-alerts",
            "description": "ELK Stack告警接入点",
            "endpoint_type": "webhook", 
            "config": {
                "field_mapping": {
                    "title": "alert_name",
                    "description": "alert_description",
                    "severity": "level",
                    "host": "hostname",
                    "service": "service_name"
                }
            }
        },
        {
            "name": "custom-api",
            "description": "自定义API接入点",
            "endpoint_type": "api",
            "config": {
                "field_mapping": {
                    "title": "name",
                    "description": "desc", 
                    "severity": "level",
                    "host": "server",
                    "service": "app"
                }
            }
        }
    ]
    
    created_endpoints = []
    
    for endpoint_config in endpoints_config:
        endpoint = await endpoint_manager.create_endpoint(endpoint_config)
        if endpoint:
            created_endpoints.append(endpoint)
            print(f"✅ 创建接入点: {endpoint.name}")
            print(f"   🔗 API令牌: {endpoint.api_token}")
            print(f"   📍 接入URL: http://localhost:8000{endpoint.webhook_url}")
        else:
            print(f"❌ 创建接入点失败: {endpoint_config['name']}")
    
    return created_endpoints


def generate_curl_tests(endpoints):
    """生成curl测试命令"""
    print("\n📝 生成curl测试命令...")
    
    base_url = "http://localhost:8000"
    
    curl_commands = []
    
    for endpoint in endpoints:
        api_token = endpoint.api_token
        webhook_url = f"{base_url}{endpoint.webhook_url}"
        
        # 根据不同接入点类型生成不同的测试数据
        if endpoint.name == "prometheus-alerts":
            test_data = {
                "alertname": "HighCPUUsage",
                "summary": "CPU使用率超过90%",
                "severity": "high",
                "instance": "web-server-01",
                "job": "webapp",
                "labels": {
                    "env": "production",
                    "team": "devops"
                }
            }
        elif endpoint.name == "grafana-alerts":
            test_data = {
                "title": "磁盘空间不足",
                "message": "服务器磁盘使用率超过85%",
                "state": "alerting", 
                "tags": {
                    "instance": "db-server-02",
                    "service": "database"
                }
            }
        elif endpoint.name == "zabbix-alerts":
            test_data = {
                "trigger_name": "内存使用率过高",
                "trigger_description": "内存使用率超过80%",
                "trigger_severity": "4",
                "host_name": "cache-server-01",
                "item_name": "redis"
            }
        elif endpoint.name == "elk-alerts":
            test_data = {
                "alert_name": "错误日志过多",
                "alert_description": "过去5分钟内错误日志超过100条",
                "level": "medium",
                "hostname": "api-server-03",
                "service_name": "user-service"
            }
        else:  # custom-api
            test_data = {
                "name": "网络连接超时",
                "desc": "外部API连接超时次数过多",
                "level": "high",
                "server": "gateway-01",
                "app": "api-gateway"
            }
        
        # 生成单个告警测试
        curl_cmd = f'''curl -X POST "{webhook_url}" \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(test_data, ensure_ascii=False)}'
'''
        
        curl_commands.append(f"# 测试 {endpoint.name} 接入点")
        curl_commands.append(f"echo '🧪 测试 {endpoint.name} 单个告警接收...'")
        curl_commands.append(curl_cmd)
        
        # 生成批量告警测试
        batch_data = [test_data]
        if endpoint.name == "prometheus-alerts":
            batch_data.append({
                "alertname": "HighMemoryUsage", 
                "summary": "内存使用率超过85%",
                "severity": "medium",
                "instance": "web-server-02", 
                "job": "webapp"
            })
        
        batch_url = f"{base_url}/api/webhook/batch/{api_token}"
        batch_curl = f'''curl -X POST "{batch_url}" \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(batch_data, ensure_ascii=False)}'
'''
        
        curl_commands.append(f"echo '🧪 测试 {endpoint.name} 批量告警接收...'")
        curl_commands.append(batch_curl)
        
        # 生成测试接入点验证
        test_url = f"{base_url}/api/webhook/test/{api_token}"
        test_curl = f'''curl -X GET "{test_url}"'''
        
        curl_commands.append(f"echo '🔍 验证 {endpoint.name} 接入点...'")
        curl_commands.append(test_curl)
        curl_commands.append("")
    
    # 写入测试脚本文件
    test_script = "#!/bin/bash\n\n"
    test_script += "echo '🚀 开始测试接入点功能...'\n"
    test_script += "echo ''\n\n"
    test_script += "\n".join(curl_commands)
    test_script += "\necho ''\necho '✅ 测试完成！访问 http://localhost:8000/admin 查看告警数据'"
    
    with open("test_endpoints.sh", "w", encoding="utf-8") as f:
        f.write(test_script)
    
    # 使脚本可执行
    import os
    os.chmod("test_endpoints.sh", 0o755)
    
    print("📄 已生成测试脚本: test_endpoints.sh")
    print(f"🔗 管理后台地址: http://localhost:8000/admin")
    print(f"📚 API文档地址: http://localhost:8000/docs")


async def main():
    """主函数"""
    try:
        print("🚀 开始创建接入点和测试数据...")
        
        endpoints = await create_test_endpoints()
        
        if endpoints:
            print(f"\n✅ 成功创建 {len(endpoints)} 个接入点")
            generate_curl_tests(endpoints)
            print("\n🎉 完成！现在可以运行测试了：")
            print("   ./test_endpoints.sh")
        else:
            print("❌ 没有创建任何接入点")
            
    except Exception as e:
        print(f"❌ 创建失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())