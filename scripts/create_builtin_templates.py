#!/usr/bin/env python3
"""
创建内置告警模板
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.alert_template_manager import AlertTemplateManager
from src.models.alarm import AlertTemplateCategory, TemplateType


async def create_builtin_templates():
    """创建内置告警模板"""
    manager = AlertTemplateManager()
    
    templates = [
        # 系统性能模板
        {
            "name": "系统性能告警模板",
            "description": "用于系统性能相关告警的通用模板",
            "category": AlertTemplateCategory.PERFORMANCE,
            "template_type": TemplateType.RICH,
            "title_template": "【{{ severity.upper() }}】{{ title }}",
            "content_template": """系统: {{ host or 'Unknown' }}
服务: {{ service or 'Unknown' }}
环境: {{ environment or 'Unknown' }}

告警详情:
{{ description or '无详细描述' }}

{% if metadata %}
监控指标:
{% for key, value in metadata.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

首次发生: {{ first_occurrence }}
{% if count > 1 %}
告警次数: {{ count }}
最近发生: {{ last_occurrence }}
{% endif %}""",
            "summary_template": "{{ host }}: {{ title }}",
            "contact_point_types": ["email", "feishu", "webhook"],
            "severity_filter": ["critical", "high", "medium"],
            "is_builtin": True,
            "enabled": True,
            "priority": 100
        },
        
        # 应用错误模板
        {
            "name": "应用错误告警模板",
            "description": "用于应用程序错误告警的模板",
            "category": AlertTemplateCategory.APPLICATION,
            "template_type": TemplateType.MARKDOWN,
            "title_template": "🚨 {{ title }}",
            "content_template": """## 应用错误告警

**应用名称**: {{ service or 'Unknown' }}  
**主机**: {{ host or 'Unknown' }}  
**环境**: {{ environment or 'Unknown' }}  
**严重程度**: {{ severity.upper() }}  

### 错误详情
```
{{ description or '无详细描述' }}
```

{% if tags %}
### 标签信息
{% for key, value in tags.items() %}
- **{{ key }}**: {{ value }}
{% endfor %}
{% endif %}

### 时间信息
- **首次发生**: {{ first_occurrence }}
{% if count > 1 %}
- **发生次数**: {{ count }}
- **最近发生**: {{ last_occurrence }}
{% endif %}

---
*告警ID: {{ id }}*""",
            "summary_template": "{{ service }}: {{ title }}",
            "contact_point_types": ["email", "slack", "teams"],
            "severity_filter": ["critical", "high"],
            "source_filter": ["application", "service"],
            "is_builtin": True,
            "enabled": True,
            "priority": 90
        },
        
        # 网络连接模板
        {
            "name": "网络连接告警模板",
            "description": "用于网络连接问题的告警模板",
            "category": AlertTemplateCategory.NETWORK,
            "template_type": TemplateType.SIMPLE,
            "title_template": "网络告警: {{ title }}",
            "content_template": """网络连接告警

主机: {{ host or 'Unknown' }}
服务: {{ service or 'Unknown' }}
严重程度: {{ severity.upper() }}

问题描述:
{{ description or '网络连接异常' }}

发生时间: {{ first_occurrence }}
{% if count > 1 %}
重复次数: {{ count }}
{% endif %}

请及时检查网络连接状态。""",
            "contact_point_types": ["sms", "email"],
            "severity_filter": ["critical", "high"],
            "source_filter": ["network", "connectivity"],
            "is_builtin": True,
            "enabled": True,
            "priority": 80
        },
        
        # 安全事件模板
        {
            "name": "安全事件告警模板",
            "description": "用于安全相关事件的告警模板",
            "category": AlertTemplateCategory.SECURITY,
            "template_type": TemplateType.RICH,
            "title_template": "🔒 安全告警: {{ title }}",
            "content_template": """⚠️ 安全事件检测

事件类型: {{ category or 'Security Event' }}
影响主机: {{ host or 'Unknown' }}
严重程度: {{ severity.upper() }}

事件描述:
{{ description or '检测到安全异常' }}

{% if metadata %}
事件详情:
{% for key, value in metadata.items() %}
{{ key }}: {{ value }}
{% endfor %}
{% endif %}

{% if tags and tags.source_ip %}
来源IP: {{ tags.source_ip }}
{% endif %}

检测时间: {{ first_occurrence }}

⚡ 请立即进行安全检查和响应处理！""",
            "summary_template": "安全事件: {{ title }}",
            "contact_point_types": ["email", "sms", "webhook"],
            "severity_filter": ["critical", "high"],
            "source_filter": ["security", "intrusion"],
            "is_builtin": True,
            "enabled": True,
            "priority": 95
        },
        
        # JSON格式模板（用于Webhook）
        {
            "name": "Webhook JSON模板",
            "description": "用于Webhook集成的JSON格式模板",
            "category": AlertTemplateCategory.CUSTOM,
            "template_type": TemplateType.JSON,
            "title_template": "{{ title }}",
            "content_template": """{
  "alert_id": {{ id }},
  "title": "{{ title }}",
  "description": "{{ description | escape }}",
  "severity": "{{ severity }}",
  "status": "{{ status }}",
  "source": "{{ source }}",
  "host": "{{ host }}",
  "service": "{{ service }}",
  "environment": "{{ environment }}",
  "created_at": "{{ created_at }}",
  "first_occurrence": "{{ first_occurrence }}",
  "last_occurrence": "{{ last_occurrence }}",
  "count": {{ count }},
  {% if tags %}
  "tags": {{ tags | tojson }},
  {% endif %}
  {% if metadata %}
  "metadata": {{ metadata | tojson }},
  {% endif %}
  "is_duplicate": {{ is_duplicate | lower }},
  "correlation_id": "{{ correlation_id }}"
}""",
            "contact_point_types": ["webhook"],
            "is_builtin": True,
            "enabled": True,
            "priority": 70
        },
        
        # 简单邮件模板
        {
            "name": "简单邮件模板",
            "description": "适用于邮件通知的简洁模板",
            "category": AlertTemplateCategory.SYSTEM,
            "template_type": TemplateType.SIMPLE,
            "title_template": "[{{ severity.upper() }}] {{ title }}",
            "content_template": """告警通知

标题: {{ title }}
来源: {{ source }}
严重程度: {{ severity.upper() }}
状态: {{ status }}

{% if host %}主机: {{ host }}{% endif %}
{% if service %}服务: {{ service }}{% endif %}
{% if environment %}环境: {{ environment }}{% endif %}

描述:
{{ description or '无详细描述' }}

时间: {{ created_at }}

--
告警系统自动发送""",
            "contact_point_types": ["email", "sms"],
            "is_builtin": True,
            "enabled": True,
            "priority": 60
        }
    ]
    
    created_count = 0
    for template_data in templates:
        try:
            await manager.create_template(**template_data)
            created_count += 1
            print(f"✓ 创建模板: {template_data['name']}")
        except Exception as e:
            print(f"✗ 创建模板失败 {template_data['name']}: {str(e)}")
    
    print(f"\n共创建 {created_count} 个内置模板")


if __name__ == "__main__":
    asyncio.run(create_builtin_templates())