"""
告警订阅和通知模型
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from src.models.alarm import Base


class SubscriptionType(str, Enum):
    """订阅类型"""
    IMMEDIATE = "immediate"     # 立即通知
    DIGEST = "digest"          # 摘要通知
    WEEKLY = "weekly"          # 周报
    CUSTOM = "custom"          # 自定义


class NotificationChannel(str, Enum):
    """通知渠道"""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"
    WECHAT = "wechat"
    PUSH = "push"


class NotificationStatus(str, Enum):
    """通知状态"""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"


class NotificationPriority(str, Enum):
    """通知优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AlarmSubscription(Base):
    """告警订阅"""
    __tablename__ = "alarm_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # 订阅者信息
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    team_id = Column(Integer, nullable=True)  # 可选的团队ID
    
    # 订阅配置
    subscription_type = Column(String(20), default=SubscriptionType.IMMEDIATE, index=True)
    enabled = Column(Boolean, default=True, index=True)
    
    # 过滤条件
    filter_conditions = Column(JSON, nullable=False)  # 告警过滤条件
    
    # 通知配置
    notification_channels = Column(JSON, nullable=False)  # 通知渠道配置
    notification_template_id = Column(Integer, ForeignKey('notification_templates.id'), nullable=True)
    
    # 调度配置
    schedule_config = Column(JSON, nullable=True)  # 调度配置（摘要通知等）
    timezone = Column(String(50), default="UTC")
    
    # 静默配置
    quiet_hours = Column(JSON, nullable=True)  # 静默时段配置
    holiday_config = Column(JSON, nullable=True)  # 节假日配置
    
    # 限流配置
    rate_limit_config = Column(JSON, nullable=True)  # 限流配置
    
    # 升级配置
    escalation_config = Column(JSON, nullable=True)  # 升级通知配置
    
    # 统计信息
    total_notifications = Column(Integer, default=0)
    successful_notifications = Column(Integer, default=0)
    failed_notifications = Column(Integer, default=0)
    last_notification_at = Column(DateTime, nullable=True)
    
    # 元数据
    subscription_metadata = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    user = relationship("User", foreign_keys=[user_id])
    template = relationship("NotificationTemplate", foreign_keys=[notification_template_id])
    notifications = relationship("AlarmNotification", back_populates="subscription")


class NotificationTemplate(Base):
    """通知模板"""
    __tablename__ = "notification_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # 模板类型和用途
    template_type = Column(String(20), nullable=False, index=True)  # immediate, digest, escalation
    channel_type = Column(String(20), nullable=False, index=True)   # email, sms, webhook等
    
    # 模板内容
    subject_template = Column(Text, nullable=True)     # 主题模板（邮件等）
    content_template = Column(Text, nullable=False)    # 内容模板
    html_template = Column(Text, nullable=True)        # HTML模板（邮件）
    
    # 模板变量
    available_variables = Column(JSON, nullable=True)   # 可用变量列表
    required_variables = Column(JSON, nullable=True)    # 必需变量列表
    
    # 格式化配置
    format_config = Column(JSON, nullable=True)        # 格式化配置
    
    # 应用条件
    applicable_channels = Column(JSON, nullable=True)   # 适用的通知渠道
    severity_filter = Column(JSON, nullable=True)       # 严重程度过滤
    
    # 版本信息
    version = Column(String(20), default="1.0")
    is_default = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)
    
    # 使用统计
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    
    enabled = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    creator = relationship("User", foreign_keys=[created_by])
    subscriptions = relationship("AlarmSubscription", back_populates="template")


