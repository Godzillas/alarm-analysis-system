"""
告警降噪数据模型
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, model_validator
from typing import Union

from src.core.database import Base


# --- Enums ---
class NoiseRuleAction(str, Enum):
    """降噪动作"""
    SUPPRESS = "suppress"      # 抑制告警
    DELAY = "delay"           # 延迟发送
    AGGREGATE = "aggregate"    # 聚合告警
    DOWNGRADE = "downgrade"   # 降低优先级
    DISCARD = "discard"       # 丢弃告警
    FORWARD = "forward"       # 转发处理


# --- New Pydantic Models for Conditions and Parameters ---

# Base models for conditions and parameters
class BaseRuleConditions(BaseModel):
    """Base class for noise reduction rule conditions."""
    pass

class BaseRuleParameters(BaseModel):
    """Base class for noise reduction rule parameters."""
    pass

# Specific Conditions Models
class FrequencyLimitConditions(BaseRuleConditions):
    rule_type: Literal["frequency_limit"] = Field(default="frequency_limit", description="规则类型")
    time_window_minutes: int = Field(..., description="时间窗口（分钟）")
    max_count: int = Field(..., description="最大告警数量")
    group_by: List[str] = Field(..., description="分组字段列表")

class ThresholdFilterConditions(BaseRuleConditions):
    rule_type: Literal["threshold_filter"] = Field(default="threshold_filter", description="规则类型")
    time_window_hours: int = Field(..., description="时间窗口（小时）")
    min_occurrences: int = Field(..., description="最小出现次数")
    severity: Optional[List[str]] = Field(None, description="告警严重程度过滤")

class SilenceWindowTimeRange(BaseModel):
    start: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="开始时间 (HH:MM)")
    end: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="结束时间 (HH:MM)")
    timezone: Optional[str] = Field("UTC", description="时区")

class SilenceWindowConditions(BaseRuleConditions):
    rule_type: Literal["silence_window"] = Field(default="silence_window", description="规则类型")
    time_ranges: List[SilenceWindowTimeRange] = Field(..., description="静默时间范围")
    affected_systems: Optional[List[str]] = Field(None, description="受影响的系统列表")

class DependencyFilterConditions(BaseRuleConditions):
    rule_type: Literal["dependency_filter"] = Field(default="dependency_filter", description="规则类型")
    parent_service_down: bool = Field(True, description="父服务是否宕机")
    dependency_map: Dict[str, List[str]] = Field(..., description="服务依赖映射")
    cascade_timeout_minutes: int = Field(5, description="级联超时时间（分钟）")

class DuplicateSuppressConditions(BaseRuleConditions):
    rule_type: Literal["duplicate_suppress"] = Field(default="duplicate_suppress", description="规则类型")
    similarity_threshold: float = Field(0.9, ge=0.0, le=1.0, description="相似度阈值")
    time_window_minutes: int = Field(30, ge=1, description="时间窗口（分钟）")

class TimeBasedConditions(BaseRuleConditions):
    rule_type: Literal["time_based"] = Field(default="time_based", description="规则类型")
    allowed_hours: Optional[List[int]] = Field(None, description="允许的小时 (0-23)")
    blocked_weekdays: Optional[List[int]] = Field(None, description="禁止的星期几 (0=周一, 6=周日)")

class CustomRuleConditions(BaseRuleConditions):
    rule_type: Literal["custom_rule"] = Field(default="custom_rule", description="规则类型")
    expression: Optional[str] = Field(None, description="自定义表达式")
    condition_groups: Optional[List["RuleConditionGroup"]] = Field(None, description="条件组")

    @model_validator(mode='after')
    def check_expression_or_groups(self):
        if not self.expression and not self.condition_groups:
            raise ValueError("Either 'expression' or 'condition_groups' must be provided for custom rules.")
        return self

# Specific Parameters Models
class FrequencyLimitParameters(BaseRuleParameters):
    rule_type: Literal["frequency_limit"] = Field(default="frequency_limit", description="规则类型")
    action_after_limit: NoiseRuleAction = Field(NoiseRuleAction.SUPPRESS, description="达到限制后的动作")
    reset_window: bool = Field(True, description="是否重置窗口")

class ThresholdFilterParameters(BaseRuleParameters):
    rule_type: Literal["threshold_filter"] = Field(default="threshold_filter", description="规则类型")
    discard_below_threshold: bool = Field(True, description="是否丢弃低于阈值的告警")

class SilenceWindowParameters(BaseRuleParameters):
    rule_type: Literal["silence_window"] = Field(default="silence_window", description="规则类型")
    maintenance_mode: bool = Field(True, description="是否为维护模式")
    notify_before_window: Optional[int] = Field(None, description="提前通知时间（分钟）")

class DependencyFilterParameters(BaseRuleParameters):
    rule_type: Literal["dependency_filter"] = Field(default="dependency_filter", description="规则类型")
    aggregate_child_alarms: bool = Field(True, description="是否聚合子告警")
    max_child_alarms: int = Field(10, description="最大子告警数量")

class DefaultRuleParameters(BaseRuleParameters):
    """Default parameters for rules without specific parameters."""
    rule_type: Literal["default"] = Field(default="default", description="规则类型")

class DelayParameters(BaseRuleParameters):
    rule_type: Literal["delay"] = Field(default="delay", description="规则类型")
    delay_minutes: int = Field(5, description="延迟时间（分钟）")

class DowngradeParameters(BaseRuleParameters):
    rule_type: Literal["downgrade"] = Field(default="downgrade", description="规则类型")
    new_severity: str = Field("low", description="新的告警严重程度")

class AggregateParameters(BaseRuleParameters):
    rule_type: Literal["aggregate"] = Field(default="aggregate", description="规则类型")
    group_key: str = Field("default", description="聚合分组键")
    aggregate_window_minutes: int = Field(10, description="聚合时间窗口（分钟）")

# --- Updated Pydantic Models for Create/Update/Response ---


class NoiseRuleType(str, Enum):
    """降噪规则类型"""
    FREQUENCY_LIMIT = "frequency_limit"      # 频率限制
    THRESHOLD_FILTER = "threshold_filter"    # 阈值过滤
    SILENCE_WINDOW = "silence_window"        # 静默窗口
    DEPENDENCY_FILTER = "dependency_filter"  # 依赖过滤
    DUPLICATE_SUPPRESS = "duplicate_suppress" # 重复抑制
    TIME_BASED = "time_based"               # 基于时间
    CUSTOM_RULE = "custom_rule"             # 自定义规则


class NoiseReductionRule(Base):
    """降噪规则表"""
    __tablename__ = 'noise_reduction_rules'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="规则名称")
    description = Column(Text, comment="规则描述")
    
    # 规则类型和动作
    rule_type = Column(String(50), nullable=False, comment="规则类型")
    action = Column(String(50), nullable=False, comment="执行动作")
    
    # 规则条件配置 (JSON格式)
    conditions = Column(JSON, nullable=False, comment="匹配条件")
    
    # 规则参数配置 (JSON格式)
    parameters = Column(JSON, comment="规则参数")
    
    # 优先级 (数字越小优先级越高)
    priority = Column(Integer, default=100, comment="规则优先级")
    
    # 启用状态
    enabled = Column(Boolean, default=True, comment="是否启用")
    
    # 时间设置
    effective_start = Column(DateTime, comment="生效开始时间")
    effective_end = Column(DateTime, comment="生效结束时间")
    
    # 统计信息
    hit_count = Column(Integer, default=0, comment="命中次数")
    last_hit = Column(DateTime, comment="最后命中时间")
    
    # 审计信息
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    created_by = Column(Integer, ForeignKey('users.id'), comment="创建者")
    
    # 关联关系
    creator = relationship("User", foreign_keys=[created_by])
    execution_logs = relationship("NoiseRuleExecutionLog", back_populates="rule")


class NoiseRuleExecutionLog(Base):
    """降噪规则执行日志"""
    __tablename__ = 'noise_rule_execution_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey('noise_reduction_rules.id'), nullable=False, comment="规则ID")
    alarm_id = Column(Integer, ForeignKey('alarms.id'), nullable=False, comment="告警ID")
    
    # 执行结果
    matched = Column(Boolean, nullable=False, comment="是否匹配")
    action_taken = Column(String(50), comment="执行的动作")
    result = Column(String(20), comment="执行结果")
    
    # 执行详情
    match_details = Column(JSON, comment="匹配详情")
    execution_time_ms = Column(Float, comment="执行耗时(毫秒)")
    
    # 错误信息
    error_message = Column(Text, comment="错误信息")
    
    # 时间信息
    executed_at = Column(DateTime, default=datetime.utcnow, comment="执行时间")
    
    # 关联关系
    rule = relationship("NoiseReductionRule", back_populates="execution_logs")
    alarm = relationship("AlarmTable")


class NoiseReductionStats(Base):
    """降噪统计表"""
    __tablename__ = 'noise_reduction_stats'
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, comment="统计日期")
    
    # 统计数据
    total_alarms = Column(Integer, default=0, comment="总告警数")
    suppressed_alarms = Column(Integer, default=0, comment="被抑制的告警数")
    delayed_alarms = Column(Integer, default=0, comment="被延迟的告警数")
    aggregated_alarms = Column(Integer, default=0, comment="被聚合的告警数")
    downgraded_alarms = Column(Integer, default=0, comment="被降级的告警数")
    discarded_alarms = Column(Integer, default=0, comment="被丢弃的告警数")
    
    # 效果统计
    noise_reduction_rate = Column(Float, comment="降噪率")
    processing_time_ms = Column(Float, comment="平均处理时间(毫秒)")
    
    # 规则统计
    active_rules = Column(Integer, default=0, comment="活跃规则数")
    rule_hit_rate = Column(Float, comment="规则命中率")
    
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")


# Pydantic 模型

class NoiseReductionRuleCreate(BaseModel):
    """创建降噪规则"""
    name: str = Field(..., max_length=200, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    rule_type: NoiseRuleType = Field(..., description="规则类型")
    action: NoiseRuleAction = Field(..., description="执行动作")
    conditions: Union[
        FrequencyLimitConditions,
        ThresholdFilterConditions,
        SilenceWindowConditions,
        DependencyFilterConditions,
        DuplicateSuppressConditions,
        TimeBasedConditions,
        CustomRuleConditions
    ] = Field(..., discriminator='rule_type', description="匹配条件")
    parameters: Optional[Union[
        FrequencyLimitParameters,
        ThresholdFilterParameters,
        SilenceWindowParameters,
        DependencyFilterParameters,
        DelayParameters,
        DowngradeParameters,
        AggregateParameters,
        DefaultRuleParameters # For rules without specific parameters
    ]] = Field(None, discriminator='rule_type', description="规则参数")
    priority: int = Field(default=100, ge=1, le=1000, description="规则优先级")
    effective_start: Optional[datetime] = Field(None, description="生效开始时间")
    effective_end: Optional[datetime] = Field(None, description="生效结束时间")

    @model_validator(mode='before')
    @classmethod
    def validate_conditions_and_parameters(cls, data: Any) -> Any:
        if isinstance(data, dict):
            rule_type = data.get('rule_type')
            conditions_data = data.get('conditions')
            parameters_data = data.get('parameters')

            if rule_type == NoiseRuleType.FREQUENCY_LIMIT:
                data['conditions'] = FrequencyLimitConditions(**conditions_data).model_dump()
                if parameters_data:
                    data['parameters'] = FrequencyLimitParameters(**parameters_data).model_dump()
            elif rule_type == NoiseRuleType.THRESHOLD_FILTER:
                data['conditions'] = ThresholdFilterConditions(**conditions_data).model_dump()
                if parameters_data:
                    data['parameters'] = ThresholdFilterParameters(**parameters_data).model_dump()
            elif rule_type == NoiseRuleType.SILENCE_WINDOW:
                data['conditions'] = SilenceWindowConditions(**conditions_data).model_dump()
                if parameters_data:
                    data['parameters'] = SilenceWindowParameters(**parameters_data).model_dump()
            elif rule_type == NoiseRuleType.DEPENDENCY_FILTER:
                data['conditions'] = DependencyFilterConditions(**conditions_data).model_dump()
                if parameters_data:
                    data['parameters'] = DependencyFilterParameters(**parameters_data).model_dump()
            elif rule_type == NoiseRuleType.DUPLICATE_SUPPRESS:
                data['conditions'] = DuplicateSuppressConditions(**conditions_data).model_dump()
            elif rule_type == NoiseRuleType.TIME_BASED:
                data['conditions'] = TimeBasedConditions(**conditions_data).model_dump()
            elif rule_type == NoiseRuleType.CUSTOM_RULE:
                data['conditions'] = CustomRuleConditions(**conditions_data).model_dump()
            # For other rule types, conditions/parameters remain as Dict[str, Any] or None
        return data


class NoiseReductionRuleUpdate(BaseModel):
    """更新降噪规则"""
    name: Optional[str] = Field(None, max_length=200, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    rule_type: Optional[NoiseRuleType] = Field(None, description="规则类型")
    action: Optional[NoiseRuleAction] = Field(None, description="执行动作")
    conditions: Optional[Union[
        FrequencyLimitConditions,
        ThresholdFilterConditions,
        SilenceWindowConditions,
        DependencyFilterConditions,
        DuplicateSuppressConditions,
        TimeBasedConditions,
        CustomRuleConditions
    ]] = Field(None, discriminator='rule_type', description="匹配条件")
    parameters: Optional[Union[
        FrequencyLimitParameters,
        ThresholdFilterParameters,
        SilenceWindowParameters,
        DependencyFilterParameters,
        DelayParameters,
        DowngradeParameters,
        AggregateParameters,
        DefaultRuleParameters
    ]] = Field(None, discriminator='rule_type', description="规则参数")
    priority: Optional[int] = Field(None, ge=1, le=1000, description="规则优先级")
    enabled: Optional[bool] = Field(None, description="是否启用")
    effective_start: Optional[datetime] = Field(None, description="生效开始时间")
    effective_end: Optional[datetime] = Field(None, description="生效结束时间")

    @model_validator(mode='before')
    @classmethod
    def validate_conditions_and_parameters(cls, data: Any) -> Any:
        if isinstance(data, dict):
            rule_type = data.get('rule_type')
            conditions_data = data.get('conditions')
            parameters_data = data.get('parameters')

            if rule_type == NoiseRuleType.FREQUENCY_LIMIT and conditions_data:
                data['conditions'] = FrequencyLimitConditions(**conditions_data).model_dump()
                if parameters_data:
                    data['parameters'] = FrequencyLimitParameters(**parameters_data).model_dump()
            elif rule_type == NoiseRuleType.THRESHOLD_FILTER and conditions_data:
                data['conditions'] = ThresholdFilterConditions(**conditions_data).model_dump()
                if parameters_data:
                    data['parameters'] = ThresholdFilterParameters(**parameters_data).model_dump()
            elif rule_type == NoiseRuleType.SILENCE_WINDOW and conditions_data:
                data['conditions'] = SilenceWindowConditions(**conditions_data).model_dump()
                if parameters_data:
                    data['parameters'] = SilenceWindowParameters(**parameters_data).model_dump()
            elif rule_type == NoiseRuleType.DEPENDENCY_FILTER and conditions_data:
                data['conditions'] = DependencyFilterConditions(**conditions_data).model_dump()
                if parameters_data:
                    data['parameters'] = DependencyFilterParameters(**parameters_data).model_dump()
            elif rule_type == NoiseRuleType.DUPLICATE_SUPPRESS and conditions_data:
                data['conditions'] = DuplicateSuppressConditions(**conditions_data).model_dump()
            elif rule_type == NoiseRuleType.TIME_BASED and conditions_data:
                data['conditions'] = TimeBasedConditions(**conditions_data).model_dump()
            elif rule_type == NoiseRuleType.CUSTOM_RULE and conditions_data:
                data['conditions'] = CustomRuleConditions(**conditions_data).model_dump()
        return data


class NoiseReductionRuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    rule_type: str
    action: str
    conditions: Union[
        FrequencyLimitConditions,
        ThresholdFilterConditions,
        SilenceWindowConditions,
        DependencyFilterConditions,
        DuplicateSuppressConditions,
        TimeBasedConditions,
        CustomRuleConditions,
        Dict[str, Any] # Fallback for unknown or generic types
    ]
    parameters: Optional[Union[
        FrequencyLimitParameters,
        ThresholdFilterParameters,
        SilenceWindowParameters,
        DependencyFilterParameters,
        DefaultRuleParameters,
        Dict[str, Any] # Fallback
    ]]
    priority: int
    enabled: bool
    effective_start: Optional[datetime]
    effective_end: Optional[datetime]
    hit_count: int
    last_hit: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        # This is crucial for Pydantic to correctly parse the `conditions` and `parameters`
        # from the SQLAlchemy model's JSON fields into the specific Pydantic models.
        # It tells Pydantic to use the `rule_type` field to determine which
        # `conditions` and `parameters` model to use.
        json_encoders = {
            FrequencyLimitConditions: lambda v: v.model_dump(),
            ThresholdFilterConditions: lambda v: v.model_dump(),
            SilenceWindowConditions: lambda v: v.model_dump(),
            DependencyFilterConditions: lambda v: v.model_dump(),
            DuplicateSuppressConditions: lambda v: v.model_dump(),
            TimeBasedConditions: lambda v: v.model_dump(),
            CustomRuleConditions: lambda v: v.model_dump(),
            FrequencyLimitParameters: lambda v: v.model_dump(),
            ThresholdFilterParameters: lambda v: v.model_dump(),
            SilenceWindowParameters: lambda v: v.model_dump(),
            DependencyFilterParameters: lambda v: v.model_dump(),
            DelayParameters: lambda v: v.model_dump(),
            DowngradeParameters: lambda v: v.model_dump(),
            AggregateParameters: lambda v: v.model_dump(),
            DefaultRuleParameters: lambda v: v.model_dump(),
        }

    @model_validator(mode='before')
    @classmethod
    def parse_conditions_and_parameters(cls, data: Any) -> Any:
        if isinstance(data, dict):
            rule_type = data.get('rule_type')
            conditions_data = data.get('conditions')
            parameters_data = data.get('parameters')

            if rule_type == NoiseRuleType.FREQUENCY_LIMIT:
                if conditions_data:
                    data['conditions'] = FrequencyLimitConditions(**conditions_data)
                if parameters_data:
                    data['parameters'] = FrequencyLimitParameters(**parameters_data)
            elif rule_type == NoiseRuleType.THRESHOLD_FILTER:
                if conditions_data:
                    data['conditions'] = ThresholdFilterConditions(**conditions_data)
                if parameters_data:
                    data['parameters'] = ThresholdFilterParameters(**parameters_data)
            elif rule_type == NoiseRuleType.SILENCE_WINDOW:
                if conditions_data:
                    data['conditions'] = SilenceWindowConditions(**conditions_data)
                if parameters_data:
                    data['parameters'] = SilenceWindowParameters(**parameters_data)
            elif rule_type == NoiseRuleType.DEPENDENCY_FILTER:
                if conditions_data:
                    data['conditions'] = DependencyFilterConditions(**conditions_data)
                if parameters_data:
                    data['parameters'] = DependencyFilterParameters(**parameters_data)
            elif rule_type == NoiseRuleType.DUPLICATE_SUPPRESS:
                if conditions_data:
                    data['conditions'] = DuplicateSuppressConditions(**conditions_data)
            elif rule_type == NoiseRuleType.TIME_BASED:
                if conditions_data:
                    data['conditions'] = TimeBasedConditions(**conditions_data)
            elif rule_type == NoiseRuleType.CUSTOM_RULE:
                if conditions_data:
                    data['conditions'] = CustomRuleConditions(**conditions_data)
        return data


class NoiseRuleTestRequest(BaseModel):
    """规则测试请求"""
    rule_config: NoiseReductionRuleCreate = Field(..., description="规则配置")
    test_alarms: List[Dict[str, Any]] = Field(..., description="测试告警数据")


class NoiseRuleTestResult(BaseModel):
    """规则测试结果"""
    total_alarms: int = Field(..., description="测试告警总数")
    matched_alarms: int = Field(..., description="匹配的告警数")
    match_rate: float = Field(..., description="匹配率")
    execution_time_ms: float = Field(..., description="执行耗时")
    results: List[Dict[str, Any]] = Field(..., description="详细结果")


class NoiseReductionStatsResponse(BaseModel):
    """降噪统计响应"""
    date: datetime
    total_alarms: int
    suppressed_alarms: int
    delayed_alarms: int
    aggregated_alarms: int
    downgraded_alarms: int
    discarded_alarms: int
    noise_reduction_rate: float
    processing_time_ms: float
    active_rules: int
    rule_hit_rate: float
    
    class Config:
        from_attributes = True


# 规则配置模板和示例将在文件末尾定义

def _create_rule_templates():
    return {
    "frequency_limit": {
        "name": "频率限制模板",
        "description": "限制相同告警在指定时间窗口内的发送频率",
        "conditions": FrequencyLimitConditions(
            time_window_minutes=10,
            max_count=3,
            group_by=["host", "service", "severity"]
        ).model_dump(),
        "parameters": FrequencyLimitParameters(
            action_after_limit=NoiseRuleAction.SUPPRESS,
            reset_window=True
        ).model_dump()
    },
    "threshold_filter": {
        "name": "阈值过滤模板",
        "description": "基于告警频次过滤低频告警",
        "conditions": ThresholdFilterConditions(
            time_window_hours=1,
            min_occurrences=5,
            severity=["low", "info"]
        ).model_dump(),
        "parameters": ThresholdFilterParameters(
            discard_below_threshold=True
        ).model_dump()
    },
    "silence_window": {
        "name": "静默窗口模板",
        "description": "在维护时间窗口内抑制告警",
        "conditions": SilenceWindowConditions(
            time_ranges=[
                SilenceWindowTimeRange(start="02:00", end="06:00", timezone="UTC"),
                SilenceWindowTimeRange(start="14:00", end="16:00", timezone="UTC")
            ],
            affected_systems=[]
        ).model_dump(),
        "parameters": SilenceWindowParameters(
            maintenance_mode=True,
            notify_before_window=15
        ).model_dump()
    },
    "dependency_filter": {
        "name": "依赖过滤模板",
        "description": "基于服务依赖关系过滤衍生告警",
        "conditions": DependencyFilterConditions(
            parent_service_down=True,
            dependency_map={},
            cascade_timeout_minutes=5
        ).model_dump(),
        "parameters": DependencyFilterParameters(
            aggregate_child_alarms=True,
            max_child_alarms=10
        ).model_dump()
    },
    "duplicate_suppress": {
        "name": "重复抑制模板",
        "description": "抑制在指定时间窗口内重复出现的告警",
        "conditions": DuplicateSuppressConditions(
            similarity_threshold=0.9,
            time_window_minutes=30
        ).model_dump(),
        "parameters": DefaultRuleParameters().model_dump() # No specific parameters
    },
    "time_based": {
        "name": "基于时间抑制模板",
        "description": "在特定时间段或星期几抑制告警",
        "conditions": TimeBasedConditions(
            allowed_hours=[9, 10, 11, 12, 13, 14, 15, 16, 17],
            blocked_weekdays=[5, 6] # Saturday, Sunday
        ).model_dump(),
        "parameters": DefaultRuleParameters().model_dump() # No specific parameters
    },
    "custom_rule": {
        "name": "自定义规则模板",
        "description": "使用自定义表达式或条件组定义规则",
        "conditions": CustomRuleConditions(
            expression="alarm.severity == 'critical' and alarm.host == 'server1'"
        ).model_dump(),
        "parameters": DefaultRuleParameters().model_dump() # No specific parameters
    }
    }


class RuleCondition(BaseModel):
    """规则条件"""
    field: str = Field(..., description="字段名")
    operator: str = Field(..., description="操作符: eq, ne, in, not_in, contains, regex, gt, lt, gte, lte")
    value: Any = Field(..., description="比较值")
    case_sensitive: bool = Field(default=True, description="是否大小写敏感")


class RuleConditionGroup(BaseModel):
    """规则条件组"""
    logic: str = Field(default="AND", description="逻辑操作: AND, OR")
    conditions: List[RuleCondition] = Field(..., description="条件列表")
    groups: Optional[List["RuleConditionGroup"]] = Field(default=None, description="嵌套条件组")


# 用于递归引用
RuleConditionGroup.model_rebuild()
CustomRuleConditions.model_rebuild()

# 在所有模型定义完成后创建模板
RULE_TEMPLATES = _create_rule_templates()