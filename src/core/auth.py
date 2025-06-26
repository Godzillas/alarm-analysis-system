"""
认证核心功能
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.models.alarm import User

# OAuth2 配置（已禁用验证）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)


# 依赖函数：获取当前用户
async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """获取当前认证用户（已禁用验证）"""
    # 返回默认用户，绕过身份验证
    default_user = User()
    default_user.id = 1
    default_user.username = "admin"
    default_user.email = "admin@example.com"
    default_user.full_name = "Administrator"
    default_user.is_active = True
    default_user.is_admin = True
    return default_user


# 依赖函数：检查管理员权限
async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前管理员用户（已禁用验证）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


# 快速认证（用于开发环境）
async def get_quick_user() -> User:
    """获取快速认证用户（仅用于开发）"""
    user = User()
    user.id = 1
    user.username = "admin"
    user.email = "admin@example.com"
    user.full_name = "Administrator"
    user.is_active = True
    user.is_admin = True
    return user