class AlarmNotification(Base):
    """告警通知记录"""
    __tablename__ = "alarm_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 关联信息
    alarm_id = Column(Integer, ForeignKey('alarms.id'), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey('alarm_subscriptions.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # 通知内容
    notification_type = Column(String(20), nullable=False, index=True)  # immediate, digest, escalation
    channel = Column(String(20), nullable=False, index=True)
    recipient = Column(String(255), nullable=False)  # 接收者（邮箱、手机号等）
    
    # 消息内容
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    html_content = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)
    
    # 发送状态
    status = Column(String(20), default=NotificationStatus.PENDING, index=True)
    priority = Column(String(20), default=NotificationPriority.NORMAL, index=True)
    
    # 时间信息
    scheduled_at = Column(DateTime, nullable=True)    # 计划发送时间
    sent_at = Column(DateTime, nullable=True)         # 实际发送时间
    delivered_at = Column(DateTime, nullable=True)    # 送达时间
    read_at = Column(DateTime, nullable=True)         # 阅读时间
    
    # 重试信息
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_retry_at = Column(DateTime, nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # 外部服务信息
    external_id = Column(String(255), nullable=True)   # 外部服务的消息ID
    webhook_url = Column(String(500), nullable=True)   # Webhook URL
    
    # 通知配置快照
    notification_config = Column(JSON, nullable=True)  # 发送时的配置快照
    
    # 性能指标
    processing_time_ms = Column(Integer, nullable=True)  # 处理耗时
    delivery_time_ms = Column(Integer, nullable=True)    # 送达耗时
    
    # 元数据
    notification_metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    alarm = relationship("AlarmTable", foreign_keys=[alarm_id])
    subscription = relationship("AlarmSubscription", back_populates="notifications")
    user = relationship("User", foreign_keys=[user_id])


class NotificationChannel(Base):
    """通知渠道配置"""
    __tablename__ = "notification_channels"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # 渠道类型
    channel_type = Column(String(20), nullable=False, index=True)
    
    # 连接配置
    connection_config = Column(JSON, nullable=False)  # 连接参数
    auth_config = Column(JSON, nullable=True)         # 认证配置
    
    # 限流配置
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_hour = Column(Integer, default=1000)
    rate_limit_per_day = Column(Integer, default=10000)
    
    # 重试配置
    retry_config = Column(JSON, nullable=True)
    
    # 健康检查
    health_check_config = Column(JSON, nullable=True)
    last_health_check = Column(DateTime, nullable=True)
    is_healthy = Column(Boolean, default=True)
    
    # 统计信息
    total_sent = Column(Integer, default=0)
    successful_sent = Column(Integer, default=0)
    failed_sent = Column(Integer, default=0)
    last_sent = Column(DateTime, nullable=True)
    
    # 成本信息
    cost_per_message = Column(String(10), nullable=True)  # 每条消息成本
    
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationDigest(Base):
    """通知摘要"""
    __tablename__ = "notification_digests"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 摘要信息
    subscription_id = Column(Integer, ForeignKey('alarm_subscriptions.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # 时间范围
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    digest_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    
    # 摘要内容
    alarm_count = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    
    # 摘要数据
    alarm_summary = Column(JSON, nullable=False)      # 告警汇总数据
    trend_analysis = Column(JSON, nullable=True)      # 趋势分析
    
    # 发送状态
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    notification_id = Column(Integer, ForeignKey('alarm_notifications.id'), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 关联关系
    subscription = relationship("AlarmSubscription", foreign_keys=[subscription_id])
    user = relationship("User", foreign_keys=[user_id])
    notification = relationship("AlarmNotification", foreign_keys=[notification_id])


# Pydantic模型用于API

class SubscriptionCreate(BaseModel):
    """创建订阅"""
    name: str = Field(..., description="订阅名称")
    description: Optional[str] = Field(None, description="订阅描述")
    subscription_type: SubscriptionType = Field(SubscriptionType.IMMEDIATE, description="订阅类型")
    filter_conditions: Dict[str, Any] = Field(..., description="过滤条件")
    notification_channels: List[Dict[str, Any]] = Field(..., description="通知渠道配置")
    notification_template_id: Optional[int] = Field(None, description="通知模板ID")
    schedule_config: Optional[Dict[str, Any]] = Field(None, description="调度配置")
    quiet_hours: Optional[Dict[str, Any]] = Field(None, description="静默时段")
    rate_limit_config: Optional[Dict[str, Any]] = Field(None, description="限流配置")
    tags: Optional[List[str]] = Field(None, description="标签")


class SubscriptionUpdate(BaseModel):
    """更新订阅"""
    name: Optional[str] = None
    description: Optional[str] = None
    subscription_type: Optional[SubscriptionType] = None
    filter_conditions: Optional[Dict[str, Any]] = None
    notification_channels: Optional[List[Dict[str, Any]]] = None
    notification_template_id: Optional[int] = None
    schedule_config: Optional[Dict[str, Any]] = None
    quiet_hours: Optional[Dict[str, Any]] = None
    rate_limit_config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None


class NotificationTemplateCreate(BaseModel):
    """创建通知模板"""
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    template_type: str = Field(..., description="模板类型")
    channel_type: str = Field(..., description="渠道类型")
    subject_template: Optional[str] = Field(None, description="主题模板")
    content_template: str = Field(..., description="内容模板")
    html_template: Optional[str] = Field(None, description="HTML模板")
    format_config: Optional[Dict[str, Any]] = Field(None, description="格式化配置")
    applicable_channels: Optional[List[str]] = Field(None, description="适用渠道")


class NotificationChannelCreate(BaseModel):
    """创建通知渠道"""
    name: str = Field(..., description="渠道名称")
    description: Optional[str] = Field(None, description="渠道描述")
    channel_type: str = Field(..., description="渠道类型")
    connection_config: Dict[str, Any] = Field(..., description="连接配置")
    auth_config: Optional[Dict[str, Any]] = Field(None, description="认证配置")
    rate_limit_per_minute: int = Field(60, description="每分钟限制")
    rate_limit_per_hour: int = Field(1000, description="每小时限制")
    retry_config: Optional[Dict[str, Any]] = Field(None, description="重试配置")


class SubscriptionResponse(BaseModel):
    """订阅响应"""
    id: int
    name: str
    description: Optional[str]
    user_id: int
    subscription_type: str
    enabled: bool
    filter_conditions: Dict[str, Any]
    notification_channels: List[Dict[str, Any]]
    total_notifications: int
    successful_notifications: int
    failed_notifications: int
    last_notification_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    """通知响应"""
    id: int
    alarm_id: int
    subscription_id: int
    notification_type: str
    channel: str
    recipient: str
    subject: Optional[str]
    status: str
    priority: str
    scheduled_at: Optional[datetime]
    sent_at: Optional[datetime]
    retry_count: int
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class NotificationTemplateResponse(BaseModel):
    """通知模板响应"""
    id: int
    name: str
    description: Optional[str]
    template_type: str
    channel_type: str
    subject_template: Optional[str]
    content_template: str
    version: str
    is_default: bool
    usage_count: int
    enabled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True