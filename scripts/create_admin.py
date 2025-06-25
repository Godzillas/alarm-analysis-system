#!/usr/bin/env python3
"""
创建管理员用户脚本
"""

import asyncio
import sys
from passlib.context import CryptContext
from sqlalchemy import text
from src.core.database import async_session_maker, init_db


async def create_admin_user():
    """创建管理员用户"""
    
    # 密码哈希
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    password_hash = pwd_context.hash("admin123456")
    
    async with async_session_maker() as session:
        try:
            # 检查用户是否已存在
            result = await session.execute(
                text("SELECT id FROM users WHERE username = 'admin'")
            )
            if result.fetchone():
                print("管理员用户已存在")
                return
            
            # 创建管理员用户
            await session.execute(
                text("""
                INSERT INTO users (username, email, password_hash, full_name, is_active, is_admin, created_at) 
                VALUES ('admin', 'admin@example.com', :password_hash, '系统管理员', true, true, NOW())
                """),
                {"password_hash": password_hash}
            )
            
            # 获取用户ID
            result = await session.execute(
                text("SELECT id FROM users WHERE username = 'admin'")
            )
            user_id = result.fetchone()[0]
            
            # 创建默认系统
            await session.execute(
                text("""
                INSERT IGNORE INTO systems (name, description, code, owner, enabled, created_at)
                VALUES ('演示系统', '告警系统演示', 'DEMO', 'admin', true, NOW())
                """)
            )
            
            # 获取系统ID
            result = await session.execute(
                text("SELECT id FROM systems WHERE code = 'DEMO'")
            )
            system_id = result.fetchone()[0]
            
            # 用户系统关联
            await session.execute(
                text("""
                INSERT IGNORE INTO user_systems (user_id, system_id, created_at)
                VALUES (:user_id, :system_id, NOW())
                """),
                {"user_id": user_id, "system_id": system_id}
            )
            
            await session.commit()
            print(f"✅ 管理员用户创建成功")
            print(f"   用户名: admin")
            print(f"   密码: admin123456")
            print(f"   邮箱: admin@example.com")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ 创建管理员用户失败: {str(e)}")
            sys.exit(1)


async def main():
    """主函数"""
    print("正在初始化数据库...")
    await init_db()
    
    print("正在创建管理员用户...")
    await create_admin_user()
    
    print("初始化完成！")


if __name__ == "__main__":
    asyncio.run(main())