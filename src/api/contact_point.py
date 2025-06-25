"""
联络点管理API路由
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.models.alarm import (
    ContactPoint, ContactPointCreate, ContactPointUpdate, ContactPointResponse, 
    ContactPointType, PaginatedResponse
)
from src.services.contact_point_manager import ContactPointManager
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# 全局服务实例
contact_point_manager = None


def get_contact_point_manager():
    global contact_point_manager
    if contact_point_manager is None:
        contact_point_manager = ContactPointManager()
    return contact_point_manager


@router.get("/", response_model=PaginatedResponse[ContactPointResponse])
async def get_contact_points(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    system_id: Optional[int] = Query(None, description="系统ID过滤"),
    contact_type: Optional[ContactPointType] = Query(None, description="联络点类型过滤"),
    enabled: Optional[bool] = Query(None, description="启用状态过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db_session)
):
    """获取联络点列表"""
    try:
        manager = get_contact_point_manager()
        
        # 计算偏移量
        skip = (page - 1) * page_size
        
        # 获取联络点列表
        contact_points = await manager.get_contact_points(
            system_id=system_id,
            contact_type=contact_type,
            enabled=enabled,
            skip=skip,
            limit=page_size
        )
        
        # 如果有搜索条件，在内存中过滤（简单实现）
        if search:
            search_lower = search.lower()
            contact_points = [
                cp for cp in contact_points 
                if search_lower in cp.name.lower() or 
                   (cp.description and search_lower in cp.description.lower())
            ]
        
        # 计算总数（这里简化处理，实际应该在数据库层面计算）
        total = len(contact_points)
        pages = (total + page_size - 1) // page_size
        
        return PaginatedResponse(
            data=[ContactPointResponse.model_validate(cp) for cp in contact_points],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"获取联络点列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取联络点列表失败")


@router.post("/", response_model=ContactPointResponse)
async def create_contact_point(
    contact_point_data: ContactPointCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """创建联络点"""
    try:
        manager = get_contact_point_manager()
        
        contact_point = await manager.create_contact_point(
            name=contact_point_data.name,
            contact_type=contact_point_data.contact_type,
            config=contact_point_data.config,
            system_id=contact_point_data.system_id,
            description=contact_point_data.description,
            enabled=contact_point_data.enabled,
            retry_count=contact_point_data.retry_count,
            retry_interval=contact_point_data.retry_interval,
            timeout=contact_point_data.timeout
        )
        
        logger.info(f"创建联络点成功: {contact_point.name}")
        return ContactPointResponse.model_validate(contact_point)
        
    except ValueError as e:
        logger.warning(f"创建联络点参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建联络点失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建联络点失败")


@router.get("/{contact_point_id}", response_model=ContactPointResponse)
async def get_contact_point(
    contact_point_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """获取联络点详情"""
    try:
        manager = get_contact_point_manager()
        contact_point = await manager.get_contact_point_by_id(contact_point_id)
        
        if not contact_point:
            raise HTTPException(status_code=404, detail="联络点不存在")
        
        return ContactPointResponse.model_validate(contact_point)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取联络点详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取联络点详情失败")


@router.put("/{contact_point_id}", response_model=ContactPointResponse)
async def update_contact_point(
    contact_point_id: int,
    contact_point_data: ContactPointUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """更新联络点"""
    try:
        manager = get_contact_point_manager()
        
        # 过滤掉None值
        update_data = contact_point_data.model_dump(exclude_unset=True)
        
        contact_point = await manager.update_contact_point(
            contact_point_id, **update_data
        )
        
        logger.info(f"更新联络点成功: {contact_point.name}")
        return ContactPointResponse.model_validate(contact_point)
        
    except ValueError as e:
        logger.warning(f"更新联络点参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新联络点失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新联络点失败")


@router.delete("/{contact_point_id}")
async def delete_contact_point(
    contact_point_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """删除联络点"""
    try:
        manager = get_contact_point_manager()
        await manager.delete_contact_point(contact_point_id)
        
        logger.info(f"删除联络点成功: ID {contact_point_id}")
        return {"message": "删除成功"}
        
    except ValueError as e:
        logger.warning(f"删除联络点参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"删除联络点失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除联络点失败")


@router.post("/{contact_point_id}/test")
async def test_contact_point(
    contact_point_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """测试联络点"""
    try:
        manager = get_contact_point_manager()
        result = await manager.test_contact_point(contact_point_id)
        
        if result["success"]:
            logger.info(f"联络点测试成功: ID {contact_point_id}")
        else:
            logger.warning(f"联络点测试失败: ID {contact_point_id}, 错误: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"测试联络点失败: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/{contact_point_id}/stats")
async def get_contact_point_stats(
    contact_point_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """获取联络点统计信息"""
    try:
        manager = get_contact_point_manager()
        stats = await manager.get_contact_point_stats(contact_point_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="联络点不存在")
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取联络点统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取联络点统计失败")


@router.get("/types/", response_model=List[dict])
async def get_contact_point_types():
    """获取支持的联络点类型"""
    try:
        types = []
        for contact_type in ContactPointType:
            type_info = {
                "value": contact_type.value,
                "label": _get_type_label(contact_type),
                "description": _get_type_description(contact_type),
                "config_schema": _get_type_config_schema(contact_type)
            }
            types.append(type_info)
        
        return types
        
    except Exception as e:
        logger.error(f"获取联络点类型失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取联络点类型失败")


def _get_type_label(contact_type: ContactPointType) -> str:
    """获取联络点类型显示名称"""
    labels = {
        ContactPointType.EMAIL: "邮件",
        ContactPointType.WEBHOOK: "Webhook",
        ContactPointType.SLACK: "Slack",
        ContactPointType.TEAMS: "Microsoft Teams",
        ContactPointType.FEISHU: "飞书",
        ContactPointType.DINGTALK: "钉钉",
        ContactPointType.SMS: "短信",
        ContactPointType.WECHAT: "企业微信"
    }
    return labels.get(contact_type, contact_type.value)


def _get_type_description(contact_type: ContactPointType) -> str:
    """获取联络点类型描述"""
    descriptions = {
        ContactPointType.EMAIL: "通过SMTP发送邮件通知",
        ContactPointType.WEBHOOK: "通过HTTP/HTTPS发送Webhook通知",
        ContactPointType.SLACK: "发送消息到Slack频道",
        ContactPointType.TEAMS: "发送消息到Microsoft Teams",
        ContactPointType.FEISHU: "发送消息到飞书群聊",
        ContactPointType.DINGTALK: "发送消息到钉钉群聊",
        ContactPointType.SMS: "发送短信通知",
        ContactPointType.WECHAT: "发送消息到企业微信"
    }
    return descriptions.get(contact_type, "")


def _get_type_config_schema(contact_type: ContactPointType) -> dict:
    """获取联络点类型配置模式"""
    schemas = {
        ContactPointType.EMAIL: {
            "required": ["smtp_server", "smtp_port", "username", "password", "to_addresses"],
            "properties": {
                "smtp_server": {"type": "string", "title": "SMTP服务器"},
                "smtp_port": {"type": "integer", "title": "SMTP端口"},
                "username": {"type": "string", "title": "用户名"},
                "password": {"type": "string", "title": "密码", "format": "password"},
                "to_addresses": {"type": "array", "title": "收件人邮箱", "items": {"type": "string"}},
                "from_address": {"type": "string", "title": "发件人邮箱"},
                "use_tls": {"type": "boolean", "title": "使用TLS", "default": True}
            }
        },
        ContactPointType.WEBHOOK: {
            "required": ["url"],
            "properties": {
                "url": {"type": "string", "title": "Webhook URL", "format": "uri"},
                "method": {"type": "string", "title": "HTTP方法", "enum": ["GET", "POST", "PUT", "PATCH"], "default": "POST"},
                "headers": {"type": "object", "title": "HTTP头部"},
                "timeout": {"type": "integer", "title": "超时时间(秒)", "default": 30}
            }
        },
        ContactPointType.FEISHU: {
            "required": ["webhook_url"],
            "properties": {
                "webhook_url": {"type": "string", "title": "飞书Webhook URL", "format": "uri"},
                "msg_type": {"type": "string", "title": "消息类型", "enum": ["text", "rich_text", "interactive"], "default": "rich_text"},
                "timeout": {"type": "integer", "title": "超时时间(秒)", "default": 30}
            }
        }
    }
    
    return schemas.get(contact_type, {"required": [], "properties": {}})