"""
值班管理数据模型
"""

from datetime import datetime, time
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Time, Text, JSON
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from src.models.alarm import Base


class OnCallShiftType(str, Enum):
    """值班班次类型"""
    DAILY = "daily"           # 日班
    WEEKLY = "weekly"         # 周班  
    MONTHLY = "monthly"       # 月班
    CUSTOM = "custom"         # 自定义


class OnCallStatus(str, Enum):
    """值班状态"""
    ACTIVE = "active"         # 当前值班
    SCHEDULED = "scheduled"   # 已安排
    COMPLETED = "completed"   # 已完成
    CANCELLED = "cancelled"   # 已取消


class EscalationLevel(str, Enum):
    """升级级别"""
    L1 = "L1"  # 一级
    L2 = "L2"  # 二级
    L3 = "L3"  # 三级
    L4 = "L4"  # 四级


class OnCallTeam(Base):
    """值班团队"""
    __tablename__ = "oncall_teams"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    
    # 团队配置
    timezone = Column(String(50), default="Asia/Shanghai")
    escalation_timeout = Column(Integer, default=300)  # 升级超时时间(秒)
    notification_methods = Column(JSON)  # 通知方式配置
    
    # 系统关联
    system_id = Column(Integer, ForeignKey('systems.id'), nullable=True, index=True)
    system = relationship("System")
    
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    members = relationship("OnCallMember", back_populates="team")
    schedules = relationship("OnCallSchedule", back_populates="team")
    escalation_policies = relationship("EscalationPolicy", back_populates="team")


class OnCallMember(Base):
    """值班成员"""
    __tablename__ = "oncall_members"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('oncall_teams.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 成员配置
    role = Column(String(50), default="member")  # member, leader, backup
    escalation_level = Column(String(10), default="L1")
    contact_methods = Column(JSON)  # 联系方式
    
    # 可用性配置
    working_hours_start = Column(Time, default=time(9, 0))
    working_hours_end = Column(Time, default=time(18, 0))
    working_days = Column(JSON, default=lambda: [1, 2, 3, 4, 5])  # 周一到周五
    
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    team = relationship("OnCallTeam", back_populates="members")
    user = relationship("User")
    shifts = relationship("OnCallShift", back_populates="member")


class OnCallSchedule(Base):
    """值班计划"""
    __tablename__ = "oncall_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('oncall_teams.id'), nullable=False)
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # 计划配置
    shift_type = Column(String(20), nullable=False, default=OnCallShiftType.WEEKLY)
    shift_duration = Column(Integer, default=7)  # 班次持续时间(天)
    rotation_start = Column(DateTime, nullable=False)  # 轮换开始时间
    
    # 高级配置
    include_holidays = Column(Boolean, default=True)
    auto_advance = Column(Boolean, default=True)  # 自动推进
    
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    team = relationship("OnCallTeam", back_populates="schedules")
    shifts = relationship("OnCallShift", back_populates="schedule")


class OnCallShift(Base):
    """值班班次"""
    __tablename__ = "oncall_shifts"
    
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey('oncall_schedules.id'), nullable=False)
    member_id = Column(Integer, ForeignKey('oncall_members.id'), nullable=False)
    
    # 班次时间
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    
    # 状态和配置
    status = Column(String(20), default=OnCallStatus.SCHEDULED)
    is_override = Column(Boolean, default=False)  # 是否为覆盖班次
    override_reason = Column(Text)
    
    # 统计信息
    alerts_received = Column(Integer, default=0)
    alerts_acknowledged = Column(Integer, default=0)
    alerts_resolved = Column(Integer, default=0)
    response_time_avg = Column(Integer, default=0)  # 平均响应时间(秒)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    schedule = relationship("OnCallSchedule", back_populates="shifts")
    member = relationship("OnCallMember", back_populates="shifts")


class EscalationPolicy(Base):
    """升级策略"""
    __tablename__ = "escalation_policies"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('oncall_teams.id'), nullable=False)
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # 升级规则
    escalation_rules = Column(JSON, nullable=False)  # 升级规则配置
    
    # 应用条件
    severity_filter = Column(JSON)  # 严重程度过滤
    time_filter = Column(JSON)     # 时间过滤
    tag_filter = Column(JSON)      # 标签过滤
    
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    team = relationship("OnCallTeam", back_populates="escalation_policies")


