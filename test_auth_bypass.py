#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试授权绕过功能
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.auth import get_current_user, get_current_admin_user

async def test_auth_bypass():
    """测试授权绕过"""
    print("测试授权绕过功能...")
    
    try:
        # 测试获取当前用户（不提供token）
        user = await get_current_user(token=None, db=None)
        print(f"✅ get_current_user 成功: {user.username} (ID: {user.id})")
        
        # 测试获取管理员用户
        admin_user = await get_current_admin_user(current_user=user)
        print(f"✅ get_current_admin_user 成功: {admin_user.username} (Admin: {admin_user.is_admin})")
        
        print("\n🎉 授权绕过测试成功！所有API现在可以无需认证访问。")
        
    except Exception as e:
        print(f"❌ 授权绕过测试失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_auth_bypass())
    sys.exit(0 if result else 1)