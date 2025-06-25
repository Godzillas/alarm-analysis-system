"""
告警模板管理服务
"""

import re
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from jinja2 import Template, Environment, TemplateSyntaxError, meta

from src.models.alarm import AlertTemplate, AlertTemplateCategory, TemplateType, System, AlarmTable
from src.utils.logger import get_logger
from src.core.database import get_db_session, async_session_maker


class AlertTemplateManager:
    """告警模板管理器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.jinja_env = Environment()
    
    async def create_template(
        self,
        name: str,
        category: AlertTemplateCategory,
        template_type: TemplateType,
        title_template: str,
        content_template: str,
        system_id: Optional[int] = None,
        **kwargs
    ) -> AlertTemplate:
        """创建告警模板"""
        async with async_session_maker() as db:
            try:
                # 检查名称是否已存在
                existing = await db.execute(
                    select(AlertTemplate).where(AlertTemplate.name == name)
                )
                if existing.scalar_one_or_none():
                    raise ValueError(f"模板名称 '{name}' 已存在")
                
                # 验证模板语法
                await self._validate_template_syntax(title_template, content_template)
                
                # 创建模板
                template = AlertTemplate(
                    name=name,
                    category=category.value,
                    template_type=template_type.value,
                    title_template=title_template,
                    content_template=content_template,
                    system_id=system_id,
                    **kwargs
                )
                
                db.add(template)
                await db.commit()
                await db.refresh(template)
                
                self.logger.info(f"创建告警模板成功: {name}")
                return template
                
            except Exception as e:
                await db.rollback()
                self.logger.error(f"创建告警模板失败: {str(e)}")
                raise
    
    async def update_template(
        self,
        template_id: int,
        **update_data
    ) -> AlertTemplate:
        """更新告警模板"""
        async with async_session_maker() as db:
            try:
                template = await db.get(AlertTemplate, template_id)
                if not template:
                    raise ValueError(f"模板 ID {template_id} 不存在")
                
                # 如果更新了模板内容，验证语法
                if 'title_template' in update_data or 'content_template' in update_data:
                    title_template = update_data.get('title_template', template.title_template)
                    content_template = update_data.get('content_template', template.content_template)
                    await self._validate_template_syntax(title_template, content_template)
                
                # 更新字段
                for field, value in update_data.items():
                    if hasattr(template, field) and not field.startswith('_'):
                        setattr(template, field, value)
                
                template.updated_at = datetime.utcnow()
                await db.commit()
                await db.refresh(template)
                
                self.logger.info(f"更新告警模板成功: {template.name}")
                return template
                
            except Exception as e:
                await db.rollback()
                self.logger.error(f"更新告警模板失败: {str(e)}")
                raise
    
    async def delete_template(self, template_id: int) -> bool:
        """删除告警模板"""
        async with async_session_maker() as db:
            try:
                template = await db.get(AlertTemplate, template_id)
                if not template:
                    raise ValueError(f"模板 ID {template_id} 不存在")
                
                if template.is_builtin:
                    raise ValueError("内置模板不能删除")
                
                # 检查是否有规则在使用此模板
                # TODO: 实现规则关联检查
                
                await db.delete(template)
                await db.commit()
                
                self.logger.info(f"删除告警模板成功: {template.name}")
                return True
                
            except Exception as e:
                await db.rollback()
                self.logger.error(f"删除告警模板失败: {str(e)}")
                raise
    
    async def get_templates(
        self,
        system_id: Optional[int] = None,
        category: Optional[AlertTemplateCategory] = None,
        template_type: Optional[TemplateType] = None,
        enabled: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AlertTemplate]:
        """获取告警模板列表"""
        async with async_session_maker() as db:
            try:
                query = select(AlertTemplate).options(selectinload(AlertTemplate.system))
                
                conditions = []
                if system_id is not None:
                    conditions.append(AlertTemplate.system_id == system_id)
                if category is not None:
                    conditions.append(AlertTemplate.category == category.value)
                if template_type is not None:
                    conditions.append(AlertTemplate.template_type == template_type.value)
                if enabled is not None:
                    conditions.append(AlertTemplate.enabled == enabled)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                query = query.offset(skip).limit(limit)
                query = query.order_by(AlertTemplate.priority.desc(), AlertTemplate.created_at.desc())
                
                result = await db.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                self.logger.error(f"获取告警模板列表失败: {str(e)}")
                raise
    
    async def get_template_by_id(self, template_id: int) -> Optional[AlertTemplate]:
        """根据ID获取告警模板"""
        async with async_session_maker() as db:
            try:
                query = select(AlertTemplate).options(selectinload(AlertTemplate.system))
                query = query.where(AlertTemplate.id == template_id)
                
                result = await db.execute(query)
                return result.scalar_one_or_none()
                
            except Exception as e:
                self.logger.error(f"获取告警模板失败: {str(e)}")
                raise
    
    async def render_template(
        self,
        template_id: int,
        alarm_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """渲染告警模板"""
        try:
            template = await self.get_template_by_id(template_id)
            if not template:
                raise ValueError(f"模板 ID {template_id} 不存在")
            
            if not template.enabled:
                raise ValueError("模板已禁用")
            
            # 应用字段映射
            mapped_data = self._apply_field_mapping(alarm_data, template.field_mapping)
            
            # 渲染模板
            title = self._render_text_template(template.title_template, mapped_data)
            content = self._render_text_template(template.content_template, mapped_data)
            summary = None
            
            if template.summary_template:
                summary = self._render_text_template(template.summary_template, mapped_data)
            
            # 更新使用统计
            await self._update_usage_stats(template_id)
            
            return {
                "title": title,
                "content": content,
                "summary": summary,
                "template_type": template.template_type,
                "template_config": template.template_config or {}
            }
            
        except Exception as e:
            self.logger.error(f"渲染模板失败: {str(e)}")
            raise
    
    async def preview_template(
        self,
        title_template: str,
        content_template: str,
        summary_template: Optional[str] = None,
        sample_data: Optional[Dict[str, Any]] = None,
        field_mapping: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """预览模板渲染效果"""
        try:
            # 使用示例数据或默认数据
            if not sample_data:
                sample_data = self._get_default_sample_data()
            
            # 应用字段映射
            mapped_data = self._apply_field_mapping(sample_data, field_mapping)
            
            # 渲染模板
            title = self._render_text_template(title_template, mapped_data)
            content = self._render_text_template(content_template, mapped_data)
            summary = None
            
            if summary_template:
                summary = self._render_text_template(summary_template, mapped_data)
            
            return {
                "title": title,
                "content": content,
                "summary": summary,
                "sample_data": mapped_data
            }
            
        except Exception as e:
            self.logger.error(f"预览模板失败: {str(e)}")
            raise
    
    async def find_matching_templates(
        self,
        alarm_data: Dict[str, Any],
        contact_point_type: Optional[str] = None
    ) -> List[AlertTemplate]:
        """查找匹配的告警模板"""
        try:
            # 获取所有启用的模板
            templates = await self.get_templates(enabled=True, limit=1000)
            
            matching_templates = []
            for template in templates:
                if await self._template_matches_alarm(template, alarm_data, contact_point_type):
                    matching_templates.append(template)
            
            # 按优先级排序
            matching_templates.sort(key=lambda t: t.priority, reverse=True)
            
            return matching_templates
            
        except Exception as e:
            self.logger.error(f"查找匹配模板失败: {str(e)}")
            return []
    
    async def _validate_template_syntax(self, title_template: str, content_template: str):
        """验证模板语法"""
        try:
            # 验证Jinja2语法
            self.jinja_env.parse(title_template)
            self.jinja_env.parse(content_template)
            
            # 检查模板变量
            title_vars = meta.find_undeclared_variables(self.jinja_env.parse(title_template))
            content_vars = meta.find_undeclared_variables(self.jinja_env.parse(content_template))
            
            # 获取推荐的变量列表
            recommended_vars = self._get_recommended_variables()
            
            # 检查是否使用了不推荐的变量
            all_vars = title_vars.union(content_vars)
            unknown_vars = all_vars - recommended_vars
            
            if unknown_vars:
                self.logger.warning(f"模板使用了未知变量: {unknown_vars}")
            
        except TemplateSyntaxError as e:
            raise ValueError(f"模板语法错误: {str(e)}")
        except Exception as e:
            raise ValueError(f"模板验证失败: {str(e)}")
    
    def _render_text_template(self, template_str: str, data: Dict[str, Any]) -> str:
        """渲染文本模板"""
        try:
            template = Template(template_str)
            return template.render(**data)
        except Exception as e:
            self.logger.error(f"模板渲染失败: {str(e)}")
            return template_str  # 返回原始模板
    
    def _apply_field_mapping(
        self, 
        data: Dict[str, Any], 
        field_mapping: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """应用字段映射"""
        if not field_mapping:
            return data
        
        mapped_data = data.copy()
        
        # 应用字段重命名
        renames = field_mapping.get("renames", {})
        for old_key, new_key in renames.items():
            if old_key in mapped_data:
                mapped_data[new_key] = mapped_data.pop(old_key)
        
        # 应用字段转换
        transforms = field_mapping.get("transforms", {})
        for field, transform_rule in transforms.items():
            if field in mapped_data:
                mapped_data[field] = self._apply_field_transform(
                    mapped_data[field], transform_rule
                )
        
        # 添加计算字段
        computed = field_mapping.get("computed", {})
        for field, expression in computed.items():
            try:
                # 简单的表达式计算
                mapped_data[field] = eval(expression, {"__builtins__": {}}, mapped_data)
            except Exception as e:
                self.logger.warning(f"计算字段 {field} 失败: {str(e)}")
        
        return mapped_data
    
    def _apply_field_transform(self, value: Any, transform_rule: Dict[str, Any]) -> Any:
        """应用字段转换规则"""
        transform_type = transform_rule.get("type")
        
        if transform_type == "upper":
            return str(value).upper()
        elif transform_type == "lower":
            return str(value).lower()
        elif transform_type == "format":
            format_str = transform_rule.get("format", "{}")
            return format_str.format(value)
        elif transform_type == "regex":
            pattern = transform_rule.get("pattern")
            replacement = transform_rule.get("replacement", "")
            return re.sub(pattern, replacement, str(value))
        elif transform_type == "mapping":
            mapping = transform_rule.get("mapping", {})
            return mapping.get(str(value), value)
        
        return value
    
    async def _template_matches_alarm(
        self,
        template: AlertTemplate,
        alarm_data: Dict[str, Any],
        contact_point_type: Optional[str]
    ) -> bool:
        """检查模板是否匹配告警"""
        # 检查联络点类型
        if contact_point_type and template.contact_point_types:
            if contact_point_type not in template.contact_point_types:
                return False
        
        # 检查严重程度过滤
        if template.severity_filter:
            alarm_severity = alarm_data.get("severity")
            if alarm_severity not in template.severity_filter:
                return False
        
        # 检查来源过滤
        if template.source_filter:
            alarm_source = alarm_data.get("source")
            if alarm_source not in template.source_filter:
                return False
        
        # 检查自定义条件
        if template.conditions:
            if not self._evaluate_conditions(template.conditions, alarm_data):
                return False
        
        return True
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], alarm_data: Dict[str, Any]) -> bool:
        """评估自定义条件"""
        try:
            condition_type = conditions.get("type", "and")
            rules = conditions.get("rules", [])
            
            if condition_type == "and":
                return all(self._evaluate_single_condition(rule, alarm_data) for rule in rules)
            elif condition_type == "or":
                return any(self._evaluate_single_condition(rule, alarm_data) for rule in rules)
            
            return True
            
        except Exception as e:
            self.logger.warning(f"条件评估失败: {str(e)}")
            return True
    
    def _evaluate_single_condition(self, rule: Dict[str, Any], alarm_data: Dict[str, Any]) -> bool:
        """评估单个条件"""
        field = rule.get("field")
        operator = rule.get("operator")
        value = rule.get("value")
        
        if not field or not operator:
            return True
        
        alarm_value = alarm_data.get(field)
        
        if operator == "equals":
            return alarm_value == value
        elif operator == "not_equals":
            return alarm_value != value
        elif operator == "contains":
            return value in str(alarm_value or "")
        elif operator == "not_contains":
            return value not in str(alarm_value or "")
        elif operator == "regex":
            return bool(re.search(value, str(alarm_value or "")))
        elif operator == "in":
            return alarm_value in (value if isinstance(value, list) else [value])
        elif operator == "not_in":
            return alarm_value not in (value if isinstance(value, list) else [value])
        
        return True
    
    async def _update_usage_stats(self, template_id: int):
        """更新模板使用统计"""
        async with async_session_maker() as db:
            try:
                template = await db.get(AlertTemplate, template_id)
                if template:
                    template.usage_count += 1
                    template.last_used = datetime.utcnow()
                    await db.commit()
            except Exception as e:
                self.logger.warning(f"更新模板使用统计失败: {str(e)}")
    
    def _get_recommended_variables(self) -> set:
        """获取推荐的模板变量"""
        return {
            "id", "source", "title", "description", "severity", "status", "category",
            "host", "service", "environment", "created_at", "updated_at",
            "tags", "metadata", "count", "first_occurrence", "last_occurrence",
            "correlation_id", "is_duplicate", "similarity_score", "system_id"
        }
    
    def _get_default_sample_data(self) -> Dict[str, Any]:
        """获取默认示例数据"""
        return {
            "id": 12345,
            "source": "monitoring-system",
            "title": "高CPU使用率告警",
            "description": "服务器 web-01 的CPU使用率持续超过85%",
            "severity": "high",
            "status": "active",
            "category": "performance",
            "host": "web-01.example.com",
            "service": "nginx",
            "environment": "production",
            "created_at": "2024-06-24 10:30:00",
            "updated_at": "2024-06-24 10:30:00",
            "tags": {"team": "ops", "region": "us-west-1"},
            "metadata": {"cpu_usage": 87.5, "threshold": 85.0},
            "count": 1,
            "first_occurrence": "2024-06-24 10:30:00",
            "last_occurrence": "2024-06-24 10:30:00",
            "correlation_id": None,
            "is_duplicate": False,
            "similarity_score": None,
            "system_id": 1
        }