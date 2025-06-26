"""
RBAC权限控制服务
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete, update
from sqlalchemy.orm import selectinload

from src.core.database import async_session_maker
from src.core.logging import get_logger
from src.core.exceptions import (
    DatabaseException, ValidationException, 
    ResourceNotFoundException, AuthorizationException
)
from src.models.rbac import (
    RBACRole, RBACPermission, RBACUserPermission, RBACAccessLog,
    RBACRoleCreate, RBACRoleUpdate, RBACPermissionCreate,
    configure_user_roles
)
from src.models.alarm import User

logger = get_logger(__name__)

# 配置函数将在需要时调用，避免循环导入
# configure_user_roles()  # 注释掉，在首次使用时调用


class RBACService:
    """RBAC权限控制服务"""
    
    def __init__(self):
        self.logger = logger
        # 权限缓存，减少数据库查询
        self._permission_cache = {}
        self._cache_ttl = 300  # 5分钟缓存
        
        # 配置User模型的roles关系（在首次使用时）
        try:
            configure_user_roles()
        except Exception as e:
            self.logger.warning(f"Could not configure user roles: {str(e)}")
    
    # 角色管理
    
    async def create_role(
        self,
        role_data: RBACRoleCreate,
        creator_id: int
    ) -> RBACRole:
        """创建角色"""
        async with async_session_maker() as session:
            try:
                # 检查角色名是否重复
                existing = await session.execute(
                    select(RBACRole).where(RBACRole.name == role_data.name)
                )
                if existing.scalar_one_or_none():
                    raise ValidationException(
                        "Role with this name already exists",
                        field="name"
                    )
                
                role = RBACRole(
                    name=role_data.name,
                    display_name=role_data.display_name,
                    description=role_data.description,
                    level=role_data.level,
                    config=role_data.config,
                    created_by=creator_id
                )
                
                session.add(role)
                await session.commit()
                await session.refresh(role)
                
                self.logger.info(
                    f"Created role: {role.name}",
                    extra={"role_id": role.id, "creator_id": creator_id}
                )
                
                return role
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, ValidationException):
                    raise
                raise DatabaseException(f"Failed to create role: {str(e)}")
    
    async def get_roles(
        self,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[RBACRole]:
        """获取角色列表"""
        async with async_session_maker() as session:
            try:
                query = select(RBACRole).options(
                    selectinload(RBACRole.permissions)
                )
                
                if active_only:
                    query = query.where(RBACRole.is_active == True)
                
                query = query.order_by(RBACRole.level, RBACRole.name)
                query = query.limit(limit).offset(offset)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                raise DatabaseException(f"Failed to get roles: {str(e)}")
    
    async def update_role(
        self,
        role_id: int,
        role_data: RBACRoleUpdate,
        updater_id: int
    ) -> RBACRole:
        """更新角色"""
        async with async_session_maker() as session:
            try:
                role = await session.get(RBACRole, role_id)
                if not role:
                    raise ResourceNotFoundException("RBACRole", role_id)
                
                # 系统角色不能修改
                if role.is_system:
                    raise ValidationException("Cannot modify system role")
                
                # 更新字段
                for field, value in role_data.dict(exclude_unset=True).items():
                    setattr(role, field, value)
                
                role.updated_at = datetime.utcnow()
                await session.commit()
                
                self.logger.info(
                    f"Updated role: {role.name}",
                    extra={"role_id": role_id, "updater_id": updater_id}
                )
                
                return role
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, (ValidationException, ResourceNotFoundException)):
                    raise
                raise DatabaseException(f"Failed to update role: {str(e)}")
    
    # 权限管理
    
    async def create_permission(
        self,
        permission_data: RBACPermissionCreate
    ) -> RBACPermission:
        """创建权限"""
        async with async_session_maker() as session:
            try:
                # 检查权限代码是否重复
                existing = await session.execute(
                    select(RBACPermission).where(
                        RBACPermission.code == permission_data.code
                    )
                )
                if existing.scalar_one_or_none():
                    raise ValidationException(
                        "Permission with this code already exists",
                        field="code"
                    )
                
                permission = RBACPermission(**permission_data.dict())
                session.add(permission)
                await session.commit()
                await session.refresh(permission)
                
                self.logger.info(f"Created permission: {permission.code}")
                return permission
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, ValidationException):
                    raise
                raise DatabaseException(f"Failed to create permission: {str(e)}")
    
    async def get_permissions(
        self,
        module: Optional[str] = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[RBACPermission]:
        """获取权限列表"""
        async with async_session_maker() as session:
            try:
                query = select(RBACPermission)
                
                conditions = []
                if module:
                    conditions.append(RBACPermission.module == module)
                if active_only:
                    conditions.append(RBACPermission.is_active == True)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                query = query.order_by(
                    RBACPermission.module,
                    RBACPermission.action,
                    RBACPermission.resource
                )
                query = query.limit(limit).offset(offset)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                raise DatabaseException(f"Failed to get permissions: {str(e)}")
    
    # 角色权限关联
    
    async def assign_permissions_to_role(
        self,
        role_id: int,
        permission_ids: List[int],
        assigned_by: int
    ) -> bool:
        """为角色分配权限"""
        async with async_session_maker() as session:
            try:
                # 检查角色是否存在
                role = await session.get(RBACRole, role_id)
                if not role:
                    raise ResourceNotFoundException("RBACRole", role_id)
                
                # 检查权限是否存在
                permissions = await session.execute(
                    select(RBACPermission).where(
                        RBACPermission.id.in_(permission_ids)
                    )
                )
                permission_list = permissions.scalars().all()
                
                if len(permission_list) != len(permission_ids):
                    raise ValidationException("Some permissions not found")
                
                # 清除现有权限关联
                role.permissions.clear()
                
                # 添加新的权限关联
                role.permissions.extend(permission_list)
                
                await session.commit()
                
                self.logger.info(
                    f"Assigned {len(permission_ids)} permissions to role {role.name}",
                    extra={
                        "role_id": role_id,
                        "permission_count": len(permission_ids),
                        "assigned_by": assigned_by
                    }
                )
                
                return True
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, (ValidationException, ResourceNotFoundException)):
                    raise
                raise DatabaseException(f"Failed to assign permissions: {str(e)}")
    
    # 用户角色关联
    
    async def assign_roles_to_user(
        self,
        user_id: int,
        role_ids: List[int],
        assigned_by: int,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """为用户分配角色"""
        async with async_session_maker() as session:
            try:
                # 检查用户是否存在
                user = await session.get(User, user_id)
                if not user:
                    raise ResourceNotFoundException("User", user_id)
                
                # 检查角色是否存在
                roles = await session.execute(
                    select(RBACRole).where(
                        and_(
                            RBACRole.id.in_(role_ids),
                            RBACRole.is_active == True
                        )
                    )
                )
                role_list = roles.scalars().all()
                
                if len(role_list) != len(role_ids):
                    raise ValidationException("Some roles not found or inactive")
                
                # 清除现有角色关联
                user.roles.clear()
                
                # 添加新的角色关联
                user.roles.extend(role_list)
                
                await session.commit()
                
                self.logger.info(
                    f"Assigned {len(role_ids)} roles to user {user.username}",
                    extra={
                        "user_id": user_id,
                        "role_count": len(role_ids),
                        "assigned_by": assigned_by
                    }
                )
                
                return True
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, (ValidationException, ResourceNotFoundException)):
                    raise
                raise DatabaseException(f"Failed to assign roles: {str(e)}")
    
    # 权限检查
    
    async def check_permission(
        self,
        user_id: int,
        permission_code: str,
        resource: Optional[str] = None,
        log_access: bool = True
    ) -> bool:
        """检查用户权限"""
        try:
            # 获取用户权限
            user_permissions = await self.get_user_permissions(user_id)
            
            # 检查权限
            has_permission = False
            
            for perm in user_permissions:
                if perm.code == permission_code:
                    # 检查资源匹配
                    if not resource or not perm.resource or perm.resource == resource:
                        has_permission = True
                        break
                    # 支持通配符匹配
                    if perm.resource.endswith("*") and resource.startswith(perm.resource[:-1]):
                        has_permission = True
                        break
            
            # 记录访问日志
            if log_access:
                await self._log_access(
                    user_id=user_id,
                    permission_code=permission_code,
                    resource=resource,
                    access_granted=has_permission
                )
            
            return has_permission
            
        except Exception as e:
            self.logger.error(f"Error checking permission: {str(e)}")
            return False
    
    async def get_user_permissions(self, user_id: int) -> List[RBACPermission]:
        """获取用户的所有权限"""
        # 使用缓存
        cache_key = f"user_permissions_{user_id}"
        cached = self._permission_cache.get(cache_key)
        if cached and cached['expires'] > datetime.utcnow():
            return cached['permissions']
        
        async with async_session_maker() as session:
            try:
                user = await session.execute(
                    select(User)
                    .options(
                        selectinload(User.roles)
                        .selectinload(RBACRole.permissions)
                    )
                    .where(User.id == user_id)
                )
                user_obj = user.scalar_one_or_none()
                
                if not user_obj:
                    return []
                
                # 从角色获取权限
                permissions = []
                permission_ids = set()
                
                for role in user_obj.roles:
                    if role.is_active:
                        for perm in role.permissions:
                            if perm.is_active and perm.id not in permission_ids:
                                permissions.append(perm)
                                permission_ids.add(perm.id)
                
                # 获取用户直接分配的权限
                direct_permissions = await session.execute(
                    select(RBACUserPermission)
                    .options(selectinload(RBACUserPermission.permission))
                    .where(
                        and_(
                            RBACUserPermission.user_id == user_id,
                            or_(
                                RBACUserPermission.expires_at.is_(None),
                                RBACUserPermission.expires_at > datetime.utcnow()
                            )
                        )
                    )
                )
                
                for user_perm in direct_permissions.scalars():
                    perm = user_perm.permission
                    if perm.is_active and perm.id not in permission_ids:
                        permissions.append(perm)
                        permission_ids.add(perm.id)
                
                # 缓存结果
                self._permission_cache[cache_key] = {
                    'permissions': permissions,
                    'expires': datetime.utcnow() + timedelta(seconds=self._cache_ttl)
                }
                
                return permissions
                
            except Exception as e:
                self.logger.error(f"Error getting user permissions: {str(e)}")
                return []
    
    async def has_any_permission(
        self,
        user_id: int,
        permission_codes: List[str]
    ) -> bool:
        """检查用户是否有任意一个权限"""
        user_permissions = await self.get_user_permissions(user_id)
        user_codes = {perm.code for perm in user_permissions}
        
        return bool(user_codes.intersection(set(permission_codes)))
    
    async def has_all_permissions(
        self,
        user_id: int,
        permission_codes: List[str]
    ) -> bool:
        """检查用户是否有所有权限"""
        user_permissions = await self.get_user_permissions(user_id)
        user_codes = {perm.code for perm in user_permissions}
        
        return set(permission_codes).issubset(user_codes)
    
    # 数据权限
    
    async def filter_data_by_permission(
        self,
        user_id: int,
        data_type: str,
        data_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """根据数据权限过滤数据"""
        # 获取用户的数据权限配置
        user_permissions = await self.get_user_permissions(user_id)
        
        # 查找数据权限
        data_permission = None
        for perm in user_permissions:
            if perm.permission_type == "data" and perm.resource == data_type:
                data_permission = perm
                break
        
        if not data_permission or not data_permission.config:
            # 没有数据权限配置，返回空列表或根据默认策略
            return []
        
        # 应用数据过滤规则
        filtered_items = []
        filter_config = data_permission.config
        
        for item in data_items:
            if self._check_data_access(item, filter_config):
                filtered_items.append(item)
        
        return filtered_items
    
    # 系统初始化
    
    async def create_default_permissions(self):
        """创建默认权限"""
        default_permissions = [
            # 告警管理权限
            {"code": "alarms.read", "name": "查看告警", "module": "alarms", "action": "read"},
            {"code": "alarms.create", "name": "创建告警", "module": "alarms", "action": "create"},
            {"code": "alarms.update", "name": "更新告警", "module": "alarms", "action": "update"},
            {"code": "alarms.delete", "name": "删除告警", "module": "alarms", "action": "delete"},
            {"code": "alarms.acknowledge", "name": "确认告警", "module": "alarms", "action": "acknowledge"},
            {"code": "alarms.resolve", "name": "解决告警", "module": "alarms", "action": "resolve"},
            
            # 用户管理权限
            {"code": "users.read", "name": "查看用户", "module": "users", "action": "read"},
            {"code": "users.create", "name": "创建用户", "module": "users", "action": "create"},
            {"code": "users.update", "name": "更新用户", "module": "users", "action": "update"},
            {"code": "users.delete", "name": "删除用户", "module": "users", "action": "delete"},
            
            # 配置管理权限
            {"code": "config.read", "name": "查看配置", "module": "config", "action": "read"},
            {"code": "config.update", "name": "更新配置", "module": "config", "action": "update"},
            
            # 分析统计权限
            {"code": "analytics.read", "name": "查看分析", "module": "analytics", "action": "read"},
            {"code": "analytics.export", "name": "导出分析", "module": "analytics", "action": "export"},
            
            # 系统管理权限
            {"code": "system.manage", "name": "系统管理", "module": "system", "action": "manage"},
            {"code": "system.backup", "name": "系统备份", "module": "system", "action": "backup"},
            {"code": "rbac.manage", "name": "权限管理", "module": "rbac", "action": "manage"},
        ]
        
        async with async_session_maker() as session:
            try:
                for perm_data in default_permissions:
                    # 检查是否已存在
                    existing = await session.execute(
                        select(RBACPermission).where(
                            RBACPermission.code == perm_data["code"]
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue
                    
                    permission = RBACPermission(
                        is_system=True,
                        **perm_data
                    )
                    session.add(permission)
                
                await session.commit()
                self.logger.info("Created default permissions")
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error creating default permissions: {str(e)}")
    
    async def create_default_roles(self):
        """创建默认角色"""
        async with async_session_maker() as session:
            try:
                # 获取所有权限
                all_permissions = await session.execute(select(RBACPermission))
                permissions = {p.code: p for p in all_permissions.scalars()}
                
                default_roles = [
                    {
                        "name": "super_admin",
                        "display_name": "超级管理员",
                        "description": "拥有系统所有权限",
                        "level": 1,
                        "permissions": list(permissions.keys())
                    },
                    {
                        "name": "admin",
                        "display_name": "系统管理员",
                        "description": "系统管理权限",
                        "level": 10,
                        "permissions": [
                            "alarms.read", "alarms.update", "alarms.acknowledge", "alarms.resolve",
                            "users.read", "users.create", "users.update",
                            "config.read", "config.update",
                            "analytics.read", "analytics.export"
                        ]
                    },
                    {
                        "name": "operator",
                        "display_name": "运维人员",
                        "description": "告警处理权限",
                        "level": 20,
                        "permissions": [
                            "alarms.read", "alarms.acknowledge", "alarms.resolve",
                            "analytics.read"
                        ]
                    },
                    {
                        "name": "viewer",
                        "display_name": "只读用户",
                        "description": "只能查看信息",
                        "level": 30,
                        "permissions": [
                            "alarms.read",
                            "analytics.read"
                        ]
                    }
                ]
                
                for role_data in default_roles:
                    # 检查是否已存在
                    existing = await session.execute(
                        select(RBACRole).where(RBACRole.name == role_data["name"])
                    )
                    if existing.scalar_one_or_none():
                        continue
                    
                    role = RBACRole(
                        name=role_data["name"],
                        display_name=role_data["display_name"],
                        description=role_data["description"],
                        level=role_data["level"],
                        role_type="system",
                        is_system=True,
                        created_by=1  # 系统用户
                    )
                    
                    # 添加权限
                    role_permissions = []
                    for perm_code in role_data["permissions"]:
                        if perm_code in permissions:
                            role_permissions.append(permissions[perm_code])
                    
                    role.permissions = role_permissions
                    session.add(role)
                
                await session.commit()
                self.logger.info("Created default roles")
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error creating default roles: {str(e)}")
    
    # 私有方法
    
    async def _log_access(
        self,
        user_id: int,
        permission_code: str,
        resource: Optional[str],
        access_granted: bool,
        **kwargs
    ):
        """记录访问日志"""
        try:
            async with async_session_maker() as session:
                log = RBACAccessLog(
                    user_id=user_id,
                    resource=resource or permission_code,
                    action=permission_code,
                    permission_code=permission_code,
                    access_granted=access_granted,
                    **kwargs
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            # 日志记录失败不应该影响业务流程
            self.logger.error(f"Failed to log access: {str(e)}")
    
    def _check_data_access(
        self,
        data_item: Dict[str, Any],
        filter_config: Dict[str, Any]
    ) -> bool:
        """检查数据访问权限"""
        # 实现数据级权限过滤逻辑
        # 这里可以根据filter_config中的规则来判断是否有权限访问数据项
        return True  # 默认允许访问
    
    def clear_permission_cache(self, user_id: Optional[int] = None):
        """清除权限缓存"""
        if user_id:
            cache_key = f"user_permissions_{user_id}"
            self._permission_cache.pop(cache_key, None)
        else:
            self._permission_cache.clear()