class OnCallOverride(Base):
    """值班覆盖"""
    __tablename__ = "oncall_overrides"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('oncall_teams.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 覆盖时间
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    reason = Column(Text)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    team = relationship("OnCallTeam")
    user = relationship("User", foreign_keys=[user_id])
    creator = relationship("User", foreign_keys=[created_by])


# Pydantic 模型

class OnCallTeamCreate(BaseModel):
    name: str = Field(..., description="团队名称")
    description: Optional[str] = Field(None, description="团队描述")
    timezone: str = Field("Asia/Shanghai", description="时区")
    escalation_timeout: int = Field(300, description="升级超时时间(秒)")
    notification_methods: Optional[List[str]] = Field(None, description="通知方式")
    system_id: Optional[int] = Field(None, description="所属系统ID")


class OnCallTeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    timezone: Optional[str] = None
    escalation_timeout: Optional[int] = None
    notification_methods: Optional[List[str]] = None
    system_id: Optional[int] = None
    enabled: Optional[bool] = None


class OnCallTeamResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    timezone: str
    escalation_timeout: int
    notification_methods: Optional[List[str]]
    system_id: Optional[int]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OnCallMemberCreate(BaseModel):
    team_id: int = Field(..., description="团队ID")
    user_id: int = Field(..., description="用户ID")
    role: str = Field("member", description="角色")
    escalation_level: str = Field("L1", description="升级级别")
    contact_methods: Optional[List[str]] = Field(None, description="联系方式")
    working_hours_start: Optional[time] = Field(None, description="工作开始时间")
    working_hours_end: Optional[time] = Field(None, description="工作结束时间")
    working_days: Optional[List[int]] = Field(None, description="工作日")


class OnCallMemberResponse(BaseModel):
    id: int
    team_id: int
    user_id: int
    role: str
    escalation_level: str
    contact_methods: Optional[List[str]]
    working_hours_start: Optional[time]
    working_hours_end: Optional[time]
    working_days: Optional[List[int]]
    enabled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class OnCallScheduleCreate(BaseModel):
    team_id: int = Field(..., description="团队ID")
    name: str = Field(..., description="计划名称")
    description: Optional[str] = Field(None, description="计划描述")
    shift_type: OnCallShiftType = Field(..., description="班次类型")
    shift_duration: int = Field(7, description="班次持续时间(天)")
    rotation_start: datetime = Field(..., description="轮换开始时间")
    include_holidays: bool = Field(True, description="包含假期")
    auto_advance: bool = Field(True, description="自动推进")


class OnCallScheduleResponse(BaseModel):
    id: int
    team_id: int
    name: str
    description: Optional[str]
    shift_type: str
    shift_duration: int
    rotation_start: datetime
    include_holidays: bool
    auto_advance: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OnCallShiftResponse(BaseModel):
    id: int
    schedule_id: int
    member_id: int
    start_time: datetime
    end_time: datetime
    status: str
    is_override: bool
    override_reason: Optional[str]
    alerts_received: int
    alerts_acknowledged: int
    alerts_resolved: int
    response_time_avg: int
    
    class Config:
        from_attributes = True


class EscalationPolicyCreate(BaseModel):
    team_id: int = Field(..., description="团队ID")
    name: str = Field(..., description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")
    escalation_rules: List[dict] = Field(..., description="升级规则")
    severity_filter: Optional[List[str]] = Field(None, description="严重程度过滤")
    time_filter: Optional[dict] = Field(None, description="时间过滤")
    tag_filter: Optional[dict] = Field(None, description="标签过滤")


class EscalationPolicyResponse(BaseModel):
    id: int
    team_id: int
    name: str
    description: Optional[str]
    escalation_rules: List[dict]
    severity_filter: Optional[List[str]]
    time_filter: Optional[dict]
    tag_filter: Optional[dict]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OnCallOverrideCreate(BaseModel):
    team_id: int = Field(..., description="团队ID")
    user_id: int = Field(..., description="用户ID")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    reason: Optional[str] = Field(None, description="覆盖原因")


class OnCallOverrideResponse(BaseModel):
    id: int
    team_id: int
    user_id: int
    start_time: datetime
    end_time: datetime
    reason: Optional[str]
    created_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True