"""
告警处理流程模型
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from src.models.alarm import Base


class AlarmProcessingStatus(str, Enum):
    """告警处理状态"""
    PENDING = "pending"           # 待处理
    ACKNOWLEDGED = "acknowledged" # 已确认
    INVESTIGATING = "investigating" # 调查中
    IN_PROGRESS = "in_progress"   # 处理中
    WAITING = "waiting"           # 等待中（等待外部响应）
    RESOLVED = "resolved"         # 已解决
    CLOSED = "closed"             # 已关闭
    ESCALATED = "escalated"       # 已升级


class AlarmPriority(str, Enum):
    """告警优先级"""
    P1 = "p1"  # 紧急 - 1小时内响应
    P2 = "p2"  # 高 - 4小时内响应
    P3 = "p3"  # 中等 - 24小时内响应
    P4 = "p4"  # 低 - 72小时内响应


class ProcessingActionType(str, Enum):
    """处理动作类型"""
    ACKNOWLEDGE = "acknowledge"      # 确认
    ASSIGN = "assign"               # 分配
    ESCALATE = "escalate"           # 升级
    RESOLVE = "resolve"             # 解决
    CLOSE = "close"                 # 关闭
    COMMENT = "comment"             # 评论
    UPDATE_STATUS = "update_status"  # 更新状态
    MERGE = "merge"                 # 合并告警
    SPLIT = "split"                 # 拆分告警


class ResolutionMethod(str, Enum):
    """解决方法类型"""
    FIXED = "fixed"                 # 已修复
    WORKAROUND = "workaround"       # 临时解决方案
    DUPLICATE = "duplicate"         # 重复告警
    FALSE_POSITIVE = "false_positive" # 误报
    NOT_REPRODUCIBLE = "not_reproducible" # 无法重现
    WONT_FIX = "wont_fix"          # 不予修复
    CONFIGURATION = "configuration" # 配置问题
    EXTERNAL = "external"           # 外部问题


class AlarmProcessing(Base):
    """告警处理主表"""
    __tablename__ = "alarm_processing"
    
    id = Column(Integer, primary_key=True, index=True)
    alarm_id = Column(Integer, ForeignKey('alarms.id'), nullable=False, index=True)
    
    # 处理状态
    status = Column(String(20), default=AlarmProcessingStatus.PENDING, index=True)
    priority = Column(String(10), default=AlarmPriority.P3, index=True)
    
    # 处理人员
    assigned_to = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    assigned_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    
    # 确认信息
    acknowledged_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledgment_note = Column(Text, nullable=True)
    
    # 解决信息
    resolved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_method = Column(String(20), nullable=True)
    resolution_note = Column(Text, nullable=True)
    resolution_time_minutes = Column(Integer, nullable=True)  # 解决耗时（分钟）
    
    # 关闭信息
    closed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    closed_at = Column(DateTime, nullable=True)
    close_note = Column(Text, nullable=True)
    
    # 升级信息
    escalated_to = Column(Integer, ForeignKey('users.id'), nullable=True)
    escalated_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    escalated_at = Column(DateTime, nullable=True)
    escalation_reason = Column(Text, nullable=True)
    escalation_level = Column(Integer, default=0)  # 升级层级
    
    # SLA信息
    sla_deadline = Column(DateTime, nullable=True)  # SLA截止时间
    sla_breached = Column(Boolean, default=False)   # 是否违反SLA
    response_time_minutes = Column(Integer, nullable=True)  # 响应时间（分钟）
    
    # 工作量估计
    estimated_effort_hours = Column(Integer, nullable=True)  # 预计工作量（小时）
    actual_effort_hours = Column(Integer, nullable=True)     # 实际工作量（小时）
    
    # 影响评估
    impact_level = Column(String(10), nullable=True)  # 影响级别：low, medium, high, critical
    affected_users = Column(Integer, nullable=True)   # 受影响用户数
    business_impact = Column(Text, nullable=True)     # 业务影响描述
    
    # 处理元数据
    processing_metadata = Column(JSON, nullable=True)  # 处理相关元数据
    tags = Column(JSON, nullable=True)                 # 处理标签
    
    # 关联告警（用于合并/拆分场景）
    parent_processing_id = Column(Integer, ForeignKey('alarm_processing.id'), nullable=True)
    related_alarm_ids = Column(JSON, nullable=True)    # 相关告警ID列表
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    alarm = relationship("AlarmTable", foreign_keys=[alarm_id])
    assigned_user = relationship("User", foreign_keys=[assigned_to])
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])
    acknowledged_by_user = relationship("User", foreign_keys=[acknowledged_by])
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])
    closed_by_user = relationship("User", foreign_keys=[closed_by])
    escalated_to_user = relationship("User", foreign_keys=[escalated_to])
    escalated_by_user = relationship("User", foreign_keys=[escalated_by])
    
    # 处理历史
    processing_history = relationship("AlarmProcessingHistory", back_populates="processing")
    # 处理评论
    comments = relationship("AlarmProcessingComment", back_populates="processing")


class AlarmProcessingHistory(Base):
    """告警处理历史记录"""
    __tablename__ = "alarm_processing_history"
    
    id = Column(Integer, primary_key=True, index=True)
    processing_id = Column(Integer, ForeignKey('alarm_processing.id'), nullable=False, index=True)
    
    # 动作信息
    action_type = Column(String(20), nullable=False, index=True)
    action_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    action_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 状态变化
    old_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=True)
    old_assigned_to = Column(Integer, nullable=True)
    new_assigned_to = Column(Integer, nullable=True)
    
    # 动作详情
    action_details = Column(JSON, nullable=True)  # 动作具体内容
    notes = Column(Text, nullable=True)           # 操作说明
    
    # 系统信息
    ip_address = Column(String(45), nullable=True)  # 操作IP
    user_agent = Column(String(500), nullable=True) # 用户代理
    
    # 关联关系
    processing = relationship("AlarmProcessing", back_populates="processing_history")
    action_by_user = relationship("User", foreign_keys=[action_by])


class AlarmProcessingComment(Base):
    """告警处理评论"""
    __tablename__ = "alarm_processing_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    processing_id = Column(Integer, ForeignKey('alarm_processing.id'), nullable=False, index=True)
    
    # 评论内容
    content = Column(Text, nullable=False)
    comment_type = Column(String(20), default="general")  # 评论类型：general, solution, question
    
    # 评论人信息
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    author_name = Column(String(100), nullable=False)  # 冗余存储，防止用户删除
    
    # 可见性
    visibility = Column(String(20), default="public")  # public, internal, private
    
    # 附件信息
    attachments = Column(JSON, nullable=True)  # 附件列表
    
    # 元数据
    comment_metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    processing = relationship("AlarmProcessing", back_populates="comments")
    author = relationship("User", foreign_keys=[author_id])


class AlarmSLA(Base):
    """告警SLA配置"""
    __tablename__ = "alarm_sla"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # SLA规则
    severity_mapping = Column(JSON, nullable=False)      # 严重程度到优先级的映射
    priority_sla = Column(JSON, nullable=False)          # 优先级对应的SLA时间
    business_hours_only = Column(Boolean, default=False) # 是否仅工作时间计算
    
    # 应用条件
    conditions = Column(JSON, nullable=True)  # 应用此SLA的条件
    
    # 升级规则
    escalation_rules = Column(JSON, nullable=True)  # 自动升级规则
    
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # 规则优先级
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProcessingSolution(Base):
    """处理解决方案库"""
    __tablename__ = "processing_solutions"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # 分类
    category = Column(String(50), nullable=False, index=True)
    tags = Column(JSON, nullable=True)
    
    # 解决方案内容
    solution_steps = Column(JSON, nullable=False)      # 解决步骤
    required_tools = Column(JSON, nullable=True)       # 需要的工具
    required_permissions = Column(JSON, nullable=True) # 需要的权限
    estimated_time_minutes = Column(Integer, nullable=True) # 预计耗时
    
    # 应用条件
    applicable_conditions = Column(JSON, nullable=True)  # 适用条件
    severity_filter = Column(JSON, nullable=True)        # 严重程度过滤
    source_filter = Column(JSON, nullable=True)          # 来源过滤
    
    # 统计信息
    usage_count = Column(Integer, default=0)
    success_rate = Column(Integer, default=0)  # 成功率（0-100）
    avg_resolution_time = Column(Integer, nullable=True)  # 平均解决时间
    
    # 版本信息
    version = Column(String(20), default="1.0")
    is_approved = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # 创建者信息
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])


# Pydantic模型用于API
class AlarmProcessingCreate(BaseModel):
    """创建告警处理记录"""
    alarm_id: int = Field(..., description="告警ID")
    priority: AlarmPriority = Field(AlarmPriority.P3, description="优先级")
    assigned_to: Optional[int] = Field(None, description="分配给用户ID")
    estimated_effort_hours: Optional[int] = Field(None, description="预计工作量（小时）")
    impact_level: Optional[str] = Field(None, description="影响级别")
    business_impact: Optional[str] = Field(None, description="业务影响描述")
    tags: Optional[List[str]] = Field(None, description="标签")


class AlarmProcessingUpdate(BaseModel):
    """更新告警处理记录"""
    status: Optional[AlarmProcessingStatus] = None
    priority: Optional[AlarmPriority] = None
    assigned_to: Optional[int] = None
    acknowledgment_note: Optional[str] = None
    resolution_method: Optional[ResolutionMethod] = None
    resolution_note: Optional[str] = None
    close_note: Optional[str] = None
    escalation_reason: Optional[str] = None
    estimated_effort_hours: Optional[int] = None
    actual_effort_hours: Optional[int] = None
    impact_level: Optional[str] = None
    business_impact: Optional[str] = None
    tags: Optional[List[str]] = None


class AlarmProcessingAction(BaseModel):
    """告警处理动作"""
    action_type: ProcessingActionType = Field(..., description="动作类型")
    notes: Optional[str] = Field(None, description="操作说明")
    assigned_to: Optional[int] = Field(None, description="分配给用户ID（用于分配动作）")
    resolution_method: Optional[ResolutionMethod] = Field(None, description="解决方法")
    escalation_reason: Optional[str] = Field(None, description="升级原因")
    escalated_to: Optional[int] = Field(None, description="升级给用户ID")


class CommentCreate(BaseModel):
    """创建评论"""
    content: str = Field(..., description="评论内容")
    comment_type: str = Field("general", description="评论类型")
    visibility: str = Field("public", description="可见性")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件")


class SolutionCreate(BaseModel):
    """创建解决方案"""
    title: str = Field(..., description="标题")
    description: str = Field(..., description="描述")
    category: str = Field(..., description="分类")
    solution_steps: List[Dict[str, Any]] = Field(..., description="解决步骤")
    tags: Optional[List[str]] = Field(None, description="标签")
    required_tools: Optional[List[str]] = Field(None, description="需要的工具")
    estimated_time_minutes: Optional[int] = Field(None, description="预计耗时")


class AlarmProcessingResponse(BaseModel):
    """告警处理响应"""
    id: int
    alarm_id: int
    status: str
    priority: str
    assigned_to: Optional[int]
    assigned_by: Optional[int]
    assigned_at: Optional[datetime]
    acknowledged_by: Optional[int]
    acknowledged_at: Optional[datetime]
    resolved_by: Optional[int]
    resolved_at: Optional[datetime]
    resolution_method: Optional[str]
    response_time_minutes: Optional[int]
    resolution_time_minutes: Optional[int]
    sla_deadline: Optional[datetime]
    sla_breached: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProcessingHistoryResponse(BaseModel):
    """处理历史响应"""
    id: int
    action_type: str
    action_by: int
    action_at: datetime
    old_status: Optional[str]
    new_status: Optional[str]
    notes: Optional[str]
    
    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    """评论响应"""
    id: int
    content: str
    comment_type: str
    author_id: int
    author_name: str
    visibility: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True