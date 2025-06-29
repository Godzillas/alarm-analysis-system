"""
告警抑制数据模型
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, model_validator
from typing import Union

from src.core.database import Base


# --- New Pydantic Models for Conditions and Action Configs ---

# Base models for conditions and action configs
class BaseSuppressionConditions(BaseModel):
    """Base class for suppression rule conditions."""
    pass

class BaseSuppressionActionConfig(BaseModel):
    """Base class for suppression rule action configurations."""
    pass

# Specific Conditions Models
class ManualConditions(BaseSuppressionConditions):
    suppression_type: Literal["manual"] = Field(default="manual", description="抑制类型")
    hosts: Optional[List[str]] = Field(None, description="受影响的主机列表")
    services: Optional[List[str]] = Field(None, description="受影响的服务列表")
    severity_filter: Optional[List[str]] = Field(None, description="按严重程度过滤")
    tags: Optional[List[str]] = Field(None, description="标签过滤")

    @model_validator(mode='after')
    def check_at_least_one_filter(self):
        if not any([self.hosts, self.services, self.severity_filter, self.tags]):
            raise ValueError("At least one of hosts, services, severity_filter, or tags must be provided.")
        return self

class MaintenanceConditions(BaseSuppressionConditions):
    suppression_type: Literal["maintenance"] = Field(default="maintenance", description="抑制类型")
    maintenance_mode: bool = Field(True, description="是否为维护模式")
    affected_resources: Optional[List[str]] = Field(None, description="受影响的资源列表 (e.g., host, service)")
    severity_threshold: Optional[str] = Field(None, description="严重程度阈值 (e.g., high, critical)")

class DependencyConditions(BaseSuppressionConditions):
    suppression_type: Literal["dependency"] = Field(default="dependency", description="抑制类型")
    parent_service_status: str = Field(..., description="父服务状态 (e.g., down, degraded)")
    cascade_rules: Dict[str, Any] = Field(..., description="级联规则配置")
    timeout_minutes: int = Field(10, description="级联超时时间（分钟）")

class ScheduleConditions(BaseSuppressionConditions):
    suppression_type: Literal["schedule"] = Field(default="schedule", description="抑制类型")
    cron_schedule: str = Field(..., description="Cron 表达式")
    duration_minutes: int = Field(..., description="抑制持续时间（分钟）")
    affected_resources: Optional[List[str]] = Field(None, description="受影响的资源列表")

class ConditionalConditions(BaseSuppressionConditions):
    suppression_type: Literal["conditional"] = Field(default="conditional", description="抑制类型")
    expression: Optional[str] = Field(None, description="自定义条件表达式")
    condition_groups: Optional[List[Dict[str, Any]]] = Field(None, description="条件组") # Using Dict for now, can be refined later

    @model_validator(mode='after')
    def check_expression_or_groups(self):
        if not self.expression and not self.condition_groups:
            raise ValueError("Either 'expression' or 'condition_groups' must be provided for conditional rules.")
        return self

class CascadeConditions(BaseSuppressionConditions):
    suppression_type: Literal["cascade"] = Field(default="cascade", description="抑制类型")
    root_alarm_fingerprint: str = Field(..., description="根告警指纹")
    max_cascade_depth: int = Field(5, description="最大级联深度")
    time_window_minutes: int = Field(30, description="级联时间窗口（分钟）")

# Specific Action Config Models
class ManualActionConfig(BaseSuppressionActionConfig):
    suppression_type: Literal["manual"] = Field(default="manual", description="抑制类型")
    notify_suppressed: bool = Field(True, description="是否通知被抑制的告警")
    add_comment: bool = Field(True, description="是否添加评论")

class MaintenanceActionConfig(BaseSuppressionActionConfig):
    suppression_type: Literal["maintenance"] = Field(default="maintenance", description="抑制类型")
    notify_before_start: bool = Field(True, description="是否在开始前通知")
    notify_after_end: bool = Field(True, description="是否在结束后通知")
    aggregate_suppressed: bool = Field(True, description="是否聚合被抑制的告警")

class DependencyActionConfig(BaseSuppressionActionConfig):
    suppression_type: Literal["dependency"] = Field(default="dependency", description="抑制类型")
    aggregate_child_alarms: bool = Field(True, description="是否聚合子告警")
    max_child_alarms: int = Field(50, description="最大子告警数量")

class DefaultActionConfig(BaseSuppressionActionConfig):
    """Default action config for suppressions without specific configurations."""
    suppression_type: Literal["default"] = Field(default="default", description="抑制类型")

# --- Updated Pydantic Models for Create/Update/Response ---


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
    conditions: Union[
        ManualConditions,
        MaintenanceConditions,
        DependencyConditions,
        ScheduleConditions,
        ConditionalConditions,
        CascadeConditions
    ] = Field(..., discriminator='suppression_type', description="抑制条件")
    start_time: datetime = Field(..., description="抑制开始时间")
    end_time: Optional[datetime] = Field(None, description="抑制结束时间")
    is_recurring: bool = Field(default=False, description="是否为周期性抑制")
    recurrence_pattern: Optional[Dict[str, Any]] = Field(None, description="周期模式配置")
    priority: int = Field(default=100, ge=1, le=1000, description="抑制优先级")
    action_config: Optional[Union[
        ManualActionConfig,
        MaintenanceActionConfig,
        DependencyActionConfig,
        DefaultActionConfig
    ]] = Field(None, discriminator='suppression_type', description="抑制动作配置")

    @model_validator(mode='before')
    @classmethod
    def validate_conditions_and_action_config(cls, data: Any) -> Any:
        if isinstance(data, dict):
            suppression_type = data.get('suppression_type')
            conditions_data = data.get('conditions')
            action_config_data = data.get('action_config')

            if suppression_type == SuppressionType.MANUAL:
                data['conditions'] = ManualConditions(**conditions_data).model_dump()
                if action_config_data:
                    data['action_config'] = ManualActionConfig(**action_config_data).model_dump()
            elif suppression_type == SuppressionType.MAINTENANCE:
                data['conditions'] = MaintenanceConditions(**conditions_data).model_dump()
                if action_config_data:
                    data['action_config'] = MaintenanceActionConfig(**action_config_data).model_dump()
            elif suppression_type == SuppressionType.DEPENDENCY:
                data['conditions'] = DependencyConditions(**conditions_data).model_dump()
                if action_config_data:
                    data['action_config'] = DependencyActionConfig(**action_config_data).model_dump()
            elif suppression_type == SuppressionType.SCHEDULE:
                data['conditions'] = ScheduleConditions(**conditions_data).model_dump()
            elif suppression_type == SuppressionType.CONDITIONAL:
                data['conditions'] = ConditionalConditions(**conditions_data).model_dump()
            elif suppression_type == SuppressionType.CASCADE:
                data['conditions'] = CascadeConditions(**conditions_data).model_dump()
        return data


class AlarmSuppressionUpdate(BaseModel):
    """更新告警抑制"""
    name: Optional[str] = Field(None, max_length=200, description="抑制规则名称")
    description: Optional[str] = Field(None, description="抑制规则描述")
    conditions: Optional[Union[
        ManualConditions,
        MaintenanceConditions,
        DependencyConditions,
        ScheduleConditions,
        ConditionalConditions,
        CascadeConditions
    ]] = Field(None, discriminator='suppression_type', description="抑制条件")
    start_time: Optional[datetime] = Field(None, description="抑制开始时间")
    end_time: Optional[datetime] = Field(None, description="抑制结束时间")
    is_recurring: Optional[bool] = Field(None, description="是否为周期性抑制")
    recurrence_pattern: Optional[Dict[str, Any]] = Field(None, description="周期模式配置")
    priority: Optional[int] = Field(None, ge=1, le=1000, description="抑制优先级")
    action_config: Optional[Union[
        ManualActionConfig,
        MaintenanceActionConfig,
        DependencyActionConfig,
        DefaultActionConfig
    ]] = Field(None, discriminator='suppression_type', description="抑制动作配置")
    status: Optional[SuppressionStatus] = Field(None, description="抑制状态")

    @model_validator(mode='before')
    @classmethod
    def validate_conditions_and_action_config(cls, data: Any) -> Any:
        if isinstance(data, dict):
            suppression_type = data.get('suppression_type')
            conditions_data = data.get('conditions')
            action_config_data = data.get('action_config')

            if suppression_type == SuppressionType.MANUAL and conditions_data:
                data['conditions'] = ManualConditions(**conditions_data).model_dump()
                if action_config_data:
                    data['action_config'] = ManualActionConfig(**action_config_data).model_dump()
            elif suppression_type == SuppressionType.MAINTENANCE and conditions_data:
                data['conditions'] = MaintenanceConditions(**conditions_data).model_dump()
                if action_config_data:
                    data['action_config'] = MaintenanceActionConfig(**action_config_data).model_dump()
            elif suppression_type == SuppressionType.DEPENDENCY and conditions_data:
                data['conditions'] = DependencyConditions(**conditions_data).model_dump()
                if action_config_data:
                    data['action_config'] = DependencyActionConfig(**action_config_data).model_dump()
            elif suppression_type == SuppressionType.SCHEDULE and conditions_data:
                data['conditions'] = ScheduleConditions(**conditions_data).model_dump()
            elif suppression_type == SuppressionType.CONDITIONAL and conditions_data:
                data['conditions'] = ConditionalConditions(**conditions_data).model_dump()
            elif suppression_type == SuppressionType.CASCADE and conditions_data:
                data['conditions'] = CascadeConditions(**conditions_data).model_dump()
        return data


class AlarmSuppressionResponse(BaseModel):
    """告警抑制响应"""
    id: int
    name: str
    description: Optional[str]
    suppression_type: str
    status: str
    conditions: Union[
        ManualConditions,
        MaintenanceConditions,
        DependencyConditions,
        ScheduleConditions,
        ConditionalConditions,
        CascadeConditions,
        Dict[str, Any] # Fallback for unknown or generic types
    ]
    start_time: datetime
    end_time: Optional[datetime]
    is_recurring: bool
    recurrence_pattern: Optional[Dict[str, Any]]
    priority: int
    action_config: Optional[Union[
        ManualActionConfig,
        MaintenanceActionConfig,
        DependencyActionConfig,
        DefaultActionConfig,
        Dict[str, Any] # Fallback
    ]]
    suppressed_count: int
    last_match: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            ManualConditions: lambda v: v.model_dump(),
            MaintenanceConditions: lambda v: v.model_dump(),
            DependencyConditions: lambda v: v.model_dump(),
            ScheduleConditions: lambda v: v.model_dump(),
            ConditionalConditions: lambda v: v.model_dump(),
            CascadeConditions: lambda v: v.model_dump(),
            ManualActionConfig: lambda v: v.model_dump(),
            MaintenanceActionConfig: lambda v: v.model_dump(),
            DependencyActionConfig: lambda v: v.model_dump(),
            DefaultActionConfig: lambda v: v.model_dump(),
        }

    @model_validator(mode='before')
    @classmethod
    def parse_conditions_and_action_config(cls, data: Any) -> Any:
        if isinstance(data, dict):
            suppression_type = data.get('suppression_type')
            conditions_data = data.get('conditions')
            action_config_data = data.get('action_config')

            if suppression_type == SuppressionType.MANUAL:
                if conditions_data:
                    data['conditions'] = ManualConditions(**conditions_data)
                if action_config_data:
                    data['action_config'] = ManualActionConfig(**action_config_data)
            elif suppression_type == SuppressionType.MAINTENANCE:
                if conditions_data:
                    data['conditions'] = MaintenanceConditions(**conditions_data)
                if action_config_data:
                    data['action_config'] = MaintenanceActionConfig(**action_config_data)
            elif suppression_type == SuppressionType.DEPENDENCY:
                if conditions_data:
                    data['conditions'] = DependencyConditions(**conditions_data)
                if action_config_data:
                    data['action_config'] = DependencyActionConfig(**action_config_data)
            elif suppression_type == SuppressionType.SCHEDULE:
                if conditions_data:
                    data['conditions'] = ScheduleConditions(**conditions_data)
            elif suppression_type == SuppressionType.CONDITIONAL:
                if conditions_data:
                    data['conditions'] = ConditionalConditions(**conditions_data)
            elif suppression_type == SuppressionType.CASCADE:
                if conditions_data:
                    data['conditions'] = CascadeConditions(**conditions_data)
        return data


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
        "conditions": ManualConditions(
            hosts=["example-host"],
            severity_filter=None,
            services=None,
            tags=None
        ).model_dump(),
        "action_config": ManualActionConfig(
            notify_suppressed=True,
            add_comment=True
        ).model_dump()
    },
    "manual_service": {
        "name": "服务手动抑制模板",
        "description": "手动抑制指定服务的告警",
        "conditions": ManualConditions(
            services=["example-service"],
            severity_filter=None,
            hosts=None,
            tags=None
        ).model_dump(),
        "action_config": ManualActionConfig(
            notify_suppressed=True,
            add_comment=True
        ).model_dump()
    },
    "maintenance_window": {
        "name": "维护窗口抑制模板",
        "description": "在维护窗口期间抑制相关告警",
        "conditions": MaintenanceConditions(
            maintenance_mode=True,
            affected_resources=[],
            severity_threshold="high"
        ).model_dump(),
        "action_config": MaintenanceActionConfig(
            notify_before_start=True,
            notify_after_end=True,
            aggregate_suppressed=True
        ).model_dump()
    },
    "dependency_cascade": {
        "name": "依赖级联抑制模板", 
        "description": "当父服务出现问题时抑制子服务告警",
        "conditions": DependencyConditions(
            parent_service_status="down",
            cascade_rules={},
            timeout_minutes=10
        ).model_dump(),
        "action_config": DependencyActionConfig(
            aggregate_child_alarms=True,
            max_child_alarms=50
        ).model_dump()
    },
    "schedule_suppression": {
        "name": "计划抑制模板",
        "description": "根据Cron表达式周期性抑制告警",
        "conditions": ScheduleConditions(
            cron_schedule="0 0 * * *", # Every day at midnight UTC
            duration_minutes=60,
            affected_resources=[]
        ).model_dump(),
        "action_config": DefaultActionConfig().model_dump()
    },
    "conditional_suppression": {
        "name": "条件抑制模板",
        "description": "根据自定义条件表达式抑制告警",
        "conditions": ConditionalConditions(
            expression="alarm.labels.environment == 'dev' and alarm.severity == 'info'"
        ).model_dump(),
        "action_config": DefaultActionConfig().model_dump()
    },
    "cascade_suppression": {
        "name": "级联抑制模板",
        "description": "根据根告警的指纹级联抑制相关告警",
        "conditions": CascadeConditions(
            root_alarm_fingerprint="",
            max_cascade_depth=5,
            time_window_minutes=30
        ).model_dump(),
        "action_config": DefaultActionConfig().model_dump()
    }
}