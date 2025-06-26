"""
告警降噪数据模型
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from src.core.database import Base


class NoiseRuleType(str, Enum):
    """降噪规则类型"""
    FREQUENCY_LIMIT = "frequency_limit"      # 频率限制
    THRESHOLD_FILTER = "threshold_filter"    # 阈值过滤
    SILENCE_WINDOW = "silence_window"        # 静默窗口
    DEPENDENCY_FILTER = "dependency_filter"  # 依赖过滤
    DUPLICATE_SUPPRESS = "duplicate_suppress" # 重复抑制
    TIME_BASED = "time_based"               # 基于时间
    CUSTOM_RULE = "custom_rule"             # 自定义规则


class NoiseRuleAction(str, Enum):
    """降噪动作"""
    SUPPRESS = "suppress"      # 抑制告警
    DELAY = "delay"           # 延迟发送
    AGGREGATE = "aggregate"    # 聚合告警
    DOWNGRADE = "downgrade"   # 降低优先级
    DISCARD = "discard"       # 丢弃告警
    FORWARD = "forward"       # 转发处理


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
    conditions: Dict[str, Any] = Field(..., description="匹配条件")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="规则参数")
    priority: int = Field(default=100, ge=1, le=1000, description="规则优先级")
    effective_start: Optional[datetime] = Field(None, description="生效开始时间")
    effective_end: Optional[datetime] = Field(None, description="生效结束时间")


class NoiseReductionRuleUpdate(BaseModel):
    """更新降噪规则"""
    name: Optional[str] = Field(None, max_length=200, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    rule_type: Optional[NoiseRuleType] = Field(None, description="规则类型")
    action: Optional[NoiseRuleAction] = Field(None, description="执行动作")
    conditions: Optional[Dict[str, Any]] = Field(None, description="匹配条件")
    parameters: Optional[Dict[str, Any]] = Field(None, description="规则参数")
    priority: Optional[int] = Field(None, ge=1, le=1000, description="规则优先级")
    enabled: Optional[bool] = Field(None, description="是否启用")
    effective_start: Optional[datetime] = Field(None, description="生效开始时间")
    effective_end: Optional[datetime] = Field(None, description="生效结束时间")


class NoiseReductionRuleResponse(BaseModel):
    """降噪规则响应"""
    id: int
    name: str
    description: Optional[str]
    rule_type: str
    action: str
    conditions: Dict[str, Any]
    parameters: Optional[Dict[str, Any]]
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


# 规则配置模板和示例

RULE_TEMPLATES = {
    "frequency_limit": {
        "name": "频率限制模板",
        "description": "限制相同告警在指定时间窗口内的发送频率",
        "conditions": {
            "time_window_minutes": 10,
            "max_count": 3,
            "group_by": ["host", "service", "severity"]
        },
        "parameters": {
            "action_after_limit": "suppress",
            "reset_window": True
        }
    },
    "threshold_filter": {
        "name": "阈值过滤模板", 
        "description": "基于告警频次过滤低频告警",
        "conditions": {
            "time_window_hours": 1,
            "min_occurrences": 5,
            "severity": ["low", "info"]
        },
        "parameters": {
            "discard_below_threshold": True
        }
    },
    "silence_window": {
        "name": "静默窗口模板",
        "description": "在维护时间窗口内抑制告警",
        "conditions": {
            "time_ranges": [
                {"start": "02:00", "end": "06:00", "timezone": "UTC"},
                {"start": "14:00", "end": "16:00", "timezone": "UTC"}
            ],
            "affected_systems": []
        },
        "parameters": {
            "maintenance_mode": True,
            "notify_before_window": 15
        }
    },
    "dependency_filter": {
        "name": "依赖过滤模板",
        "description": "基于服务依赖关系过滤衍生告警",
        "conditions": {
            "parent_service_down": True,
            "dependency_map": {},
            "cascade_timeout_minutes": 5
        },
        "parameters": {
            "aggregate_child_alarms": True,
            "max_child_alarms": 10
        }
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