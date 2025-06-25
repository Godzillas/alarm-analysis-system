"""
告警模板管理API路由
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.models.alarm import (
    AlertTemplate, AlertTemplateCreate, AlertTemplateUpdate, AlertTemplateResponse,
    AlertTemplateCategory, TemplateType, PaginatedResponse
)
from src.services.alert_template_manager import AlertTemplateManager
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# 全局服务实例
template_manager = None


def get_template_manager():
    global template_manager
    if template_manager is None:
        template_manager = AlertTemplateManager()
    return template_manager


@router.get("/", response_model=PaginatedResponse[AlertTemplateResponse])
async def get_alert_templates(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    system_id: Optional[int] = Query(None, description="系统ID过滤"),
    category: Optional[AlertTemplateCategory] = Query(None, description="模板分类过滤"),
    template_type: Optional[TemplateType] = Query(None, description="模板类型过滤"),
    enabled: Optional[bool] = Query(None, description="启用状态过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db_session)
):
    """获取告警模板列表"""
    try:
        manager = get_template_manager()
        
        # 计算偏移量
        skip = (page - 1) * page_size
        
        # 获取模板列表
        templates = await manager.get_templates(
            system_id=system_id,
            category=category,
            template_type=template_type,
            enabled=enabled,
            skip=skip,
            limit=page_size
        )
        
        # 如果有搜索条件，在内存中过滤
        if search:
            search_lower = search.lower()
            templates = [
                t for t in templates 
                if search_lower in t.name.lower() or 
                   (t.description and search_lower in t.description.lower())
            ]
        
        # 计算总数
        total = len(templates)
        pages = (total + page_size - 1) // page_size
        
        return PaginatedResponse(
            data=[AlertTemplateResponse.model_validate(t) for t in templates],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"获取告警模板列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取告警模板列表失败")


@router.post("/", response_model=AlertTemplateResponse)
async def create_alert_template(
    template_data: AlertTemplateCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """创建告警模板"""
    try:
        manager = get_template_manager()
        
        template = await manager.create_template(
            name=template_data.name,
            category=template_data.category,
            template_type=template_data.template_type,
            title_template=template_data.title_template,
            content_template=template_data.content_template,
            summary_template=template_data.summary_template,
            template_config=template_data.template_config,
            field_mapping=template_data.field_mapping,
            conditions=template_data.conditions,
            contact_point_types=template_data.contact_point_types,
            severity_filter=template_data.severity_filter,
            source_filter=template_data.source_filter,
            system_id=template_data.system_id,
            description=template_data.description,
            enabled=template_data.enabled,
            priority=template_data.priority
        )
        
        logger.info(f"创建告警模板成功: {template.name}")
        return AlertTemplateResponse.model_validate(template)
        
    except ValueError as e:
        logger.warning(f"创建告警模板参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建告警模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建告警模板失败")


@router.get("/{template_id}", response_model=AlertTemplateResponse)
async def get_alert_template(
    template_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """获取告警模板详情"""
    try:
        manager = get_template_manager()
        template = await manager.get_template_by_id(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="告警模板不存在")
        
        return AlertTemplateResponse.model_validate(template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取告警模板详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取告警模板详情失败")


@router.put("/{template_id}", response_model=AlertTemplateResponse)
async def update_alert_template(
    template_id: int,
    template_data: AlertTemplateUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """更新告警模板"""
    try:
        manager = get_template_manager()
        
        # 过滤掉None值
        update_data = template_data.model_dump(exclude_unset=True)
        
        template = await manager.update_template(template_id, **update_data)
        
        logger.info(f"更新告警模板成功: {template.name}")
        return AlertTemplateResponse.model_validate(template)
        
    except ValueError as e:
        logger.warning(f"更新告警模板参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新告警模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新告警模板失败")


@router.delete("/{template_id}")
async def delete_alert_template(
    template_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """删除告警模板"""
    try:
        manager = get_template_manager()
        await manager.delete_template(template_id)
        
        logger.info(f"删除告警模板成功: ID {template_id}")
        return {"message": "删除成功"}
        
    except ValueError as e:
        logger.warning(f"删除告警模板参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"删除告警模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除告警模板失败")


@router.post("/{template_id}/render")
async def render_alert_template(
    template_id: int,
    alarm_data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session)
):
    """渲染告警模板"""
    try:
        manager = get_template_manager()
        result = await manager.render_template(template_id, alarm_data)
        
        logger.info(f"渲染告警模板成功: ID {template_id}")
        return result
        
    except ValueError as e:
        logger.warning(f"渲染告警模板参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"渲染告警模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="渲染告警模板失败")


@router.post("/preview")
async def preview_alert_template(
    preview_data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session)
):
    """预览告警模板"""
    try:
        manager = get_template_manager()
        
        title_template = preview_data.get("title_template", "")
        content_template = preview_data.get("content_template", "")
        summary_template = preview_data.get("summary_template")
        sample_data = preview_data.get("sample_data")
        field_mapping = preview_data.get("field_mapping")
        
        result = await manager.preview_template(
            title_template=title_template,
            content_template=content_template,
            summary_template=summary_template,
            sample_data=sample_data,
            field_mapping=field_mapping
        )
        
        logger.info("预览告警模板成功")
        return result
        
    except Exception as e:
        logger.error(f"预览告警模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"预览告警模板失败: {str(e)}")


@router.post("/find-matching")
async def find_matching_templates(
    alarm_data: Dict[str, Any] = Body(...),
    contact_point_type: Optional[str] = Query(None, description="联络点类型"),
    db: AsyncSession = Depends(get_db_session)
):
    """查找匹配的告警模板"""
    try:
        manager = get_template_manager()
        templates = await manager.find_matching_templates(alarm_data, contact_point_type)
        
        return {
            "templates": [AlertTemplateResponse.model_validate(t) for t in templates],
            "count": len(templates)
        }
        
    except Exception as e:
        logger.error(f"查找匹配模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="查找匹配模板失败")


@router.get("/categories/", response_model=List[dict])
async def get_template_categories():
    """获取模板分类列表"""
    try:
        categories = []
        for category in AlertTemplateCategory:
            category_info = {
                "value": category.value,
                "label": _get_category_label(category),
                "description": _get_category_description(category)
            }
            categories.append(category_info)
        
        return categories
        
    except Exception as e:
        logger.error(f"获取模板分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取模板分类失败")


@router.get("/types/", response_model=List[dict])
async def get_template_types():
    """获取模板类型列表"""
    try:
        types = []
        for template_type in TemplateType:
            type_info = {
                "value": template_type.value,
                "label": _get_type_label(template_type),
                "description": _get_type_description(template_type)
            }
            types.append(type_info)
        
        return types
        
    except Exception as e:
        logger.error(f"获取模板类型失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取模板类型失败")


@router.get("/variables/", response_model=Dict[str, Any])
async def get_template_variables():
    """获取可用的模板变量"""
    try:
        manager = get_template_manager()
        
        variables = {
            "alarm_fields": [
                {"name": "id", "type": "integer", "description": "告警ID"},
                {"name": "source", "type": "string", "description": "告警来源"},
                {"name": "title", "type": "string", "description": "告警标题"},
                {"name": "description", "type": "string", "description": "告警描述"},
                {"name": "severity", "type": "string", "description": "严重程度"},
                {"name": "status", "type": "string", "description": "告警状态"},
                {"name": "category", "type": "string", "description": "告警分类"},
                {"name": "host", "type": "string", "description": "主机名"},
                {"name": "service", "type": "string", "description": "服务名"},
                {"name": "environment", "type": "string", "description": "环境"},
                {"name": "created_at", "type": "datetime", "description": "创建时间"},
                {"name": "updated_at", "type": "datetime", "description": "更新时间"},
                {"name": "tags", "type": "object", "description": "标签"},
                {"name": "metadata", "type": "object", "description": "元数据"},
                {"name": "count", "type": "integer", "description": "告警次数"}
            ],
            "functions": [
                {"name": "now()", "description": "当前时间"},
                {"name": "date(value)", "description": "格式化日期"},
                {"name": "upper(value)", "description": "转换为大写"},
                {"name": "lower(value)", "description": "转换为小写"},
                {"name": "length(value)", "description": "获取长度"}
            ],
            "sample_data": manager._get_default_sample_data()
        }
        
        return variables
        
    except Exception as e:
        logger.error(f"获取模板变量失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取模板变量失败")


def _get_category_label(category: AlertTemplateCategory) -> str:
    """获取分类显示名称"""
    labels = {
        AlertTemplateCategory.SYSTEM: "系统",
        AlertTemplateCategory.APPLICATION: "应用",
        AlertTemplateCategory.NETWORK: "网络",
        AlertTemplateCategory.SECURITY: "安全",
        AlertTemplateCategory.PERFORMANCE: "性能",
        AlertTemplateCategory.CUSTOM: "自定义"
    }
    return labels.get(category, category.value)


def _get_category_description(category: AlertTemplateCategory) -> str:
    """获取分类描述"""
    descriptions = {
        AlertTemplateCategory.SYSTEM: "系统级别告警模板",
        AlertTemplateCategory.APPLICATION: "应用程序告警模板",
        AlertTemplateCategory.NETWORK: "网络相关告警模板",
        AlertTemplateCategory.SECURITY: "安全事件告警模板",
        AlertTemplateCategory.PERFORMANCE: "性能监控告警模板",
        AlertTemplateCategory.CUSTOM: "用户自定义告警模板"
    }
    return descriptions.get(category, "")


def _get_type_label(template_type: TemplateType) -> str:
    """获取类型显示名称"""
    labels = {
        TemplateType.SIMPLE: "简单文本",
        TemplateType.RICH: "富文本",
        TemplateType.MARKDOWN: "Markdown",
        TemplateType.HTML: "HTML",
        TemplateType.JSON: "JSON"
    }
    return labels.get(template_type, template_type.value)


def _get_type_description(template_type: TemplateType) -> str:
    """获取类型描述"""
    descriptions = {
        TemplateType.SIMPLE: "纯文本格式，适用于邮件和短信",
        TemplateType.RICH: "富文本格式，支持样式和格式化",
        TemplateType.MARKDOWN: "Markdown格式，支持标记语法",
        TemplateType.HTML: "HTML格式，支持完整的HTML标记",
        TemplateType.JSON: "JSON格式，适用于API和Webhook"
    }
    return descriptions.get(template_type, "")