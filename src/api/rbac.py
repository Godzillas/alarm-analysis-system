"""
RBAC权限管理API
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.core.auth import get_current_user
from src.core.rbac import require_permission, admin_required
from src.core.exceptions import DatabaseException, ValidationException, ResourceNotFoundException
from src.services.rbac_service import RBACService
from src.models.rbac import (
    RBACRole, RBACPermission,
    RBACRoleCreate, RBACRoleUpdate, RBACRoleResponse,
    RBACPermissionCreate, RBACPermissionResponse,
    UserRoleAssignment, UserPermissionAssignment
)
from src.models.alarm import User

router = APIRouter(prefix="/api/v1/rbac", tags=["rbac"])


# 角色管理 API

@router.post("/roles", response_model=RBACRoleResponse)
@require_permission("rbac.manage")
async def create_role(
    role_data: RBACRoleCreate,
    current_user: User = Depends(get_current_user)
):
    """创建角色"""
    service = RBACService()
    
    try:
        role = await service.create_role(role_data, current_user.id)
        return RBACRoleResponse.from_orm(role)
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles", response_model=List[RBACRoleResponse])
@require_permission("rbac.manage")
async def get_roles(
    active_only: bool = Query(True, description="只返回活跃角色"),
    limit: int = Query(50, ge=1, le=100, description="限制数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user)
):
    """获取角色列表"""
    service = RBACService()
    
    try:
        roles = await service.get_roles(active_only, limit, offset)
        return [RBACRoleResponse.from_orm(role) for role in roles]
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles/{role_id}", response_model=RBACRoleResponse)
@require_permission("rbac.manage")
async def get_role(
    role_id: int,
    current_user: User = Depends(get_current_user)
):
    """获取角色详情"""
    service = RBACService()
    
    try:
        roles = await service.get_roles(active_only=False, limit=1)
        role = next((r for r in roles if r.id == role_id), None)
        
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        return RBACRoleResponse.from_orm(role)
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/roles/{role_id}", response_model=RBACRoleResponse)
@require_permission("rbac.manage")
async def update_role(
    role_id: int,
    role_data: RBACRoleUpdate,
    current_user: User = Depends(get_current_user)
):
    """更新角色"""
    service = RBACService()
    
    try:
        role = await service.update_role(role_id, role_data, current_user.id)
        return RBACRoleResponse.from_orm(role)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roles/{role_id}/permissions")
@require_permission("rbac.manage")
async def assign_permissions_to_role(
    role_id: int,
    permission_ids: List[int],
    current_user: User = Depends(get_current_user)
):
    """为角色分配权限"""
    service = RBACService()
    
    try:
        success = await service.assign_permissions_to_role(
            role_id, permission_ids, current_user.id
        )
        return {"success": success, "message": "Permissions assigned successfully"}
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


# 权限管理 API

@router.post("/permissions", response_model=RBACPermissionResponse)
@require_permission("rbac.manage")
async def create_permission(
    permission_data: RBACPermissionCreate,
    current_user: User = Depends(get_current_user)
):
    """创建权限"""
    service = RBACService()
    
    try:
        permission = await service.create_permission(permission_data)
        return RBACPermissionResponse.from_orm(permission)
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/permissions", response_model=List[RBACPermissionResponse])
@require_permission("rbac.manage")
async def get_permissions(
    module: Optional[str] = Query(None, description="权限模块"),
    active_only: bool = Query(True, description="只返回活跃权限"),
    limit: int = Query(100, ge=1, le=500, description="限制数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user)
):
    """获取权限列表"""
    service = RBACService()
    
    try:
        permissions = await service.get_permissions(module, active_only, limit, offset)
        return [RBACPermissionResponse.from_orm(perm) for perm in permissions]
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/permissions/modules")
@require_permission("rbac.manage")
async def get_permission_modules(
    current_user: User = Depends(get_current_user)
):
    """获取权限模块列表"""
    service = RBACService()
    
    try:
        permissions = await service.get_permissions(active_only=False, limit=1000)
        modules = list(set(perm.module for perm in permissions))
        modules.sort()
        return {"modules": modules}
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


# 用户角色管理 API

@router.post("/users/{user_id}/roles")
@require_permission("rbac.manage")
async def assign_roles_to_user(
    user_id: int,
    assignment: UserRoleAssignment,
    current_user: User = Depends(get_current_user)
):
    """为用户分配角色"""
    service = RBACService()
    
    try:
        success = await service.assign_roles_to_user(
            assignment.user_id, assignment.role_ids, 
            current_user.id, assignment.expires_at
        )
        return {"success": success, "message": "Roles assigned successfully"}
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """获取用户权限"""
    # 只能查看自己的权限，除非是管理员
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    service = RBACService()
    
    try:
        permissions = await service.get_user_permissions(user_id)
        return {
            "user_id": user_id,
            "permissions": [
                {
                    "id": perm.id,
                    "code": perm.code,
                    "name": perm.name,
                    "module": perm.module,
                    "action": perm.action,
                    "resource": perm.resource
                }
                for perm in permissions
            ]
        }
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/roles")
async def get_user_roles(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """获取用户角色"""
    # 只能查看自己的角色，除非是管理员
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    from src.core.database import async_session_maker
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    async with async_session_maker() as session:
        try:
            user = await session.execute(
                select(User)
                .options(selectinload(User.roles))
                .where(User.id == user_id)
            )
            user_obj = user.scalar_one_or_none()
            
            if not user_obj:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "user_id": user_id,
                "roles": [
                    {
                        "id": role.id,
                        "name": role.name,
                        "display_name": role.display_name,
                        "level": role.level,
                        "is_active": role.is_active
                    }
                    for role in user_obj.roles
                ]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# 权限检查 API

@router.post("/check-permission")
async def check_user_permission(
    permission_code: str,
    resource: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """检查用户权限"""
    service = RBACService()
    
    try:
        has_permission = await service.check_permission(
            user_id=current_user.id,
            permission_code=permission_code,
            resource=resource,
            log_access=False  # API调用不记录访问日志
        )
        
        return {
            "user_id": current_user.id,
            "permission_code": permission_code,
            "resource": resource,
            "has_permission": has_permission
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-permissions")
async def check_user_permissions(
    permission_codes: List[str],
    current_user: User = Depends(get_current_user)
):
    """批量检查用户权限"""
    service = RBACService()
    
    try:
        results = {}
        for permission_code in permission_codes:
            has_permission = await service.check_permission(
                user_id=current_user.id,
                permission_code=permission_code,
                log_access=False
            )
            results[permission_code] = has_permission
        
        return {
            "user_id": current_user.id,
            "permissions": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 系统初始化 API

@router.post("/initialize")
@admin_required
async def initialize_rbac_system(
    current_user: User = Depends(get_current_user)
):
    """初始化RBAC系统"""
    service = RBACService()
    
    try:
        # 创建默认权限
        await service.create_default_permissions()
        
        # 创建默认角色
        await service.create_default_roles()
        
        return {
            "success": True,
            "message": "RBAC system initialized successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 权限缓存管理 API

@router.post("/clear-cache")
@require_permission("rbac.manage")
async def clear_permission_cache(
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """清除权限缓存"""
    service = RBACService()
    service.clear_permission_cache(user_id)
    
    return {
        "success": True,
        "message": f"Permission cache cleared {'for user ' + str(user_id) if user_id else 'for all users'}"
    }


# 访问日志查询 API

@router.get("/access-logs")
@require_permission("rbac.manage")
async def get_access_logs(
    user_id: Optional[int] = Query(None, description="用户ID"),
    resource: Optional[str] = Query(None, description="资源"),
    access_granted: Optional[bool] = Query(None, description="是否授权"),
    limit: int = Query(50, ge=1, le=200, description="限制数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user)
):
    """获取访问日志"""
    from src.core.database import async_session_maker
    from src.models.rbac import RBACAccessLog
    from sqlalchemy import select, and_, desc
    
    async with async_session_maker() as session:
        try:
            query = select(RBACAccessLog).options(
                selectinload(RBACAccessLog.user)
            )
            
            conditions = []
            if user_id:
                conditions.append(RBACAccessLog.user_id == user_id)
            if resource:
                conditions.append(RBACAccessLog.resource.ilike(f"%{resource}%"))
            if access_granted is not None:
                conditions.append(RBACAccessLog.access_granted == access_granted)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.order_by(desc(RBACAccessLog.accessed_at))
            query = query.limit(limit).offset(offset)
            
            result = await session.execute(query)
            logs = result.scalars().all()
            
            return {
                "logs": [
                    {
                        "id": log.id,
                        "user_id": log.user_id,
                        "username": log.user.username if log.user else "Unknown",
                        "resource": log.resource,
                        "action": log.action,
                        "permission_code": log.permission_code,
                        "access_granted": log.access_granted,
                        "denied_reason": log.denied_reason,
                        "ip_address": log.ip_address,
                        "accessed_at": log.accessed_at
                    }
                    for log in logs
                ],
                "total": len(logs),
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))