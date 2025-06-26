"""
告警抑制数据模型
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from src.core.database import Base


class SuppressionType(str, Enum):
    """抑制类型"""
    MANUAL = "manual"                    # 手动抑制
    MAINTENANCE = "maintenance"          # 维护抑制
    DEPENDENCY = "dependency"            # 依赖抑制
    SCHEDULE = "schedule"               # 计划抑制
    CONDITIONAL = "conditional"          # 条件抑制
    CASCADE = "cascade"                 # 级联抑制


class SuppressionStatus(str, Enum):
    """抑制状态"""
    ACTIVE = "active"                   # 活跃
    EXPIRED = "expired"                 # 已过期
    CANCELLED = "cancelled"             # 已取消
    PAUSED = "paused"                  # 已暂停


class AlarmSuppression(Base):
    """告警抑制表"""
    __tablename__ = 'alarm_suppressions'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="抑制规则名称")
    description = Column(Text, comment="抑制规则描述")
    
    # 抑制类型和状态
    suppression_type = Column(String(50), nullable=False, comment="抑制类型")
    status = Column(String(20), default=SuppressionStatus.ACTIVE, comment="抑制状态")
    
    # 抑制条件 (JSON格式)
    conditions = Column(JSON, nullable=False, comment="抑制条件")
    
    # 时间设置
    start_time = Column(DateTime, nullable=False, comment="抑制开始时间")
    end_time = Column(DateTime, comment="抑制结束时间")
    
    # 周期性抑制设置
    is_recurring = Column(Boolean, default=False, comment="是否为周期性抑制")
    recurrence_pattern = Column(JSON, comment="周期模式配置")
    
    # 优先级和权重
    priority = Column(Integer, default=100, comment="抑制优先级")
    
    # 抑制动作配置
    action_config = Column(JSON, comment="抑制动作配置")
    
    # 统计信息
    suppressed_count = Column(Integer, default=0, comment="已抑制告警数量")
    last_match = Column(DateTime, comment="最后匹配时间")
    
    # 审计信息
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    created_by = Column(Integer, ForeignKey('users.id'), comment="创建者")
    
    # 关联关系
    creator = relationship("User", foreign_keys=[created_by])
    suppression_logs = relationship("SuppressionLog", back_populates="suppression")


class SuppressionLog(Base):
    """抑制日志表"""
    __tablename__ = 'suppression_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    suppression_id = Column(Integer, ForeignKey('alarm_suppressions.id'), nullable=False, comment="抑制规则ID")
    alarm_id = Column(Integer, ForeignKey('alarms.id'), comment="告警ID")
    
    # 抑制详情
    action = Column(String(50), nullable=False, comment="执行动作")
    reason = Column(Text, comment="抑制原因")
    match_details = Column(JSON, comment="匹配详情")
    
    # 告警信息快照
    alarm_snapshot = Column(JSON, comment="告警信息快照")
    
    # 时间信息
    suppressed_at = Column(DateTime, default=datetime.utcnow, comment="抑制时间")
    
    # 关联关系
    suppression = relationship("AlarmSuppression", back_populates="suppression_logs")
    alarm = relationship("AlarmTable")


class MaintenanceWindow(Base):
    """维护窗口表"""
    __tablename__ = 'maintenance_windows'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="维护窗口名称")
    description = Column(Text, comment="维护描述")
    
    # 时间设置
    start_time = Column(DateTime, nullable=False, comment="维护开始时间")
    end_time = Column(DateTime, nullable=False, comment="维护结束时间")
    
    # 周期性维护
    is_recurring = Column(Boolean, default=False, comment="是否为周期性维护")
    recurrence_pattern = Column(JSON, comment="周期模式")
    
    # 影响范围
    affected_systems = Column(JSON, comment="受影响的系统")
    affected_services = Column(JSON, comment="受影响的服务")
    affected_hosts = Column(JSON, comment="受影响的主机")
    
    # 维护配置
    suppress_all = Column(Boolean, default=False, comment="是否抑制所有告警")
    severity_filter = Column(JSON, comment="按严重程度过滤")
    
    # 通知设置
    notify_before_minutes = Column(Integer, default=30, comment="提前通知时间(分钟)")
    notification_config = Column(JSON, comment="通知配置")
    
    # 状态
    status = Column(String(20), default="scheduled", comment="维护状态")
    
    # 审计信息
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    created_by = Column(Integer, ForeignKey('users.id'), comment="创建者")
    
    # 关联关系
    creator = relationship("User", foreign_keys=[created_by])


class DependencyMap(Base):
    """依赖关系映射表"""
    __tablename__ = 'dependency_maps'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="依赖关系名称")
    description = Column(Text, comment="依赖关系描述")
    
    # 父子关系
    parent_type = Column(String(50), nullable=False, comment="父节点类型")
    parent_identifier = Column(String(200), nullable=False, comment="父节点标识")
    child_type = Column(String(50), nullable=False, comment="子节点类型")
    child_identifier = Column(String(200), nullable=False, comment="子节点标识")
    
    # 依赖配置
    dependency_config = Column(JSON, comment="依赖配置")
    cascade_timeout_minutes = Column(Integer, default=5, comment="级联超时时间")
    
    # 权重和优先级
    weight = Column(Float, default=1.0, comment="依赖权重")
    priority = Column(Integer, default=100, comment="依赖优先级")
    
    # 状态
    enabled = Column(Boolean, default=True, comment="是否启用")
    
    # 审计信息
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    created_by = Column(Integer, ForeignKey('users.id'), comment="创建者")


# Pydantic 模型

class AlarmSuppressionCreate(BaseModel):
    """创建告警抑制"""
    name: str = Field(..., max_length=200, description="抑制规则名称")
    description: Optional[str] = Field(None, description="抑制规则描述")
    suppression_type: SuppressionType = Field(..., description="抑制类型")
    conditions: Dict[str, Any] = Field(..., description="抑制条件")
    start_time: datetime = Field(..., description="抑制开始时间")
    end_time: Optional[datetime] = Field(None, description="抑制结束时间")
    is_recurring: bool = Field(default=False, description="是否为周期性抑制")
    recurrence_pattern: Optional[Dict[str, Any]] = Field(None, description="周期模式配置")
    priority: int = Field(default=100, ge=1, le=1000, description="抑制优先级")
    action_config: Optional[Dict[str, Any]] = Field(None, description="抑制动作配置")


class AlarmSuppressionUpdate(BaseModel):
    """更新告警抑制"""
    name: Optional[str] = Field(None, max_length=200, description="抑制规则名称")
    description: Optional[str] = Field(None, description="抑制规则描述")
    conditions: Optional[Dict[str, Any]] = Field(None, description="抑制条件")
    start_time: Optional[datetime] = Field(None, description="抑制开始时间")
    end_time: Optional[datetime] = Field(None, description="抑制结束时间")
    is_recurring: Optional[bool] = Field(None, description="是否为周期性抑制")
    recurrence_pattern: Optional[Dict[str, Any]] = Field(None, description="周期模式配置")
    priority: Optional[int] = Field(None, ge=1, le=1000, description="抑制优先级")
    action_config: Optional[Dict[str, Any]] = Field(None, description="抑制动作配置")
    status: Optional[SuppressionStatus] = Field(None, description="抑制状态")


class AlarmSuppressionResponse(BaseModel):
    """告警抑制响应"""
    id: int
    name: str
    description: Optional[str]
    suppression_type: str
    status: str
    conditions: Dict[str, Any]
    start_time: datetime
    end_time: Optional[datetime]
    is_recurring: bool
    recurrence_pattern: Optional[Dict[str, Any]]
    priority: int
    action_config: Optional[Dict[str, Any]]
    suppressed_count: int
    last_match: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MaintenanceWindowCreate(BaseModel):
    """创建维护窗口"""
    name: str = Field(..., max_length=200, description="维护窗口名称")
    description: Optional[str] = Field(None, description="维护描述")
    start_time: datetime = Field(..., description="维护开始时间")
    end_time: datetime = Field(..., description="维护结束时间")
    is_recurring: bool = Field(default=False, description="是否为周期性维护")
    recurrence_pattern: Optional[Dict[str, Any]] = Field(None, description="周期模式")
    affected_systems: Optional[List[str]] = Field(None, description="受影响的系统")
    affected_services: Optional[List[str]] = Field(None, description="受影响的服务")
    affected_hosts: Optional[List[str]] = Field(None, description="受影响的主机")
    suppress_all: bool = Field(default=False, description="是否抑制所有告警")
    severity_filter: Optional[List[str]] = Field(None, description="按严重程度过滤")
    notify_before_minutes: int = Field(default=30, ge=0, le=1440, description="提前通知时间")
    notification_config: Optional[Dict[str, Any]] = Field(None, description="通知配置")


class MaintenanceWindowResponse(BaseModel):
    """维护窗口响应"""
    id: int
    name: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    is_recurring: bool
    recurrence_pattern: Optional[Dict[str, Any]]
    affected_systems: Optional[List[str]]
    affected_services: Optional[List[str]]
    affected_hosts: Optional[List[str]]
    suppress_all: bool
    severity_filter: Optional[List[str]]
    notify_before_minutes: int
    notification_config: Optional[Dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DependencyMapCreate(BaseModel):
    """创建依赖关系"""
    name: str = Field(..., max_length=200, description="依赖关系名称")
    description: Optional[str] = Field(None, description="依赖关系描述")
    parent_type: str = Field(..., description="父节点类型")
    parent_identifier: str = Field(..., description="父节点标识")
    child_type: str = Field(..., description="子节点类型")
    child_identifier: str = Field(..., description="子节点标识")
    dependency_config: Optional[Dict[str, Any]] = Field(None, description="依赖配置")
    cascade_timeout_minutes: int = Field(default=5, ge=1, le=60, description="级联超时时间")
    weight: float = Field(default=1.0, ge=0.1, le=10.0, description="依赖权重")
    priority: int = Field(default=100, ge=1, le=1000, description="依赖优先级")


class DependencyMapResponse(BaseModel):
    """依赖关系响应"""
    id: int
    name: str
    description: Optional[str]
    parent_type: str
    parent_identifier: str
    child_type: str
    child_identifier: str
    dependency_config: Optional[Dict[str, Any]]
    cascade_timeout_minutes: int
    weight: float
    priority: int
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SuppressionTestRequest(BaseModel):
    """抑制测试请求"""
    suppression_config: AlarmSuppressionCreate = Field(..., description="抑制配置")
    test_alarms: List[Dict[str, Any]] = Field(..., description="测试告警数据")
    test_time: Optional[datetime] = Field(None, description="测试时间点")


class SuppressionTestResult(BaseModel):
    """抑制测试结果"""
    total_alarms: int = Field(..., description="测试告警总数")
    suppressed_alarms: int = Field(..., description="被抑制的告警数")
    suppression_rate: float = Field(..., description="抑制率")
    test_results: List[Dict[str, Any]] = Field(..., description="详细测试结果")


# 抑制条件模板

SUPPRESSION_TEMPLATES = {
    "manual_host": {
        "name": "主机手动抑制模板",
        "description": "手动抑制指定主机的所有告警",
        "conditions": {
            "hosts": [],
            "severity_filter": None,
            "service_filter": None
        },
        "action_config": {
            "notify_suppressed": True,
            "add_comment": True
        }
    },
    "manual_service": {
        "name": "服务手动抑制模板",
        "description": "手动抑制指定服务的告警",
        "conditions": {
            "services": [],
            "severity_filter": None,
            "hosts": None
        },
        "action_config": {
            "notify_suppressed": True,
            "add_comment": True
        }
    },
    "maintenance_window": {
        "name": "维护窗口抑制模板",
        "description": "在维护窗口期间抑制相关告警",
        "conditions": {
            "maintenance_mode": True,
            "affected_resources": [],
            "severity_threshold": "high"
        },
        "action_config": {
            "notify_before_start": True,
            "notify_after_end": True,
            "aggregate_suppressed": True
        }
    },
    "dependency_cascade": {
        "name": "依赖级联抑制模板", 
        "description": "当父服务出现问题时抑制子服务告警",
        "conditions": {
            "parent_service_status": "down",
            "cascade_rules": {},
            "timeout_minutes": 10
        },
        "action_config": {
            "aggregate_child_alarms": True,
            "max_child_alarms": 50
        }
    }
}