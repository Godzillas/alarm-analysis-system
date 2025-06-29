#!/usr/bin/env python3
"""
创建默认管理员用户
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import async_session_maker
from src.models.alarm import User
from src.services.auth import auth_service


async def create_admin_user():
    """创建默认管理员用户"""
    async with async_session_maker() as session:
        try:
            # 检查是否已存在admin用户
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.username == "admin")
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print("管理员用户已存在")
                print(f"用户名: {existing_user.username}")
                print(f"邮箱: {existing_user.email}")
                print(f"状态: {'活跃' if existing_user.is_active else '非活跃'}")
                return existing_user
            
            # 创建新的管理员用户
            admin_user = User()
            admin_user.username = "admin"
            admin_user.email = "admin@example.com"
            admin_user.full_name = "系统管理员"
            admin_user.password_hash = auth_service.get_password_hash("admin123")
            admin_user.is_active = True
            admin_user.is_admin = True
            
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            
            print("✅ 默认管理员用户创建成功！")
            print(f"用户名: {admin_user.username}")
            print(f"密码: admin123")
            print(f"邮箱: {admin_user.email}")
            print(f"ID: {admin_user.id}")
            
            return admin_user
            
        except Exception as e:
            await session.rollback()
            print(f"❌ 创建管理员用户失败: {str(e)}")
            raise


async def main():
    """主函数"""
    print("正在创建默认管理员用户...")
    try:
        await create_admin_user()
    except Exception as e:
        print(f"操作失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())