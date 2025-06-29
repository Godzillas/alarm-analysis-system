#!/usr/bin/env python3
"""
修复现有Grafana接入点的webhook URL
"""

import asyncio
import sys
from sqlalchemy import select, update
from src.core.database import async_session_maker
from src.models.alarm import Endpoint

async def fix_grafana_endpoints():
    """修复Grafana接入点的webhook URL"""
    try:
        async with async_session_maker() as session:
            # 查找所有Grafana接入点
            result = await session.execute(
                select(Endpoint).where(Endpoint.endpoint_type == "grafana")
            )
            grafana_endpoints = result.scalars().all()
            
            if not grafana_endpoints:
                print("未找到Grafana接入点")
                return
            
            print(f"找到 {len(grafana_endpoints)} 个Grafana接入点，开始修复...")
            
            fixed_count = 0
            for endpoint in grafana_endpoints:
                if endpoint.api_token:
                    # 生成正确的Grafana webhook URL
                    new_webhook_url = f"/api/grafana/webhook/{endpoint.api_token}"
                    
                    if endpoint.webhook_url != new_webhook_url:
                        print(f"修复接入点 '{endpoint.name}':")
                        print(f"  旧URL: {endpoint.webhook_url}")
                        print(f"  新URL: {new_webhook_url}")
                        
                        # 更新webhook URL
                        await session.execute(
                            update(Endpoint)
                            .where(Endpoint.id == endpoint.id)
                            .values(webhook_url=new_webhook_url)
                        )
                        fixed_count += 1
                    else:
                        print(f"接入点 '{endpoint.name}' 的URL已正确，跳过")
                else:
                    print(f"警告: 接入点 '{endpoint.name}' 没有API令牌")
            
            if fixed_count > 0:
                await session.commit()
                print(f"\n✅ 成功修复了 {fixed_count} 个Grafana接入点的webhook URL")
            else:
                print("\nℹ️  所有Grafana接入点的URL都已正确")
                
    except Exception as e:
        print(f"❌ 修复过程中出现错误: {str(e)}")
        return False
    
    return True

async def main():
    """主函数"""
    print("=== Grafana接入点webhook URL修复工具 ===\n")
    
    success = await fix_grafana_endpoints()
    
    if success:
        print("\n🎉 修复完成！现在可以重新测试Grafana告警配置。")
        print("\n💡 提示:")
        print("1. 重启告警分析系统以应用更改")
        print("2. 在Grafana中使用新的webhook URL进行测试")
        print("3. 新的URL格式为: /api/grafana/webhook/{token}")
    else:
        print("\n❌ 修复失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())