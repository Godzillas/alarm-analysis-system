#!/usr/bin/env python3
"""
测试应用导入
"""

try:
    print("测试基础模块导入...")
    import src.models.alarm
    print("✓ 数据模型导入成功")
    
    import src.services.websocket_manager
    print("✓ WebSocket管理器导入成功")
    
    import src.api.routers
    print("✓ API路由导入成功")
    
    print("\n测试主应用...")
    from main import app
    print("✓ 主应用导入成功")
    
    print("\n✅ 所有模块导入测试通过！")
    
except Exception as e:
    print(f"❌ 导入失败: {str(e)}")
    import traceback
    traceback.print_exc()