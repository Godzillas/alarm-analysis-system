#!/usr/bin/env python3
"""
RBAC系统初始化脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from src.services.rbac_service import RBACService
from src.core.logging import get_logger

logger = get_logger(__name__)


async def initialize_rbac():
    """初始化RBAC系统"""
    print("开始初始化RBAC权限系统...")
    
    service = RBACService()
    
    try:
        # 1. 创建默认权限
        print("1. 创建默认权限...")
        await service.create_default_permissions()
        print("   ✅ 默认权限创建完成")
        
        # 2. 创建默认角色
        print("2. 创建默认角色...")
        await service.create_default_roles()
        print("   ✅ 默认角色创建完成")
        
        # 3. 获取权限和角色统计
        permissions = await service.get_permissions(active_only=False, limit=1000)
        roles = await service.get_roles(active_only=False, limit=100)
        
        print(f"\n📊 RBAC系统统计:")
        print(f"   权限数量: {len(permissions)}")
        print(f"   角色数量: {len(roles)}")
        
        print(f"\n📋 创建的默认权限:")
        for perm in permissions:
            print(f"   - {perm.code}: {perm.name} ({perm.module}.{perm.action})")
        
        print(f"\n👥 创建的默认角色:")
        for role in roles:
            perm_count = len(role.permissions) if role.permissions else 0
            print(f"   - {role.name}: {role.display_name} (权限数: {perm_count})")
        
        print(f"\n✅ RBAC系统初始化完成")
        
        print(f"\n🚀 下一步操作建议:")
        print(f"   1. 为管理员用户分配 'super_admin' 角色")
        print(f"   2. 根据需要为其他用户分配相应角色")
        print(f"   3. 在API中使用 @require_permission 装饰器进行权限控制")
        
    except Exception as e:
        print(f"❌ RBAC系统初始化失败: {str(e)}")
        logger.error(f"RBAC initialization failed: {str(e)}")
        raise


async def assign_admin_role():
    """为管理员用户分配超级管理员角色"""
    from src.core.database import async_session_maker
    from src.models.alarm import User
    from src.models.rbac import RBACRole
    from sqlalchemy import select
    
    print("\n🔧 配置管理员权限...")
    
    async with async_session_maker() as session:
        try:
            # 查找管理员用户
            admin_users = await session.execute(
                select(User).where(User.is_admin == True)
            )
            admin_user_list = admin_users.scalars().all()
            
            if not admin_user_list:
                print("   ⚠️  未找到管理员用户，请先创建管理员用户")
                return
            
            # 查找超级管理员角色
            super_admin_role = await session.execute(
                select(RBACRole).where(RBACRole.name == "super_admin")
            )
            super_admin = super_admin_role.scalar_one_or_none()
            
            if not super_admin:
                print("   ❌ 未找到超级管理员角色")
                return
            
            service = RBACService()
            
            # 为所有管理员用户分配超级管理员角色
            for admin_user in admin_user_list:
                try:
                    await service.assign_roles_to_user(
                        user_id=admin_user.id,
                        role_ids=[super_admin.id],
                        assigned_by=1  # 系统分配
                    )
                    print(f"   ✅ 已为用户 {admin_user.username} 分配超级管理员角色")
                except Exception as e:
                    print(f"   ❌ 为用户 {admin_user.username} 分配角色失败: {str(e)}")
            
        except Exception as e:
            print(f"   ❌ 配置管理员权限失败: {str(e)}")


async def show_rbac_status():
    """显示RBAC系统状态"""
    from src.core.database import async_session_maker
    from src.models.rbac import RBACRole, RBACPermission
    from src.models.alarm import User
    from sqlalchemy import select, func
    
    print("\n📊 RBAC系统状态:")
    
    async with async_session_maker() as session:
        try:
            # 权限统计
            perm_count = await session.execute(
                select(func.count(RBACPermission.id))
            )
            perm_total = perm_count.scalar()
            
            # 角色统计
            role_count = await session.execute(
                select(func.count(RBACRole.id))
            )
            role_total = role_count.scalar()
            
            # 用户统计
            user_count = await session.execute(
                select(func.count(User.id))
            )
            user_total = user_count.scalar()
            
            print(f"   权限总数: {perm_total}")
            print(f"   角色总数: {role_total}")
            print(f"   用户总数: {user_total}")
            
            # 显示权限模块分布
            modules = await session.execute(
                select(RBACPermission.module, func.count(RBACPermission.id))
                .group_by(RBACPermission.module)
                .order_by(RBACPermission.module)
            )
            
            print(f"\n   权限模块分布:")
            for module, count in modules.fetchall():
                print(f"     - {module}: {count} 个权限")
            
        except Exception as e:
            print(f"   ❌ 获取状态失败: {str(e)}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="RBAC权限系统管理工具")
    parser.add_argument("--init", action="store_true", help="初始化RBAC系统")
    parser.add_argument("--assign-admin", action="store_true", help="为管理员分配角色")
    parser.add_argument("--status", action="store_true", help="显示系统状态")
    parser.add_argument("--all", action="store_true", help="执行所有操作")
    
    args = parser.parse_args()
    
    if not any([args.init, args.assign_admin, args.status, args.all]):
        parser.print_help()
        return
    
    async def run_tasks():
        if args.all or args.init:
            await initialize_rbac()
        
        if args.all or args.assign_admin:
            await assign_admin_role()
        
        if args.all or args.status:
            await show_rbac_status()
    
    try:
        asyncio.run(run_tasks())
        print(f"\n🎉 操作完成")
    except Exception as e:
        print(f"\n❌ 操作失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()