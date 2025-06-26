"""
告警订阅API接口
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.responses import DataResponse, ListResponse, data_response, list_response
from src.core.exceptions import AlarmSystemException, to_http_exception
from src.models.subscription import (
    SubscriptionCreate, SubscriptionUpdate, NotificationTemplateCreate,
    NotificationChannelCreate, SubscriptionResponse, NotificationResponse,
    NotificationTemplateResponse, SubscriptionType, NotificationStatus
)
from src.services.subscription_service import SubscriptionService
from src.services.notification_service import NotificationService
from src.services.template_service import TemplateService
from src.services.notification_engine import notification_engine

router = APIRouter()


def get_subscription_service() -> SubscriptionService:
    """获取订阅服务实例"""
    return SubscriptionService()


def get_notification_service() -> NotificationService:
    """获取通知服务实例"""
    return NotificationService()


def get_template_service() -> TemplateService:
    """获取模板服务实例"""
    return TemplateService()


def get_current_user_id() -> int:
    """获取当前用户ID（简化版本）"""
    return 1


@router.post("/subscriptions", response_model=DataResponse[SubscriptionResponse])
async def create_subscription(
    subscription_data: SubscriptionCreate,
    service: SubscriptionService = Depends(get_subscription_service),
    current_user: int = Depends(get_current_user_id)
):
    """创建告警订阅"""
    try:
        subscription = await service.create_subscription(current_user, subscription_data)
        response = SubscriptionResponse.from_orm(subscription)
        return data_response(response, "订阅创建成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/subscriptions", response_model=ListResponse[SubscriptionResponse])
async def get_subscriptions(
    enabled_only: bool = Query(True),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    service: SubscriptionService = Depends(get_subscription_service),
    current_user: int = Depends(get_current_user_id)
):
    """获取用户订阅列表"""
    try:
        subscriptions = await service.get_user_subscriptions(
            current_user, enabled_only, limit, offset
        )
        
        responses = [SubscriptionResponse.from_orm(sub) for sub in subscriptions]
        return list_response(responses, len(responses), "获取成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/subscriptions/{subscription_id}", response_model=DataResponse[SubscriptionResponse])
async def get_subscription(
    subscription_id: int,
    service: SubscriptionService = Depends(get_subscription_service),
    current_user: int = Depends(get_current_user_id)
):
    """获取订阅详情"""
    try:
        async with get_db_session() as session:
            subscription = await service._get_subscription_with_permission(
                session, subscription_id, current_user
            )
            response = SubscriptionResponse.from_orm(subscription)
            return data_response(response, "获取成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.put("/subscriptions/{subscription_id}", response_model=DataResponse[SubscriptionResponse])
async def update_subscription(
    subscription_id: int,
    update_data: SubscriptionUpdate,
    service: SubscriptionService = Depends(get_subscription_service),
    current_user: int = Depends(get_current_user_id)
):
    """更新订阅"""
    try:
        subscription = await service.update_subscription(subscription_id, current_user, update_data)
        response = SubscriptionResponse.from_orm(subscription)
        return data_response(response, "订阅更新成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    service: SubscriptionService = Depends(get_subscription_service),
    current_user: int = Depends(get_current_user_id)
):
    """删除订阅"""
    try:
        await service.delete_subscription(subscription_id, current_user)
        return data_response(None, "订阅删除成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.post("/subscriptions/{subscription_id}/test")
async def test_subscription(
    subscription_id: int,
    test_alarm_data: Dict[str, Any],
    service: SubscriptionService = Depends(get_subscription_service),
    current_user: int = Depends(get_current_user_id)
):
    """测试订阅过滤条件"""
    try:
        async with get_db_session() as session:
            subscription = await service._get_subscription_with_permission(
                session, subscription_id, current_user
            )
            
            # 测试过滤条件
            matches = await service.test_subscription_filter(
                subscription.filter_conditions,
                test_alarm_data
            )
            
            return data_response(
                {"matches": matches, "subscription_id": subscription_id},
                "测试完成"
            )
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/notifications", response_model=ListResponse[NotificationResponse])
async def get_notifications(
    days: int = Query(30, ge=1, le=365),
    status_filter: Optional[List[NotificationStatus]] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    service: SubscriptionService = Depends(get_subscription_service),
    current_user: int = Depends(get_current_user_id)
):
    """获取通知历史"""
    try:
        status_list = [s.value for s in status_filter] if status_filter else None
        notifications = await service.get_notification_history(
            current_user, days, status_list, limit, offset
        )
        
        responses = [NotificationResponse.from_orm(notif) for notif in notifications]
        return list_response(responses, len(responses), "获取成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.post("/notifications/{notification_id}/retry")
async def retry_notification(
    notification_id: int,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """重试失败的通知"""
    try:
        success = await notification_service.send_notification(notification_id)
        return data_response(
            {"notification_id": notification_id, "success": success},
            "重试完成"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重试失败: {str(e)}")


@router.get("/notifications/statistics")
async def get_notification_statistics(
    days: int = Query(30, ge=1, le=365),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """获取通知统计信息"""
    try:
        stats = await notification_service.get_notification_statistics(days)
        return data_response(stats, "统计信息获取成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.post("/test-notification")
async def send_test_notification(
    channel_config: Dict[str, Any],
    test_message: str = "这是一条测试通知",
    current_user: int = Depends(get_current_user_id)
):
    """发送测试通知"""
    try:
        success = await notification_engine.send_test_notification(
            current_user, channel_config, test_message
        )
        
        return data_response(
            {"success": success, "message": "测试通知已发送" if success else "测试通知发送失败"},
            "测试完成"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送测试通知失败: {str(e)}")


# 通知模板相关接口

@router.post("/templates", response_model=DataResponse[NotificationTemplateResponse])
async def create_template(
    template_data: NotificationTemplateCreate,
    service: TemplateService = Depends(get_template_service),
    current_user: int = Depends(get_current_user_id)
):
    """创建通知模板"""
    try:
        template = await service.create_template(current_user, template_data)
        response = NotificationTemplateResponse.from_orm(template)
        return data_response(response, "模板创建成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/templates", response_model=ListResponse[NotificationTemplateResponse])
async def get_templates(
    template_type: Optional[str] = Query(None),
    channel_type: Optional[str] = Query(None),
    enabled_only: bool = Query(True),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    service: TemplateService = Depends(get_template_service)
):
    """获取模板列表"""
    try:
        templates = await service.get_templates(
            template_type, channel_type, enabled_only, limit, offset
        )
        
        responses = [NotificationTemplateResponse.from_orm(tpl) for tpl in templates]
        return list_response(responses, len(responses), "获取成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.post("/templates/{template_id}/test")
async def test_template(
    template_id: int,
    test_data: Dict[str, Any],
    service: TemplateService = Depends(get_template_service)
):
    """测试模板渲染"""
    try:
        result = await service.test_template_rendering(template_id, test_data)
        return data_response(result, "模板测试成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/templates/variables")
async def get_template_variables(
    service: TemplateService = Depends(get_template_service)
):
    """获取可用的模板变量"""
    try:
        variables = await service.get_available_variables()
        return data_response(variables, "获取成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取变量失败: {str(e)}")


# 引擎状态和管理接口

@router.get("/engine/status")
async def get_engine_status():
    """获取通知引擎状态"""
    try:
        status = await notification_engine.get_engine_status()
        return data_response(status, "获取成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取引擎状态失败: {str(e)}")


# 枚举值接口

@router.get("/enums/subscription-types")
async def get_subscription_types():
    """获取订阅类型选项"""
    options = [
        {"value": stype.value, "label": stype.value, "description": ""}
        for stype in SubscriptionType
    ]
    return data_response(options, "获取成功")


@router.get("/enums/notification-status")
async def get_notification_status_options():
    """获取通知状态选项"""
    options = [
        {"value": status.value, "label": status.value}
        for status in NotificationStatus
    ]
    return data_response(options, "获取成功")


@router.get("/filter-examples")
async def get_filter_examples():
    """获取过滤条件示例"""
    examples = [
        {
            "name": "严重程度过滤",
            "description": "只接收高级别告警",
            "filter": {
                "field": "severity",
                "operator": "in",
                "value": ["critical", "high"]
            }
        },
        {
            "name": "服务过滤",
            "description": "只接收特定服务的告警",
            "filter": {
                "field": "service",
                "operator": "equals",
                "value": "web-server"
            }
        },
        {
            "name": "环境过滤",
            "description": "只接收生产环境告警",
            "filter": {
                "field": "environment",
                "operator": "equals",
                "value": "production"
            }
        },
        {
            "name": "组合条件",
            "description": "生产环境的高级别告警",
            "filter": {
                "and": [
                    {
                        "field": "environment",
                        "operator": "equals",
                        "value": "production"
                    },
                    {
                        "field": "severity",
                        "operator": "in",
                        "value": ["critical", "high"]
                    }
                ]
            }
        },
        {
            "name": "标题关键词过滤",
            "description": "包含特定关键词的告警",
            "filter": {
                "field": "title",
                "operator": "contains",
                "value": "数据库"
            }
        }
    ]
    
    return data_response(examples, "获取成功")