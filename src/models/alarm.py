"""
告警数据模型
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field

Base = declarative_base()


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


class EndpointType(str, Enum):
    HTTP = "http"
    WEBHOOK = "webhook"
    SYSLOG = "syslog"
    SNMP = "snmp"
    EMAIL = "email"
    API = "api"


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


class EndpointCreate(BaseModel):
    name: str = Field(..., description="接入点名称")
    description: Optional[str] = Field(None, description="接入点描述")
    endpoint_type: EndpointType = Field(..., description="接入点类型")
    config: Dict[str, Any] = Field(..., description="接入点配置")
    enabled: bool = Field(True, description="是否启用")
    rate_limit: int = Field(1000, description="速率限制")
    timeout: int = Field(30, description="超时时间")


class EndpointUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    rate_limit: Optional[int] = None
    timeout: Optional[int] = None


class EndpointResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    endpoint_type: str
    config: Dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    rate_limit: int
    timeout: int
    
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
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]
    
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