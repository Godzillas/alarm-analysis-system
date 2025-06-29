"""
默认通知模板创建服务
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.alarm import NotificationTemplate
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def create_default_templates(session: AsyncSession):
    """创建默认通知模板"""
    
    # 检查是否已存在模板
    query = select(NotificationTemplate).where(NotificationTemplate.is_system_template == True)
    result = await session.execute(query)
    existing_templates = result.scalars().all()
    
    if existing_templates:
        logger.info(f"发现 {len(existing_templates)} 个系统模板，跳过创建")
        return
    
    templates = [
        # 飞书通知模板
        {
            "name": "飞书默认告警模板",
            "description": "飞书机器人告警通知的默认模板",
            "template_type": "interactive",
            "content_type": "feishu",
            "title_template": "🚨 告警通知: {{ alarm.title }}",
            "content_template": """
**告警详情:**
- **严重程度:** {{ alarm.severity }}
- **状态:** {{ alarm.status }}
- **来源:** {{ alarm.source }}
- **描述:** {{ alarm.description or '无' }}
- **主机:** {{ alarm.host or '无' }}
- **服务:** {{ alarm.service or '无' }}
- **环境:** {{ alarm.environment or '无' }}
- **创建时间:** {{ alarm.created_at }}

**订阅信息:**
- **订阅名称:** {{ subscription.name }}
            """.strip(),
            "footer_template": "告警分析系统",
            "variables": {
                "alarm": {
                    "title": "告警标题",
                    "severity": "告警严重程度",
                    "status": "告警状态",
                    "source": "告警来源",
                    "description": "告警描述",
                    "host": "主机名",
                    "service": "服务名",
                    "environment": "环境",
                    "created_at": "创建时间"
                },
                "subscription": {
                    "name": "订阅名称"
                }
            },
            "style_config": {
                "color_mapping": {
                    "critical": "red",
                    "high": "orange", 
                    "medium": "blue",
                    "low": "grey",
                    "info": "green"
                }
            }
        },
        
        # 邮件通知模板
        {
            "name": "邮件默认告警模板",
            "description": "邮件告警通知的默认模板",
            "template_type": "html",
            "content_type": "email",
            "title_template": "[{{ alarm.severity|upper }}] {{ alarm.title }}",
            "content_template": """
<html>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
    <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <!-- Header -->
        <div style="background-color: {% if alarm.severity == 'critical' %}#ff4d4f{% elif alarm.severity == 'high' %}#fa8c16{% elif alarm.severity == 'medium' %}#1890ff{% else %}#52c41a{% endif %}; color: white; padding: 20px; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">🚨 告警通知</h1>
            <p style="margin: 10px 0 0 0; font-size: 18px;">{{ alarm.title }}</p>
        </div>
        
        <!-- Content -->
        <div style="padding: 20px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; font-weight: bold; width: 30%;">严重程度:</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">
                        <span style="padding: 4px 12px; border-radius: 4px; color: white; background-color: {% if alarm.severity == 'critical' %}#ff4d4f{% elif alarm.severity == 'high' %}#fa8c16{% elif alarm.severity == 'medium' %}#1890ff{% else %}#52c41a{% endif %};">
                            {{ alarm.severity|upper }}
                        </span>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; font-weight: bold;">状态:</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">{{ alarm.status }}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; font-weight: bold;">来源:</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">{{ alarm.source }}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; font-weight: bold;">描述:</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">{{ alarm.description or '无' }}</td>
                </tr>
                {% if alarm.host %}
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; font-weight: bold;">主机:</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">{{ alarm.host }}</td>
                </tr>
                {% endif %}
                {% if alarm.service %}
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; font-weight: bold;">服务:</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">{{ alarm.service }}</td>
                </tr>
                {% endif %}
                {% if alarm.environment %}
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; font-weight: bold;">环境:</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">{{ alarm.environment }}</td>
                </tr>
                {% endif %}
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; font-weight: bold;">创建时间:</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">{{ alarm.created_at }}</td>
                </tr>
            </table>
        </div>
        
        <!-- Footer -->
        <div style="background-color: #f0f0f0; padding: 15px; text-align: center; font-size: 12px; color: #666;">
            <p style="margin: 0;">此邮件由告警分析系统自动发送</p>
            <p style="margin: 5px 0 0 0;">订阅: {{ subscription.name }}</p>
        </div>
    </div>
