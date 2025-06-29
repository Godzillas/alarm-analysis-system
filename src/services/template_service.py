"""
通知模板服务
负责模板管理和内容渲染
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
import jinja2

from src.core.database import async_session_maker
from src.core.logging import get_logger
from src.core.exceptions import (
    DatabaseException, ValidationException,
    ResourceNotFoundException
)
from src.models.alarm import (
    NotificationTemplate, NotificationLog
)
from src.models.alarm import AlarmTable

logger = get_logger(__name__)


class TemplateService:
    """模板服务"""
    
    def __init__(self):
        self.logger = logger
        self.jinja_env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=True
        )
    
    async def create_template(
        self,
        user_id: int,
        template_data: NotificationTemplateCreate
    ) -> NotificationTemplate:
        """创建通知模板"""
        async with async_session_maker() as session:
            try:
                # 检查模板名称是否重复
                existing = await session.execute(
                    select(NotificationTemplate).where(
                        NotificationTemplate.name == template_data.name
                    )
                )
                if existing.scalar_one_or_none():
                    raise ValidationException(
                        "Template with this name already exists",
                        field="name"
                    )
                
                # 验证模板语法
                self._validate_template_syntax(template_data.content_template)
                if template_data.subject_template:
                    self._validate_template_syntax(template_data.subject_template)
                if template_data.html_template:
                    self._validate_template_syntax(template_data.html_template)
                
                # 创建模板
                template = NotificationTemplate(
                    name=template_data.name,
                    description=template_data.description,
                    template_type=template_data.template_type,
                    content_type=template_data.content_type,
                    subject_template=template_data.subject_template,
                    content_template=template_data.content_template,
                    html_template=template_data.html_template,
                    created_by=user_id
                )
                
                session.add(template)
                await session.commit()
                
                self.logger.info(
                    f"Created template: {template.name}",
                    extra={
                        "template_id": template.id,
                        "user_id": user_id,
                        "template_type": template.template_type
                    }
                )
                
                return template
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, ValidationException):
                    raise
                raise DatabaseException(f"Failed to create template: {str(e)}")
    
    async def render_notification_content(
        self,
        template_id: Optional[int],
        alarm: AlarmTable,
        channel_type: str,
        template_type: str = "immediate",
        custom_variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """渲染通知内容"""
        try:
            template = None
            
            if template_id:
                # 使用指定模板
                async with async_session_maker() as session:
                    template = await session.get(NotificationTemplate, template_id)
            
            if not template:
                # 使用默认模板
                template = await self._get_default_template(channel_type, template_type)
            
            if not template:
                # 使用内置模板
                return self._render_builtin_template(alarm, channel_type, custom_variables)
            
            # 准备模板变量
            variables = self._prepare_template_variables(alarm, custom_variables)
            
            # 渲染内容
            content = self._render_template(template.content_template, variables)
            subject = self._render_template(template.subject_template, variables) if template.subject_template else None
            html_content = self._render_template(template.html_template, variables) if template.html_template else None
            
            # 更新模板使用统计
            await self._update_template_usage(template.id)
            
            return {
                "subject": subject,
                "content": content,
                "html_content": html_content
            }
            
        except Exception as e:
            self.logger.error(f"Error rendering template: {str(e)}")
            # 回退到内置模板
            return self._render_builtin_template(alarm, channel_type, custom_variables)
    
    async def get_templates(
        self,
        template_type: Optional[str] = None,
        channel_type: Optional[str] = None,
        enabled_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[NotificationTemplate]:
        """获取模板列表"""
        async with async_session_maker() as session:
            try:
                query = select(NotificationTemplate)
                
                conditions = []
                if template_type:
                    conditions.append(NotificationTemplate.template_type == template_type)
                if channel_type:
                    conditions.append(NotificationTemplate.channel_type == channel_type)
                if enabled_only:
                    conditions.append(NotificationTemplate.enabled == True)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                query = query.order_by(desc(NotificationTemplate.usage_count))
                query = query.limit(limit).offset(offset)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                raise DatabaseException(f"Failed to get templates: {str(e)}")
    
    async def test_template_rendering(
        self,
        template_id: int,
        test_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """测试模板渲染"""
        async with async_session_maker() as session:
            try:
                template = await session.get(NotificationTemplate, template_id)
                if not template:
                    raise ResourceNotFoundException("NotificationTemplate", template_id)
                
                # 使用测试数据渲染
                content = self._render_template(template.content_template, test_data)
                subject = self._render_template(template.subject_template, test_data) if template.subject_template else None
                html_content = self._render_template(template.html_template, test_data) if template.html_template else None
                
                return {
                    "subject": subject,
                    "content": content,
                    "html_content": html_content
                }
                
            except Exception as e:
                if isinstance(e, ResourceNotFoundException):
                    raise
                raise DatabaseException(f"Failed to test template: {str(e)}")
    
    async def get_available_variables(self) -> Dict[str, Any]:
        """获取可用的模板变量"""
        return {
            "alarm": {
                "id": "告警ID",
                "title": "告警标题", 
                "description": "告警描述",
                "severity": "严重程度",
                "status": "告警状态",
                "source": "告警源",
                "category": "告警分类",
                "host": "主机名",
                "service": "服务名",
                "environment": "环境",
                "created_at": "创建时间",
                "updated_at": "更新时间",
                "tags": "标签字典"
            },
            "system": {
                "current_time": "当前时间",
                "system_name": "系统名称",
                "dashboard_url": "仪表板URL"
            },
            "user": {
                "name": "用户名",
                "email": "用户邮箱"
            },
            "custom": {
                "additional_info": "自定义信息",
                "context": "上下文数据"
            }
        }
    
    async def create_builtin_templates(self):
        """创建内置模板"""
        builtin_templates = [
            {
                "name": "默认邮件模板",
                "description": "系统默认的邮件通知模板",
                "template_type": "immediate",
                "channel_type": "email",
                "subject_template": "告警通知: {{ alarm.title }}",
                "content_template": """
