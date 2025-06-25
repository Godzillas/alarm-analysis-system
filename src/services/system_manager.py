"""
系统管理服务
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import select, and_, update, func
from sqlalchemy.sql import case
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_maker
from src.models.alarm import System, User, user_system_association
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SystemManager:
    """系统管理器"""
    
    def __init__(self):
        pass
        
    async def create_system(self, system_data: Dict[str, Any]) -> Optional[System]:
        """创建系统"""
        try:
            async with async_session_maker() as session:
                system = System(**system_data)
                session.add(system)
                await session.commit()
                await session.refresh(system)
                
                logger.info(f"Created system: {system.name}")
                return system
                
        except Exception as e:
            logger.error(f"Failed to create system: {str(e)}")
            return None
            
    async def get_system(self, system_id: int) -> Optional[System]:
        """获取系统详情"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(System).where(System.id == system_id)
                )
                return result.scalars().first()
                
        except Exception as e:
            logger.error(f"Failed to get system {system_id}: {str(e)}")
            return None
            
    async def get_system_by_code(self, code: str) -> Optional[System]:
        """通过系统编码获取系统"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(System).where(System.code == code)
                )
                return result.scalars().first()
                
        except Exception as e:
            logger.error(f"Failed to get system by code {code}: {str(e)}")
            return None
            
    async def list_systems(
        self, 
        skip: int = 0, 
        limit: int = 100,
        enabled_only: bool = False
    ) -> List[System]:
        """获取系统列表"""
        try:
            async with async_session_maker() as session:
                query = select(System).offset(skip).limit(limit)
                
                if enabled_only:
                    query = query.where(System.enabled == True)
                    
                result = await session.execute(query)
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"Failed to list systems: {str(e)}")
            return []
            
    async def update_system(self, system_id: int, update_data: Dict[str, Any]) -> Optional[System]:
        """更新系统"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(System).where(System.id == system_id)
                )
                system = result.scalars().first()
                
                if not system:
                    return None
                    
                for key, value in update_data.items():
                    if hasattr(system, key):
                        setattr(system, key, value)
                        
                system.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(system)
                
                logger.info(f"Updated system: {system.name}")
                return system
                
        except Exception as e:
            logger.error(f"Failed to update system {system_id}: {str(e)}")
            return None
            
    async def delete_system(self, system_id: int) -> bool:
        """删除系统"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(System).where(System.id == system_id)
                )
                system = result.scalars().first()
                
                if not system:
                    return False
                    
                await session.delete(system)
                await session.commit()
                
                logger.info(f"Deleted system: {system.name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete system {system_id}: {str(e)}")
            return False
            
    async def add_user_to_system(self, user_id: int, system_id: int) -> bool:
        """将用户添加到系统"""
        try:
            async with async_session_maker() as session:
                # 检查用户和系统是否存在
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalars().first()
                
                system_result = await session.execute(
                    select(System).where(System.id == system_id)
                )
                system = system_result.scalars().first()
                
                if not user or not system:
                    return False
                    
                # 检查关联是否已存在
                existing = await session.execute(
                    select(user_system_association).where(
                        and_(
                            user_system_association.c.user_id == user_id,
                            user_system_association.c.system_id == system_id
                        )
                    )
                )
                
                if existing.first():
                    return True  # 已存在关联
                    
                # 创建新关联
                await session.execute(
                    user_system_association.insert().values(
                        user_id=user_id,
                        system_id=system_id,
                        created_at=datetime.utcnow()
                    )
                )
                await session.commit()
                
                logger.info(f"Added user {user_id} to system {system_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add user {user_id} to system {system_id}: {str(e)}")
            return False
            
    async def remove_user_from_system(self, user_id: int, system_id: int) -> bool:
        """从系统中移除用户"""
        try:
            async with async_session_maker() as session:
                await session.execute(
                    user_system_association.delete().where(
                        and_(
                            user_system_association.c.user_id == user_id,
                            user_system_association.c.system_id == system_id
                        )
                    )
                )
                await session.commit()
                
                logger.info(f"Removed user {user_id} from system {system_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to remove user {user_id} from system {system_id}: {str(e)}")
            return False
            
    async def get_user_systems(self, user_id: int) -> List[System]:
        """获取用户关联的系统列表"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(System)
                    .join(user_system_association)
                    .where(user_system_association.c.user_id == user_id)
                    .where(System.enabled == True)
                )
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"Failed to get systems for user {user_id}: {str(e)}")
            return []
            
    async def get_system_users(self, system_id: int) -> List[User]:
        """获取系统关联的用户列表"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(User)
                    .join(user_system_association)
                    .where(user_system_association.c.system_id == system_id)
                    .where(User.is_active == True)
                )
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"Failed to get users for system {system_id}: {str(e)}")
            return []
            
    async def get_system_stats(self, system_id: int) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            async with async_session_maker() as session:
                # 获取告警数量统计
                from src.models.alarm import AlarmTable
                alarm_result = await session.execute(
                    select(
                        func.count(AlarmTable.id).label('total_alarms'),
                        func.sum(case((AlarmTable.status == 'active', 1), else_=0)).label('active_alarms')
                    ).where(AlarmTable.system_id == system_id)
                )
                alarm_stats = alarm_result.first()
                
                # 获取接入点数量
                from src.models.alarm import Endpoint
                endpoint_result = await session.execute(
                    select(func.count(Endpoint.id)).where(
                        and_(
                            Endpoint.system_id == system_id,
                            Endpoint.enabled == True
                        )
                    )
                )
                endpoint_count = endpoint_result.scalar()
                
                # 获取用户数量
                user_result = await session.execute(
                    select(func.count(user_system_association.c.user_id))
                    .where(user_system_association.c.system_id == system_id)
                )
                user_count = user_result.scalar()
                
                return {
                    'total_alarms': alarm_stats.total_alarms or 0,
                    'active_alarms': alarm_stats.active_alarms or 0,
                    'endpoints': endpoint_count or 0,
                    'users': user_count or 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get stats for system {system_id}: {str(e)}")
            return {
                'total_alarms': 0,
                'active_alarms': 0,
                'endpoints': 0,
                'users': 0
            }