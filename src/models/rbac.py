"""
RBAC (Role-Based Access Control) 权限控制数据模型
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Table, JSON
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from src.core.database import Base


# 用户角色关联表 (多对多)
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('rbac_roles.id'), primary_key=True),
    Column('assigned_at', DateTime, default=datetime.utcnow),
    Column('assigned_by', Integer, ForeignKey('users.id')),
    Column('expires_at', DateTime, nullable=True)
)

# 为 User 模型添加 roles 关系 (延迟配置避免循环导入)
def configure_user_roles():
    """配置User模型的roles关系"""
    try:
        from src.models.alarm import User
        if not hasattr(User, 'roles'):
            User.roles = relationship(
                "RBACRole",
                secondary=user_roles,
                back_populates="users",
                foreign_keys=[user_roles.c.user_id, user_roles.c.role_id]
            )
    except ImportError:
        # 如果导入失败，忽略配置
        pass

# 角色权限关联表 (多对多)
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('rbac_roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('rbac_permissions.id'), primary_key=True),
    Column('granted_at', DateTime, default=datetime.utcnow),
    Column('granted_by', Integer, ForeignKey('users.id'))
)


class RBACRole(Base):
    """角色表"""
    __tablename__ = 'rbac_roles'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, comment="角色名称")
    display_name = Column(String(200), nullable=False, comment="显示名称")
    description = Column(Text, comment="角色描述")
    
    # 角色类型：system(系统角色), custom(自定义角色)
    role_type = Column(String(20), default='custom', comment="角色类型")
    
    # 角色层级，数字越小权限越高
    level = Column(Integer, default=100, comment="角色层级")
    
    # 角色状态
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_system = Column(Boolean, default=False, comment="是否为系统角色")
    
    # 角色配置 (JSON格式存储额外配置)
    config = Column(JSON, comment="角色配置")
    
    # 时间字段
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    created_by = Column(Integer, ForeignKey('users.id'), comment="创建者")
    
    # 关联关系
    permissions = relationship(
        "RBACPermission",
        secondary=role_permissions,
        back_populates="roles"
    )
    
    users = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
        foreign_keys=[user_roles.c.user_id, user_roles.c.role_id]
    )


class RBACPermission(Base):
    """权限表"""
    __tablename__ = 'rbac_permissions'
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, comment="权限代码")
    name = Column(String(200), nullable=False, comment="权限名称")
    description = Column(Text, comment="权限描述")
    
    # 权限模块 (alarms, users, config, analytics, system 等)
    module = Column(String(50), nullable=False, comment="权限模块")
    
    # 权限操作 (create, read, update, delete, execute 等)
    action = Column(String(50), nullable=False, comment="权限操作")
    
    # 权限资源 (具体的资源标识)
    resource = Column(String(100), comment="权限资源")
    
    # 权限类型：api(接口权限), ui(界面权限), data(数据权限)
    permission_type = Column(String(20), default='api', comment="权限类型")
    
    # 权限级别 (1-10, 数字越大权限级别越高)
    level = Column(Integer, default=1, comment="权限级别")
    
    # 是否为系统权限
    is_system = Column(Boolean, default=False, comment="是否为系统权限")
    is_active = Column(Boolean, default=True, comment="是否激活")
    
    # 权限配置 (JSON格式存储额外配置，如条件限制等)
    config = Column(JSON, comment="权限配置")
    
    # 时间字段
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关联关系
    roles = relationship(
        "RBACRole",
        secondary=role_permissions,
        back_populates="permissions"
    )


class RBACUserPermission(Base):
    """用户直接权限表 (用于特殊权限分配)"""
    __tablename__ = 'rbac_user_permissions'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment="用户ID")
    permission_id = Column(Integer, ForeignKey('rbac_permissions.id'), nullable=False, comment="权限ID")
    
    # 权限来源：direct(直接分配), role(角色继承), temporary(临时权限)
    source = Column(String(20), default='direct', comment="权限来源")
    
    # 是否为临时权限
    is_temporary = Column(Boolean, default=False, comment="是否为临时权限")
    
    # 权限有效期
    expires_at = Column(DateTime, comment="过期时间")
    
    # 分配信息
    assigned_at = Column(DateTime, default=datetime.utcnow, comment="分配时间")
    assigned_by = Column(Integer, ForeignKey('users.id'), comment="分配者")
    assigned_reason = Column(Text, comment="分配原因")
    
    # 关联关系
    user = relationship("User", foreign_keys=[user_id])
    permission = relationship("RBACPermission")
    assigner = relationship("User", foreign_keys=[assigned_by])


class RBACAccessLog(Base):
    """权限访问日志"""
    __tablename__ = 'rbac_access_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment="用户ID")
    
    # 访问信息
    resource = Column(String(200), nullable=False, comment="访问资源")
    action = Column(String(50), nullable=False, comment="执行操作")
    method = Column(String(10), comment="HTTP方法")
    path = Column(String(500), comment="请求路径")
    
    # 权限检查结果
    permission_code = Column(String(100), comment="检查的权限代码")
    access_granted = Column(Boolean, nullable=False, comment="是否授权通过")
    denied_reason = Column(String(500), comment="拒绝原因")
    
    # 请求信息
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(Text, comment="用户代理")
    request_data = Column(JSON, comment="请求数据")
    
    # 时间信息
    accessed_at = Column(DateTime, default=datetime.utcnow, comment="访问时间")
    
    # 关联关系
    user = relationship("User")


# Pydantic 模型 (用于API)

class RBACRoleCreate(BaseModel):
    """创建角色"""
    name: str = Field(..., max_length=100, description="角色名称")
    display_name: str = Field(..., max_length=200, description="显示名称")
    description: Optional[str] = Field(None, description="角色描述")
    level: int = Field(default=100, ge=1, le=1000, description="角色层级")
    config: Optional[Dict[str, Any]] = Field(default=None, description="角色配置")


class RBACRoleUpdate(BaseModel):
    """更新角色"""
    display_name: Optional[str] = Field(None, max_length=200, description="显示名称")
    description: Optional[str] = Field(None, description="角色描述")
    level: Optional[int] = Field(None, ge=1, le=1000, description="角色层级")
    is_active: Optional[bool] = Field(None, description="是否激活")
    config: Optional[Dict[str, Any]] = Field(None, description="角色配置")


class RBACRoleResponse(BaseModel):
    """角色响应"""
    id: int
    name: str
    display_name: str
    description: Optional[str]
    role_type: str
    level: int
    is_active: bool
    is_system: bool
    config: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RBACPermissionCreate(BaseModel):
    """创建权限"""
    code: str = Field(..., max_length=100, description="权限代码")
    name: str = Field(..., max_length=200, description="权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    module: str = Field(..., max_length=50, description="权限模块")
    action: str = Field(..., max_length=50, description="权限操作")
    resource: Optional[str] = Field(None, max_length=100, description="权限资源")
    permission_type: str = Field(default="api", description="权限类型")
    level: int = Field(default=1, ge=1, le=10, description="权限级别")
    config: Optional[Dict[str, Any]] = Field(default=None, description="权限配置")


class RBACPermissionResponse(BaseModel):
    """权限响应"""
    id: int
    code: str
    name: str
    description: Optional[str]
    module: str
    action: str
    resource: Optional[str]
    permission_type: str
    level: int
    is_system: bool
    is_active: bool
    config: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserRoleAssignment(BaseModel):
    """用户角色分配"""
    user_id: int = Field(..., description="用户ID")
    role_ids: List[int] = Field(..., description="角色ID列表")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class UserPermissionAssignment(BaseModel):
    """用户权限分配"""
    user_id: int = Field(..., description="用户ID")
    permission_ids: List[int] = Field(..., description="权限ID列表")
    is_temporary: bool = Field(default=False, description="是否为临时权限")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    reason: Optional[str] = Field(None, description="分配原因")


class AccessLogQuery(BaseModel):
    """访问日志查询"""
    user_id: Optional[int] = Field(None, description="用户ID")
    resource: Optional[str] = Field(None, description="资源")
    action: Optional[str] = Field(None, description="操作")
    access_granted: Optional[bool] = Field(None, description="是否授权")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    limit: int = Field(default=50, ge=1, le=1000, description="限制数量")
    offset: int = Field(default=0, ge=0, description="偏移量")