"""
用户管理服务
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_maker
from src.models.alarm import User, UserSubscription
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UserManager:
    def __init__(self):
        self.active_sessions: Dict[str, Dict] = {}
        
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[User]:
        """创建新用户"""
        try:
            async with async_session_maker() as session:
                # 检查用户名和邮箱是否已存在
                result = await session.execute(
                    select(User).where(
                        or_(
                            User.username == user_data["username"],
                            User.email == user_data["email"]
                        )
                    )
                )
                existing_user = result.scalars().first()
                
                if existing_user:
                    if existing_user.username == user_data["username"]:
                        raise ValueError("用户名已存在")
                    if existing_user.email == user_data["email"]:
                        raise ValueError("邮箱已存在")
                        
                # 密码哈希
                password_hash = self._hash_password(user_data.pop("password"))
                
                user = User(
                    password_hash=password_hash,
                    **user_data
                )
                
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
                logger.info(f"Created user: {user.username}")
                return user
                
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            return None
            
    async def get_user(self, user_id: int) -> Optional[User]:
        """获取用户"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                return result.scalars().first()
                
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {str(e)}")
            return None
            
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(User).where(User.username == username)
                )
                return result.scalars().first()
                
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {str(e)}")
            return None
            
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(User).where(User.email == email)
                )
                return result.scalars().first()
                
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {str(e)}")
            return None
            
    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Optional[User]:
        """更新用户"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalars().first()
                
                if not user:
                    return None
                    
                # 检查邮箱唯一性
                if "email" in update_data and update_data["email"] != user.email:
                    existing_result = await session.execute(
                        select(User).where(User.email == update_data["email"])
                    )
                    existing_user = existing_result.scalars().first()
                    if existing_user:
                        raise ValueError("邮箱已存在")
                        
                for key, value in update_data.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                        
                user.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(user)
                
                logger.info(f"Updated user: {user.username}")
                return user
                
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {str(e)}")
            return None
            
    async def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalars().first()
                
                if not user:
                    return False
                    
                # 删除用户的订阅
                await session.execute(
                    select(UserSubscription).where(UserSubscription.user_id == user_id)
                )
                subscriptions = result.scalars().all()
                for subscription in subscriptions:
                    await session.delete(subscription)
                    
                await session.delete(user)
                await session.commit()
                
                logger.info(f"Deleted user: {user.username}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {str(e)}")
            return False
            
    async def list_users(self, skip: int = 0, limit: int = 100, active_only: bool = False) -> List[User]:
        """获取用户列表"""
        try:
            async with async_session_maker() as session:
                query = select(User)
                
                if active_only:
                    query = query.where(User.is_active == True)
                    
                query = query.offset(skip).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"Failed to list users: {str(e)}")
            return []
            
    async def list_users_paginated(self, skip: int = 0, limit: int = 100, active_only: bool = False, filters: Dict[str, Any] = None) -> tuple[List[User], int]:
        """获取分页用户列表"""
        try:
            async with async_session_maker() as session:
                query = select(User)
                count_query = select(User)
                
                # 应用基本过滤条件
                if active_only:
                    query = query.where(User.is_active == True)
                    count_query = count_query.where(User.is_active == True)
                
                # 应用搜索过滤条件
                if filters:
                    if filters.get('search'):
                        search_term = f"%{filters['search']}%"
                        search_condition = or_(
                            User.username.like(search_term),
                            User.email.like(search_term),
                            User.full_name.like(search_term)
                        )
                        query = query.where(search_condition)
                        count_query = count_query.where(search_condition)
                    
                    if filters.get('username'):
                        username_term = f"%{filters['username']}%"
                        query = query.where(User.username.like(username_term))
                        count_query = count_query.where(User.username.like(username_term))
                    
                    if filters.get('email'):
                        email_term = f"%{filters['email']}%"
                        query = query.where(User.email.like(email_term))
                        count_query = count_query.where(User.email.like(email_term))
                    
                    if filters.get('role'):
                        if filters['role'] == 'admin':
                            query = query.where(User.is_admin == True)
                            count_query = count_query.where(User.is_admin == True)
                        elif filters['role'] in ['operator', 'viewer']:
                            query = query.where(User.is_admin == False)
                            count_query = count_query.where(User.is_admin == False)
                    
                    if filters.get('status'):
                        if filters['status'] == 'active':
                            query = query.where(User.is_active == True)
                            count_query = count_query.where(User.is_active == True)
                        elif filters['status'] == 'disabled':
                            query = query.where(User.is_active == False)
                            count_query = count_query.where(User.is_active == False)
                
                # 获取总数
                count_result = await session.execute(count_query)
                total = len(count_result.scalars().all())
                
                # 获取分页数据
                query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
                result = await session.execute(query)
                users = result.scalars().all()
                
                return users, total
                
        except Exception as e:
            logger.error(f"Failed to list users paginated: {str(e)}")
            return [], 0
            
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """用户认证"""
        try:
            user = await self.get_user_by_username(username)
            if not user:
                return None
                
            if not user.is_active:
                return None
                
            if not self._verify_password(password, user.password_hash):
                return None
                
            # 更新最后登录时间
            await self.update_user(user.id, {"last_login": datetime.utcnow()})
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to authenticate user {username}: {str(e)}")
            return None
            
    async def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """修改密码"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
                
            if not self._verify_password(old_password, user.password_hash):
                return False
                
            new_password_hash = self._hash_password(new_password)
            await self.update_user(user_id, {"password_hash": new_password_hash})
            
            logger.info(f"Changed password for user: {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to change password for user {user_id}: {str(e)}")
            return False
            
    async def reset_password(self, user_id: int, new_password: str) -> bool:
        """重置密码（管理员操作）"""
        try:
            new_password_hash = self._hash_password(new_password)
            user = await self.update_user(user_id, {"password_hash": new_password_hash})
            
            if user:
                logger.info(f"Reset password for user: {user.username}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to reset password for user {user_id}: {str(e)}")
            return False
            
    async def create_subscription(self, user_id: int, subscription_data: Dict[str, Any]) -> Optional[UserSubscription]:
        """创建用户订阅"""
        try:
            async with async_session_maker() as session:
                subscription = UserSubscription(
                    user_id=user_id,
                    **subscription_data
                )
                
                session.add(subscription)
                await session.commit()
                await session.refresh(subscription)
                
                logger.info(f"Created subscription for user {user_id}")
                return subscription
                
        except Exception as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            return None
            
    async def update_subscription(self, subscription_id: int, update_data: Dict[str, Any]) -> Optional[UserSubscription]:
        """更新用户订阅"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(UserSubscription).where(UserSubscription.id == subscription_id)
                )
                subscription = result.scalars().first()
                
                if not subscription:
                    return None
                    
                for key, value in update_data.items():
                    if hasattr(subscription, key):
                        setattr(subscription, key, value)
                        
                subscription.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(subscription)
                
                return subscription
                
        except Exception as e:
            logger.error(f"Failed to update subscription {subscription_id}: {str(e)}")
            return None
            
    async def delete_subscription(self, subscription_id: int) -> bool:
        """删除用户订阅"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(UserSubscription).where(UserSubscription.id == subscription_id)
                )
                subscription = result.scalars().first()
                
                if not subscription:
                    return False
                    
                await session.delete(subscription)
                await session.commit()
                
                logger.info(f"Deleted subscription {subscription_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete subscription {subscription_id}: {str(e)}")
            return False
            
    async def get_user_subscriptions(self, user_id: int) -> List[UserSubscription]:
        """获取用户订阅列表"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(UserSubscription).where(UserSubscription.user_id == user_id)
                )
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"Failed to get user subscriptions for user {user_id}: {str(e)}")
            return []
            
    async def create_session(self, user_id: int) -> str:
        """创建用户会话"""
        try:
            session_token = secrets.token_urlsafe(32)
            
            self.active_sessions[session_token] = {
                "user_id": user_id,
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow()
            }
            
            logger.info(f"Created session for user {user_id}")
            return session_token
            
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {str(e)}")
            return ""
            
    async def validate_session(self, session_token: str) -> Optional[int]:
        """验证用户会话"""
        try:
            if session_token not in self.active_sessions:
                return None
                
            session_info = self.active_sessions[session_token]
            
            # 检查会话是否过期（24小时）
            if datetime.utcnow() - session_info["created_at"] > timedelta(hours=24):
                del self.active_sessions[session_token]
                return None
                
            # 更新最后活动时间
            session_info["last_activity"] = datetime.utcnow()
            
            return session_info["user_id"]
            
        except Exception as e:
            logger.error(f"Failed to validate session: {str(e)}")
            return None
            
    async def destroy_session(self, session_token: str) -> bool:
        """销毁用户会话"""
        try:
            if session_token in self.active_sessions:
                user_id = self.active_sessions[session_token]["user_id"]
                del self.active_sessions[session_token]
                logger.info(f"Destroyed session for user {user_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to destroy session: {str(e)}")
            return False
            
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{password_hash.hex()}"
        
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            salt, stored_hash = password_hash.split(':', 1)
            password_hash_check = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return stored_hash == password_hash_check.hex()
        except Exception:
            return False
            
    async def get_user_stats(self) -> Dict[str, Any]:
        """获取用户统计信息"""
        try:
            async with async_session_maker() as session:
                # 总用户数
                total_result = await session.execute(select(User))
                total_users = len(total_result.scalars().all())
                
                # 活跃用户数
                active_result = await session.execute(
                    select(User).where(User.is_active == True)
                )
                active_users = len(active_result.scalars().all())
                
                # 管理员用户数
                admin_result = await session.execute(
                    select(User).where(User.is_admin == True)
                )
                admin_users = len(admin_result.scalars().all())
                
                # 总订阅数
                subscription_result = await session.execute(select(UserSubscription))
                total_subscriptions = len(subscription_result.scalars().all())
                
                return {
                    "total_users": total_users,
                    "active_users": active_users,
                    "admin_users": admin_users,
                    "total_subscriptions": total_subscriptions,
                    "active_sessions": len(self.active_sessions)
                }
                
        except Exception as e:
            logger.error(f"Failed to get user stats: {str(e)}")
            return {
                "total_users": 0,
                "active_users": 0,
                "admin_users": 0,
                "total_subscriptions": 0,
                "active_sessions": 0
            }