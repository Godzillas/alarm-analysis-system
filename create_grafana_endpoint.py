#!/usr/bin/env python3
"""
创建Grafana接入点的脚本
"""

import asyncio
import json
from sqlalchemy import select
from src.core.database import async_session_maker
from src.models.alarm import Endpoint
from src.services.endpoint_manager import EndpointManager

async def create_grafana_endpoint():
    """创建Grafana接入点"""
    try:
        endpoint_manager = EndpointManager()
        
        # Grafana接入点配置
        grafana_endpoint_data = {
            "name": "grafana-alerts",
            "description": "Grafana告警接入点",
            "endpoint_type": "grafana",
            "config": {
                "field_mapping": {
                    "title": "alerts[0].annotations.summary",
                    "description": "alerts[0].annotations.description", 
                    "severity": "alerts[0].labels.severity",
                    "host": "alerts[0].labels.instance",
                    "service": "alerts[0].labels.service"
                },
                "default_severity": "medium",
                "severity_mapping": {
                    "info": "low",
                    "warning": "medium", 
                    "critical": "critical"
                }
            },
            "system_id": None,
            "enabled": True,
            "rate_limit": 1000,
            "timeout": 30
        }
        
        # 创建接入点
        endpoint = await endpoint_manager.create_endpoint(grafana_endpoint_data)
        
        if endpoint:
            print(f"✅ 成功创建Grafana接入点:")
            print(f"   ID: {endpoint.id}")
            print(f"   名称: {endpoint.name}")
            print(f"   类型: {endpoint.endpoint_type}")
            print(f"   Token: {endpoint.api_token}")
            print(f"   Webhook URL: {endpoint.webhook_url}")
            print(f"   完整URL: http://localhost:8000{endpoint.webhook_url}")
            
            # 显示Grafana配置说明
            print(f"\n📋 Grafana配置说明:")
            print(f"   1. 在Grafana中进入 Alerting > Contact points")
            print(f"   2. 创建新的Contact point")
            print(f"   3. 选择类型: Webhook")
            print(f"   4. URL: http://localhost:8000{endpoint.webhook_url}")
            print(f"   5. HTTP Method: POST")
            print(f"   6. 不需要认证信息")
            
            return endpoint
        else:
            print("❌ 创建Grafana接入点失败")
            return None
            
    except Exception as e:
        print(f"❌ 创建过程中出现错误: {str(e)}")
        return None

async def list_existing_endpoints():
    """列出现有接入点"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(select(Endpoint))
            endpoints = result.scalars().all()
            
            if endpoints:
                print(f"现有接入点 ({len(endpoints)}个):")
                for endpoint in endpoints:
                    print(f"  - {endpoint.name} ({endpoint.endpoint_type}) - Token: {endpoint.api_token}")
                    if endpoint.endpoint_type == "grafana":
                        print(f"    URL: http://localhost:8000{endpoint.webhook_url}")
            else:
                print("未找到任何接入点")
                
    except Exception as e:
        print(f"查询接入点失败: {str(e)}")

async def main():
    """主函数"""
    print("=== Grafana接入点创建工具 ===\n")
    
    # 先列出现有接入点
    await list_existing_endpoints()
    print()
    
    # 检查是否已有Grafana接入点
    async with async_session_maker() as session:
        result = await session.execute(
            select(Endpoint).where(Endpoint.endpoint_type == "grafana")
        )
        grafana_endpoints = result.scalars().all()
        
        if grafana_endpoints:
            print("已找到Grafana接入点:")
            for endpoint in grafana_endpoints:
                print(f"  - {endpoint.name}: http://localhost:8000{endpoint.webhook_url}")
            
            answer = input("\n是否要创建新的Grafana接入点? (y/N): ")
            if answer.lower() not in ['y', 'yes']:
                print("取消创建")
                return
    
    # 创建新的Grafana接入点
    endpoint = await create_grafana_endpoint()
    
    if endpoint:
        print(f"\n🎉 创建完成！现在可以在Grafana中测试告警了。")
    else:
        print(f"\n❌ 创建失败")

if __name__ == "__main__":
    asyncio.run(main())