告警详情:
- 标题: {{ alarm.title }}
- 严重程度: {{ alarm.severity }}
- 状态: {{ alarm.status }}
- 来源: {{ alarm.source }}
- 主机: {{ alarm.host or 'N/A' }}
- 服务: {{ alarm.service or 'N/A' }}
- 环境: {{ alarm.environment or 'N/A' }}
- 时间: {{ alarm.created_at }}

描述:
{{ alarm.description }}

请及时处理此告警。
                """.strip(),
                "html_template": """
<html>
<body>
<h2>告警通知</h2>
<table border="1" cellpadding="5" cellspacing="0">
<tr><td><strong>标题</strong></td><td>{{ alarm.title }}</td></tr>
<tr><td><strong>严重程度</strong></td><td><span style="color: {% if alarm.severity == 'critical' %}red{% elif alarm.severity == 'high' %}orange{% else %}black{% endif %}">{{ alarm.severity }}</span></td></tr>
<tr><td><strong>状态</strong></td><td>{{ alarm.status }}</td></tr>
<tr><td><strong>来源</strong></td><td>{{ alarm.source }}</td></tr>
<tr><td><strong>主机</strong></td><td>{{ alarm.host or 'N/A' }}</td></tr>
<tr><td><strong>服务</strong></td><td>{{ alarm.service or 'N/A' }}</td></tr>
<tr><td><strong>环境</strong></td><td>{{ alarm.environment or 'N/A' }}</td></tr>
<tr><td><strong>时间</strong></td><td>{{ alarm.created_at }}</td></tr>
</table>
<p><strong>描述:</strong></p>
<p>{{ alarm.description }}</p>
<p>请及时处理此告警。</p>
</body>
</html>
                """.strip(),
                "is_default": True,
                "is_system": True
            },
            {
                "name": "默认Webhook模板",
                "description": "系统默认的Webhook通知模板",
                "template_type": "immediate",
                "channel_type": "webhook",
                "content_template": """{
    "alarm_id": {{ alarm.id }},
    "title": "{{ alarm.title }}",
    "severity": "{{ alarm.severity }}",
    "status": "{{ alarm.status }}",
    "source": "{{ alarm.source }}",
    "description": "{{ alarm.description }}",
    "host": "{{ alarm.host }}",
    "service": "{{ alarm.service }}",
    "environment": "{{ alarm.environment }}",
    "created_at": "{{ alarm.created_at }}",
    "tags": {{ alarm.tags | tojson if alarm.tags else '{}' }},
    "timestamp": "{{ system.current_time }}"
}""",
                "is_default": True,
                "is_system": True
            },
            {
                "name": "简短短信模板",
                "description": "适用于短信的简短通知模板",
                "template_type": "immediate", 
                "channel_type": "sms",
                "content_template": "【告警】{{ alarm.severity }}级告警: {{ alarm.title }} ({{ alarm.host or alarm.service }}) - {{ alarm.created_at.strftime('%H:%M') }}",
                "is_default": True,
                "is_system": True
            }
        ]
        
        async with async_session_maker() as session:
            try:
                for template_data in builtin_templates:
                    # 检查是否已存在
                    existing = await session.execute(
                        select(NotificationTemplate).where(
                            NotificationTemplate.name == template_data["name"]
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue
                    
                    # 查找系统用户，如果不存在则创建
                    from src.models.alarm import User
                    
                    # 尝试找到系统用户
                    system_user_result = await session.execute(
                        select(User).where(User.username == "system")
                    )
                    system_user = system_user_result.scalar_one_or_none()
                    
                    if not system_user:
                        # 创建系统用户
                        system_user = User(
                            username="system",
                            email="system@alarm-system.local",
                            password_hash="system",  # 系统用户不需要真实密码
                            full_name="系统用户",
                            is_active=False,  # 系统用户不能登录
                            is_admin=False
                        )
                        session.add(system_user)
                        await session.flush()
                    
                    template = NotificationTemplate(
                        created_by=system_user.id,
                        **template_data
                    )
                    session.add(template)
                
                await session.commit()
                self.logger.info("Created builtin notification templates")
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error creating builtin templates: {str(e)}")
    
    # 私有方法
    
    def _validate_template_syntax(self, template_string: str):
        """验证模板语法"""
        try:
            self.jinja_env.from_string(template_string)
        except jinja2.TemplateSyntaxError as e:
            raise ValidationException(f"Template syntax error: {str(e)}")
    
    def _render_template(self, template_string: str, variables: Dict[str, Any]) -> str:
        """渲染模板"""
        if not template_string:
            return ""
        
        try:
            template = self.jinja_env.from_string(template_string)
            return template.render(**variables)
        except Exception as e:
            self.logger.error(f"Template rendering error: {str(e)}")
            return template_string  # 返回原始字符串作为回退
    
    def _prepare_template_variables(
        self, 
        alarm: AlarmTable,
        custom_variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """准备模板变量"""
        variables = {
            "alarm": {
                "id": alarm.id,
                "title": alarm.title,
                "description": alarm.description or "",
                "severity": alarm.severity,
                "status": alarm.status,
                "source": alarm.source,
                "category": alarm.category,
                "host": alarm.host,
                "service": alarm.service,
                "environment": alarm.environment,
                "created_at": alarm.created_at,
                "updated_at": alarm.updated_at,
                "tags": alarm.tags or {}
            },
            "system": {
                "current_time": datetime.utcnow(),
                "system_name": "告警分析系统",
                "dashboard_url": "http://localhost:8000"
            }
        }
        
        if custom_variables:
            variables.update(custom_variables)
        
        return variables
    
    async def _get_default_template(
        self,
        channel_type: str,
        template_type: str
    ) -> Optional[NotificationTemplate]:
        """获取默认模板"""
        async with async_session_maker() as session:
            try:
                query = select(NotificationTemplate).where(
                    and_(
                        NotificationTemplate.channel_type == channel_type,
                        NotificationTemplate.template_type == template_type,
                        NotificationTemplate.is_default == True,
                        NotificationTemplate.enabled == True
                    )
                )
                
                result = await session.execute(query)
                return result.scalar_one_or_none()
                
            except Exception as e:
                self.logger.error(f"Error getting default template: {str(e)}")
                return None
    
    def _render_builtin_template(
        self,
        alarm: AlarmTable,
        channel_type: str,
        custom_variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """渲染内置模板"""
        variables = self._prepare_template_variables(alarm, custom_variables)
        
        if channel_type == "email":
            return {
                "subject": f"告警通知: {alarm.title}",
                "content": f"""
告警详情:
- 标题: {alarm.title}
- 严重程度: {alarm.severity}
- 状态: {alarm.status}
- 来源: {alarm.source}
- 时间: {alarm.created_at}

描述: {alarm.description or 'N/A'}
                """.strip(),
                "html_content": None
            }
        elif channel_type == "sms":
            return {
                "subject": None,
                "content": f"【告警】{alarm.severity}级: {alarm.title[:20]}...",
                "html_content": None
            }
        else:
            return {
                "subject": f"告警通知: {alarm.title}",
                "content": f"告警: {alarm.title} | 级别: {alarm.severity} | 时间: {alarm.created_at}",
                "html_content": None
            }
    
    async def _update_template_usage(self, template_id: int):
        """更新模板使用统计"""
        try:
            async with async_session_maker() as session:
                template = await session.get(NotificationTemplate, template_id)
                if template:
                    template.usage_count += 1
                    template.last_used = datetime.utcnow()
                    await session.commit()
        except Exception as e:
            self.logger.error(f"Error updating template usage: {str(e)}")