</body>
</html>
            """.strip(),
            "footer_template": "告警分析系统自动发送",
            "variables": {
                "alarm": {
                    "title": "告警标题",
                    "severity": "告警严重程度", 
                    "status": "告警状态",
                    "source": "告警来源",
                    "description": "告警描述",
                    "host": "主机名",
                    "service": "服务名",
                    "environment": "环境",
                    "created_at": "创建时间"
                },
                "subscription": {
                    "name": "订阅名称"
                }
            },
            "style_config": {
                "email_format": "html"
            }
        },
        
        # Webhook通知模板
        {
            "name": "Webhook默认告警模板",
            "description": "Webhook告警通知的默认模板",
            "template_type": "json",
            "content_type": "webhook",
            "title_template": "{{ alarm.title }}",
            "content_template": """
{
    "notification_type": "alarm",
    "alarm": {
        "id": {{ alarm.id }},
        "title": "{{ alarm.title }}",
        "severity": "{{ alarm.severity }}",
        "status": "{{ alarm.status }}",
        "source": "{{ alarm.source }}",
        "description": "{{ alarm.description or '' }}",
        "host": "{{ alarm.host or '' }}",
        "service": "{{ alarm.service or '' }}",
        "environment": "{{ alarm.environment or '' }}",
        "created_at": "{{ alarm.created_at }}",
        "updated_at": "{{ alarm.updated_at }}",
        "tags": {{ alarm.tags|tojson if alarm.tags else '{}' }}
    },
    "subscription": {
        "id": {{ subscription.id }},
        "name": "{{ subscription.name }}",
        "type": "{{ subscription.subscription_type }}"
    },
    "timestamp": "{{ now() }}",
    "system": "alarm-analysis-system"
}
            """.strip(),
            "variables": {
                "alarm": {
                    "id": "告警ID",
                    "title": "告警标题",
                    "severity": "告警严重程度",
                    "status": "告警状态",
                    "source": "告警来源",
                    "description": "告警描述",
                    "host": "主机名",
                    "service": "服务名",
                    "environment": "环境",
                    "created_at": "创建时间",
                    "updated_at": "更新时间",
                    "tags": "标签"
                },
                "subscription": {
                    "id": "订阅ID",
                    "name": "订阅名称",
                    "type": "订阅类型"
                }
            },
            "style_config": {
                "content_type": "application/json"
            }
        },
        
        # 简单文本模板
        {
            "name": "简单文本告警模板",
            "description": "简单文本格式的告警通知模板",
            "template_type": "simple",
            "content_type": "text",
            "title_template": "[{{ alarm.severity|upper }}] {{ alarm.title }}",
            "content_template": """
告警通知

标题: {{ alarm.title }}
严重程度: {{ alarm.severity }}
状态: {{ alarm.status }}
来源: {{ alarm.source }}
描述: {{ alarm.description or '无' }}
{% if alarm.host %}主机: {{ alarm.host }}{% endif %}
{% if alarm.service %}服务: {{ alarm.service }}{% endif %}
{% if alarm.environment %}环境: {{ alarm.environment }}{% endif %}
创建时间: {{ alarm.created_at }}

订阅: {{ subscription.name }}
            """.strip(),
            "footer_template": "-- 告警分析系统",
            "variables": {
                "alarm": {
                    "title": "告警标题",
                    "severity": "告警严重程度",
                    "status": "告警状态", 
                    "source": "告警来源",
                    "description": "告警描述",
                    "host": "主机名",
                    "service": "服务名",
                    "environment": "环境",
                    "created_at": "创建时间"
                },
                "subscription": {
                    "name": "订阅名称"
                }
            },
            "style_config": {}
        }
    ]
    
    # 创建模板
    created_count = 0
    for template_data in templates:
        template = NotificationTemplate(
            name=template_data["name"],
            description=template_data["description"],
            template_type=template_data["template_type"],
            content_type=template_data["content_type"],
            title_template=template_data["title_template"],
            content_template=template_data["content_template"],
            footer_template=template_data.get("footer_template"),
            variables=template_data["variables"],
            style_config=template_data["style_config"],
            is_system_template=True,
            enabled=True
        )
        
        session.add(template)
        created_count += 1
    
    await session.commit()
    logger.info(f"成功创建 {created_count} 个默认通知模板")


async def ensure_default_templates_exist(session: AsyncSession):
    """确保默认模板存在"""
    try:
        await create_default_templates(session)
    except Exception as e:
        logger.error(f"创建默认模板失败: {str(e)}")
        raise