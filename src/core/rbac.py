"""
RBAC权限控制装饰器和工具函数
"""

from functools import wraps
from typing import List, Optional, Callable, Any
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.auth import get_current_user
from src.core.logging import get_logger
from src.models.alarm import User
from src.services.rbac_service import RBACService

logger = get_logger(__name__)
security = HTTPBearer()


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self):
        self.rbac_service = RBACService()
    
    def require_permission(
        self,
        permission_code: str,
        resource: Optional[str] = None,
        check_admin: bool = True
    ):
        """权限检查装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 获取当前用户
                current_user = None
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break
                
                if not current_user:
                    # 从kwargs中查找
                    current_user = kwargs.get('current_user')
                
                if not current_user:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication required"
                    )
                
                # 超级管理员跳过权限检查
                if check_admin and current_user.is_admin:
                    return await func(*args, **kwargs)
                
                # 检查权限
                has_permission = await self.rbac_service.check_permission(
                    user_id=current_user.id,
                    permission_code=permission_code,
                    resource=resource
                )
                
                if not has_permission:
                    logger.warning(
                        f"Permission denied for user {current_user.username}",
                        extra={
                            "user_id": current_user.id,
                            "permission": permission_code,
                            "resource": resource
                        }
                    )
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permission denied: {permission_code}"
                    )
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def require_any_permission(
        self,
        permission_codes: List[str],
        check_admin: bool = True
    ):
        """需要任意一个权限的装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 获取当前用户
                current_user = None
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break
                
                if not current_user:
                    current_user = kwargs.get('current_user')
                
                if not current_user:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication required"
                    )
                
                # 超级管理员跳过权限检查
                if check_admin and current_user.is_admin:
                    return await func(*args, **kwargs)
                
                # 检查是否有任意一个权限
                has_any_permission = await self.rbac_service.has_any_permission(
                    user_id=current_user.id,
                    permission_codes=permission_codes
                )
                
                if not has_any_permission:
                    logger.warning(
                        f"Permission denied for user {current_user.username}",
                        extra={
                            "user_id": current_user.id,
                            "required_permissions": permission_codes
                        }
                    )
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permission denied: requires any of {permission_codes}"
                    )
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def require_all_permissions(
        self,
        permission_codes: List[str],
        check_admin: bool = True
    ):
        """需要所有权限的装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 获取当前用户
                current_user = None
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break
                
                if not current_user:
                    current_user = kwargs.get('current_user')
                
                if not current_user:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication required"
                    )
                
                # 超级管理员跳过权限检查
                if check_admin and current_user.is_admin:
                    return await func(*args, **kwargs)
                
                # 检查是否有所有权限
                has_all_permissions = await self.rbac_service.has_all_permissions(
                    user_id=current_user.id,
                    permission_codes=permission_codes
                )
                
                if not has_all_permissions:
                    logger.warning(
                        f"Permission denied for user {current_user.username}",
                        extra={
                            "user_id": current_user.id,
                            "required_permissions": permission_codes
                        }
                    )
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permission denied: requires all of {permission_codes}"
                    )
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator


# 全局权限检查器实例
permission_checker = PermissionChecker()

# 快捷装饰器
def require_permission(permission_code: str, resource: Optional[str] = None):
    """需要指定权限"""
    return permission_checker.require_permission(permission_code, resource)

def require_any_permission(permission_codes: List[str]):
    """需要任意一个权限"""
    return permission_checker.require_any_permission(permission_codes)

def require_all_permissions(permission_codes: List[str]):
    """需要所有权限"""
    return permission_checker.require_all_permissions(permission_codes)

def admin_required(func: Callable) -> Callable:
    """管理员权限装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 获取当前用户
        current_user = None
        for arg in args:
            if isinstance(arg, User):
                current_user = arg
                break
        
        if not current_user:
            current_user = kwargs.get('current_user')
        
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
        
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Administrator privileges required"
            )
        
        return await func(*args, **kwargs)
    
    return wrapper


# FastAPI依赖项
async def check_permission_dependency(
    permission_code: str,
    resource: Optional[str] = None
):
    """权限检查依赖项生成器"""
    async def permission_dependency(
        current_user: User = Depends(get_current_user)
    ):
        if current_user.is_admin:
            return current_user
        
        rbac_service = RBACService()
        has_permission = await rbac_service.check_permission(
            user_id=current_user.id,
            permission_code=permission_code,
            resource=resource
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission_code}"
            )
        
        return current_user
    
    return permission_dependency


