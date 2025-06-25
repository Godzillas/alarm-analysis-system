"""
告警数据模型
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Generic, TypeVar
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, Float, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

Base = declarative_base()

# 用户-系统关联表
user_system_association = Table(
    'user_systems',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('system_id', Integer, ForeignKey('systems.id'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow)
)


class AlarmSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlarmStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


class AlarmTable(Base):
    __tablename__ = "alarms"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    severity = Column(String(20), nullable=False, index=True)
    status = Column(String(20), default=AlarmStatus.ACTIVE, index=True)
    category = Column(String(50), index=True)
    tags = Column(JSON)
    alarm_metadata = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    host = Column(String(100), index=True)
    service = Column(String(100), index=True)
    environment = Column(String(50), index=True)
    
    count = Column(Integer, default=1)
    first_occurrence = Column(DateTime, default=datetime.utcnow)
    last_occurrence = Column(DateTime, default=datetime.utcnow)
    
    correlation_id = Column(String(100), nullable=True, index=True)
    parent_alarm_id = Column(Integer, nullable=True)
    
    is_duplicate = Column(Boolean, default=False)
    similarity_score = Column(Float, nullable=True)
    
    # 系统关联
    system_id = Column(Integer, ForeignKey('systems.id'), nullable=True, index=True)
    system = relationship("System", back_populates="alarms")


class AlarmMetrics(Base):
    __tablename__ = "alarm_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    alarm_id = Column(Integer, nullable=False, index=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    unit = Column(String(20))


class AlarmRule(Base):
    __tablename__ = "alarm_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    pattern = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)
    category = Column(String(50))
    enabled = Column(Boolean, default=True)
    auto_resolve = Column(Boolean, default=False)
    suppress_duration = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class System(Base):
    __tablename__ = "systems"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    code = Column(String(50), nullable=False, unique=True)  # 系统编码
    owner = Column(String(100))  # 系统负责人
    contact_info = Column(JSON)  # 联系方式
    enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    users = relationship("User", secondary=user_system_association, back_populates="systems")
    alarms = relationship("AlarmTable", back_populates="system")
    endpoints = relationship("Endpoint", back_populates="system")
    contact_points = relationship("ContactPoint", back_populates="system")
    alert_templates = relationship("AlertTemplate", back_populates="system")


class AlarmCreate(BaseModel):
    source: str = Field(..., description="告警源")
    title: str = Field(..., description="告警标题")
    description: Optional[str] = Field(None, description="告警描述")
    severity: AlarmSeverity = Field(..., description="告警级别")
    category: Optional[str] = Field(None, description="告警分类")
    tags: Optional[Dict[str, Any]] = Field(None, description="告警标签")
    alarm_metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    host: Optional[str] = Field(None, description="主机")
    service: Optional[str] = Field(None, description="服务")
    environment: Optional[str] = Field(None, description="环境")


class AlarmUpdate(BaseModel):
    status: Optional[AlarmStatus] = None
    severity: Optional[AlarmSeverity] = None
    description: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    alarm_metadata: Optional[Dict[str, Any]] = None


class AlarmResponse(BaseModel):
    id: int
    source: str
    title: str
    description: Optional[str]
    severity: str
    status: str
    category: Optional[str]
    tags: Optional[Dict[str, Any]]
    alarm_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    host: Optional[str]
    service: Optional[str]
    environment: Optional[str]
    count: int
    first_occurrence: datetime
    last_occurrence: datetime
    correlation_id: Optional[str]
    is_duplicate: bool
    similarity_score: Optional[float]
    
    class Config:
        from_attributes = True


class AlarmStats(BaseModel):
    total: int
    active: int
    resolved: int
    acknowledged: int
    suppressed: int
    critical: int
    high: int
    medium: int
    low: int
    info: int


T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""
    data: List[T]
    total: int
    page: int
    page_size: int
    pages: int


class EndpointType(str, Enum):
    HTTP = "http"
    WEBHOOK = "webhook"
    SYSLOG = "syslog"
    SNMP = "snmp"
    EMAIL = "email"
    API = "api"


class ContactPointType(str, Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"
    SMS = "sms"
    WECHAT = "wechat"


class TemplateType(str, Enum):
    SIMPLE = "simple"
    RICH = "rich"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


class AlertTemplateCategory(str, Enum):
    SYSTEM = "system"
    APPLICATION = "application"
    NETWORK = "network"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CUSTOM = "custom"


class Endpoint(Base):
    __tablename__ = "endpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    endpoint_type = Column(String(20), nullable=False, index=True)
    config = Column(JSON, nullable=False)
    enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # API令牌用于身份验证
    api_token = Column(String(255), nullable=True, unique=True, index=True)
    # 接入URL路径
    webhook_url = Column(String(255), nullable=True)
    # 限流配置
    rate_limit = Column(Integer, default=1000)
    timeout = Column(Integer, default=30)
    # 统计信息
    total_requests = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    
    # 系统关联
    system_id = Column(Integer, ForeignKey('systems.id'), nullable=True, index=True)
    system = relationship("System", back_populates="endpoints")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # 系统关联
    systems = relationship("System", secondary=user_system_association, back_populates="users")


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    subscription_type = Column(String(20), nullable=False)
    filters = Column(JSON, nullable=False)
    notification_methods = Column(JSON, nullable=False)
    enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RuleGroup(Base):
    __tablename__ = "rule_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    priority = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DistributionRule(Base):
    __tablename__ = "distribution_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    rule_group_id = Column(Integer, nullable=False, index=True)
    conditions = Column(JSON, nullable=False)
    actions = Column(JSON, nullable=False)
    priority = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlarmDistribution(Base):
    __tablename__ = "alarm_distributions"
    
    id = Column(Integer, primary_key=True, index=True)
    alarm_id = Column(Integer, nullable=False, index=True)
    rule_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), default="pending")
    notification_sent = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContactPoint(Base):
    __tablename__ = "contact_points"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    contact_type = Column(String(20), nullable=False, index=True)
    config = Column(JSON, nullable=False)
    enabled = Column(Boolean, default=True)
    
    # 通知设置
    retry_count = Column(Integer, default=3)
    retry_interval = Column(Integer, default=300)  # 重试间隔(秒)
    timeout = Column(Integer, default=30)  # 超时时间(秒)
    
    # 统计信息
    total_sent = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_sent = Column(DateTime, nullable=True)
    last_success = Column(DateTime, nullable=True)
    last_failure = Column(DateTime, nullable=True)
    
    # 系统关联
    system_id = Column(Integer, ForeignKey('systems.id'), nullable=True, index=True)
    system = relationship("System", back_populates="contact_points")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertTemplate(Base):
    __tablename__ = "alert_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    category = Column(String(20), nullable=False, index=True)
    template_type = Column(String(20), nullable=False, index=True)
    
    # 模板内容
    title_template = Column(Text, nullable=False)
    content_template = Column(Text, nullable=False)
    summary_template = Column(Text, nullable=True)
    
    # 模板配置
    template_config = Column(JSON, nullable=True)  # 模板特定配置
    field_mapping = Column(JSON, nullable=True)    # 字段映射规则
    conditions = Column(JSON, nullable=True)       # 应用条件
    
    # 兼容性设置
    contact_point_types = Column(JSON, nullable=True)  # 支持的联络点类型
    severity_filter = Column(JSON, nullable=True)      # 严重程度过滤
    source_filter = Column(JSON, nullable=True)        # 来源过滤
    
    # 元数据
    is_default = Column(Boolean, default=False)
    is_builtin = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # 优先级，数字越大优先级越高
    
    # 使用统计
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    
    # 系统关联
    system_id = Column(Integer, ForeignKey('systems.id'), nullable=True, index=True)
    system = relationship("System", back_populates="alert_templates")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EndpointCreate(BaseModel):
    name: str = Field(..., description="接入点名称")
    description: Optional[str] = Field(None, description="接入点描述")
    endpoint_type: EndpointType = Field(..., description="接入点类型")
    config: Dict[str, Any] = Field(..., description="接入点配置")
    system_id: Optional[int] = Field(None, description="所属系统 ID")
    enabled: bool = Field(True, description="是否启用")
    rate_limit: int = Field(1000, description="速率限制")
    timeout: int = Field(30, description="超时时间")


class EndpointUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    system_id: Optional[int] = None
    enabled: Optional[bool] = None
    rate_limit: Optional[int] = None
    timeout: Optional[int] = None


class EndpointResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    endpoint_type: str
    config: Dict[str, Any]
    system_id: Optional[int] = None
    enabled: bool
    created_at: datetime
    updated_at: datetime
    rate_limit: int
    timeout: int
    api_token: Optional[str] = None
    webhook_url: Optional[str] = None
    total_requests: int = 0
    last_used: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    password: str = Field(..., description="密码")
    full_name: Optional[str] = Field(None, description="全名")
    is_admin: bool = Field(False, description="是否管理员")


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    display_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    role: str = "viewer"
    status: str = "active"
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    subscription_count: int = 0
    system_count: int = 0
    
    class Config:
        from_attributes = True
        
    def __init__(self, **data):
        # 映射字段
        if 'full_name' in data and data['full_name']:
            data['display_name'] = data['full_name']
        elif 'display_name' not in data:
            data['display_name'] = data.get('username', '')
            
        # 映射角色
        if 'is_admin' in data:
            data['role'] = 'admin' if data['is_admin'] else 'viewer'
            
        # 映射状态
        if 'is_active' in data:
            data['status'] = 'active' if data['is_active'] else 'disabled'
            
        # 映射最后登录时间
        if 'last_login' in data and data['last_login']:
            data['last_login_at'] = data['last_login']
            
        super().__init__(**data)


class SystemCreate(BaseModel):
    name: str = Field(..., description="系统名称")
    description: Optional[str] = Field(None, description="系统描述")
    code: str = Field(..., description="系统编码")
    owner: Optional[str] = Field(None, description="系统负责人")
    contact_info: Optional[Dict[str, Any]] = Field(None, description="联系方式")
    enabled: bool = Field(True, description="是否启用")


class SystemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    owner: Optional[str] = None
    contact_info: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class SystemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    code: str
    owner: Optional[str]
    contact_info: Optional[Dict[str, Any]]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    subscription_type: str = Field(..., description="订阅类型")
    filters: Dict[str, Any] = Field(..., description="过滤条件")
    notification_methods: List[str] = Field(..., description="通知方式")


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    subscription_type: str
    filters: Dict[str, Any]
    notification_methods: List[str]
    enabled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ContactPointCreate(BaseModel):
    name: str = Field(..., description="联络点名称")
    description: Optional[str] = Field(None, description="联络点描述")
    contact_type: ContactPointType = Field(..., description="联络点类型")
    config: Dict[str, Any] = Field(..., description="联络点配置")
    system_id: Optional[int] = Field(None, description="所属系统 ID")
    enabled: bool = Field(True, description="是否启用")
    retry_count: int = Field(3, description="重试次数")
    retry_interval: int = Field(300, description="重试间隔(秒)")
    timeout: int = Field(30, description="超时时间(秒)")


class ContactPointUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    system_id: Optional[int] = None
    enabled: Optional[bool] = None
    retry_count: Optional[int] = None
    retry_interval: Optional[int] = None
    timeout: Optional[int] = None


class ContactPointResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    contact_type: str
    config: Dict[str, Any]
    system_id: Optional[int]
    enabled: bool
    retry_count: int
    retry_interval: int
    timeout: int
    total_sent: int
    success_count: int
    failure_count: int
    last_sent: Optional[datetime]
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AlertTemplateCreate(BaseModel):
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    category: AlertTemplateCategory = Field(..., description="模板分类")
    template_type: TemplateType = Field(..., description="模板类型")
    title_template: str = Field(..., description="标题模板")
    content_template: str = Field(..., description="内容模板")
    summary_template: Optional[str] = Field(None, description="摘要模板")
    template_config: Optional[Dict[str, Any]] = Field(None, description="模板配置")
    field_mapping: Optional[Dict[str, Any]] = Field(None, description="字段映射")
    conditions: Optional[Dict[str, Any]] = Field(None, description="应用条件")
    contact_point_types: Optional[List[str]] = Field(None, description="支持的联络点类型")
    severity_filter: Optional[List[str]] = Field(None, description="严重程度过滤")
    source_filter: Optional[List[str]] = Field(None, description="来源过滤")
    system_id: Optional[int] = Field(None, description="所属系统ID")
    enabled: bool = Field(True, description="是否启用")
    priority: int = Field(0, description="优先级")


class AlertTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[AlertTemplateCategory] = None
    template_type: Optional[TemplateType] = None
    title_template: Optional[str] = None
    content_template: Optional[str] = None
    summary_template: Optional[str] = None
    template_config: Optional[Dict[str, Any]] = None
    field_mapping: Optional[Dict[str, Any]] = None
    conditions: Optional[Dict[str, Any]] = None
    contact_point_types: Optional[List[str]] = None
    severity_filter: Optional[List[str]] = None
    source_filter: Optional[List[str]] = None
    system_id: Optional[int] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class AlertTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: str
    template_type: str
    title_template: str
    content_template: str
    summary_template: Optional[str]
    template_config: Optional[Dict[str, Any]]
    field_mapping: Optional[Dict[str, Any]]
    conditions: Optional[Dict[str, Any]]
    contact_point_types: Optional[List[str]]
    severity_filter: Optional[List[str]]
    source_filter: Optional[List[str]]
    system_id: Optional[int]
    is_default: bool
    is_builtin: bool
    enabled: bool
    priority: int
    usage_count: int
    last_used: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True