async def get_user_with_permissions(
    current_user: User = Depends(get_current_user)
) -> tuple[User, List[str]]:
    """获取用户及其权限列表"""
    rbac_service = RBACService()
    permissions = await rbac_service.get_user_permissions(current_user.id)
    permission_codes = [perm.code for perm in permissions]
    
    return current_user, permission_codes


class RBACMiddleware:
    """RBAC中间件"""
    
    def __init__(self, app):
        self.app = app
        self.rbac_service = RBACService()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # 跳过不需要权限检查的路径
            if self._should_skip_check(request.url.path):
                await self.app(scope, receive, send)
                return
            
            # 权限检查逻辑
            try:
                await self._check_request_permission(request)
            except HTTPException as e:
                # 返回权限错误
                response = {
                    "detail": e.detail,
                    "status_code": e.status_code
                }
                await send({
                    'type': 'http.response.start',
                    'status': e.status_code,
                    'headers': [[b'content-type', b'application/json']],
                })
                await send({
                    'type': 'http.response.body',
                    'body': str(response).encode(),
                })
                return
        
        await self.app(scope, receive, send)
    
    def _should_skip_check(self, path: str) -> bool:
        """检查是否应该跳过权限检查"""
        skip_paths = [
            "/api/auth/",
            "/docs",
            "/openapi.json",
            "/health",
            "/static/",
            "/favicon.ico"
        ]
        
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    async def _check_request_permission(self, request: Request):
        """检查请求权限"""
        # 这里可以实现基于路径和方法的权限检查
        # 例如：根据URL路径自动映射到权限代码
        pass


# 数据权限过滤器
class DataPermissionFilter:
    """数据权限过滤器"""
    
    def __init__(self):
        self.rbac_service = RBACService()
    
    async def filter_alarms(
        self,
        user: User,
        alarms: List[dict]
    ) -> List[dict]:
        """过滤告警数据"""
        if user.is_admin:
            return alarms
        
        # 根据用户权限过滤告警数据
        filtered_alarms = await self.rbac_service.filter_data_by_permission(
            user_id=user.id,
            data_type="alarms",
            data_items=alarms
        )
        
        return filtered_alarms
    
    async def filter_users(
        self,
        user: User,
        users: List[dict]
    ) -> List[dict]:
        """过滤用户数据"""
        if user.is_admin:
            return users
        
        # 非管理员只能看到自己
        return [u for u in users if u.get('id') == user.id]
    
    async def can_access_resource(
        self,
        user: User,
        resource_type: str,
        resource_id: Optional[int] = None
    ) -> bool:
        """检查是否可以访问指定资源"""
        if user.is_admin:
            return True
        
        # 根据资源类型检查权限
        permission_code = f"{resource_type}.read"
        resource_identifier = f"{resource_type}:{resource_id}" if resource_id else None
        
        return await self.rbac_service.check_permission(
            user_id=user.id,
            permission_code=permission_code,
            resource=resource_identifier,
            log_access=False
        )


# 全局数据权限过滤器实例
data_filter = DataPermissionFilter()


# 权限工具函数
async def get_user_accessible_systems(user: User) -> List[int]:
    """获取用户可访问的系统ID列表"""
    if user.is_admin:
        # 管理员可以访问所有系统
        return []  # 空列表表示无限制
    
    # 根据用户角色和权限确定可访问的系统
    rbac_service = RBACService()
    permissions = await rbac_service.get_user_permissions(user.id)
    
    accessible_systems = []
    for perm in permissions:
        if perm.permission_type == "data" and perm.resource == "systems":
            # 从权限配置中解析可访问的系统ID
            if perm.config and "system_ids" in perm.config:
                accessible_systems.extend(perm.config["system_ids"])
    
    return list(set(accessible_systems))


async def check_resource_ownership(
    user: User,
    resource_type: str,
    resource_data: dict
) -> bool:
    """检查资源所有权"""
    if user.is_admin:
        return True
    
    # 检查用户是否为资源所有者
    owner_field_map = {
        "alarms": "created_by",
        "subscriptions": "user_id",
        "templates": "created_by"
    }
    
    owner_field = owner_field_map.get(resource_type)
    if owner_field and resource_data.get(owner_field) == user.id:
        return True
    
    return False