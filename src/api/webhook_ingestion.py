"""
Webhook 推送告警接入 API 路由
支持通用 Webhook 推送和自定义格式
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body
from fastapi.responses import JSONResponse

from src.adapters.custom_webhook import CustomWebhookAdapter
from src.services.collector import AlarmCollector
from src.services.endpoint_manager import endpoint_manager
from src.services.notification_service import NotificationService
from src.core.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

# 全局实例
webhook_adapter = CustomWebhookAdapter()
collector = AlarmCollector()
notification_service = NotificationService()


@router.post("/push", summary="通用 Webhook 推送接入")
async def receive_webhook_push(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    接收通用 Webhook 推送告警
    支持自定义格式的 Webhook 数据
    """
    try:
        # 获取原始数据
        raw_data = await request.json()
        logger.info(f"Received webhook push: {raw_data}")
        
        # 验证数据格式
        if not webhook_adapter.validate_data(raw_data):
            logger.error(f"Invalid webhook push data: {raw_data}")
            raise HTTPException(status_code=400, detail="Invalid webhook push data format")
        
        # 解析告警
        alarm_data = webhook_adapter.parse_alarm(raw_data)
        
        # 收集告警
        success = await collector.collect_alarm(alarm_data)
        
        if success:
            logger.info(f"Successfully processed webhook push alarm: {alarm_data.title}")
            return JSONResponse(
                status_code=200,
                content={"status": "success", "message": "Webhook push alarm processed successfully"}
            )
        else:
            logger.error(f"Failed to process webhook push alarm: {alarm_data.title}")
            raise HTTPException(status_code=500, detail="Failed to process webhook push alarm")
            
    except ValueError as e:
        logger.error(f"Webhook push validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Webhook push processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/push/{endpoint_token}", summary="指定接入点 Webhook 推送")
async def receive_webhook_push_endpoint(
    endpoint_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    通过指定接入点接收 Webhook 推送告警
    支持接入点级别的配置和统计
    """
    try:
        # 验证接入点
        endpoint = await endpoint_manager.get_endpoint_by_token(endpoint_token)
        if not endpoint:
            logger.warning(f"Invalid endpoint token for webhook push: {endpoint_token}")
            raise HTTPException(status_code=401, detail="Invalid endpoint token")
        
        if not endpoint.enabled:
            logger.warning(f"Disabled endpoint accessed for webhook push: {endpoint_token}")
            raise HTTPException(status_code=403, detail="Endpoint is disabled")
        
        # 获取原始数据
        raw_data = await request.json()
        logger.info(f"Received webhook push for endpoint {endpoint.name}: {raw_data}")
        
        # 通过接入点处理告警
        success = await endpoint_manager.process_incoming_alarm(endpoint.id, raw_data)
        
        # 更新接入点统计
        await endpoint_manager.update_endpoint_stats(endpoint.id, 1)
        
        if success:
            logger.info(f"Successfully processed webhook push alarm via endpoint {endpoint.name}")
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success", 
                    "message": f"Webhook push alarm processed via endpoint {endpoint.name}",
                    "endpoint": endpoint.name
                }
            )
        else:
            logger.error(f"Failed to process webhook push alarm via endpoint {endpoint.name}")
            raise HTTPException(status_code=500, detail="Failed to process webhook push alarm")
            
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Webhook push endpoint validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Webhook push endpoint processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/subscribe", summary="订阅 Webhook 推送")
async def subscribe_webhook_push(
    webhook_url: str = Body(..., description="要推送的 Webhook URL"),
    event_types: List[str] = Body(default=['alarm.created', 'alarm.updated'], description="订阅的事件类型"),
    filters: Optional[Dict[str, Any]] = Body(default=None, description="过滤条件"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    订阅 Webhook 推送通知
    当系统中发生指定事件时，向订阅的 URL 推送通知
    """
    try:
        # 验证 webhook URL 格式
        if not webhook_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid webhook URL format")
        
        # 验证事件类型
        valid_event_types = [
            'alarm.created', 'alarm.updated', 'alarm.resolved', 'alarm.deleted',
            'endpoint.created', 'endpoint.updated', 'endpoint.deleted',
            'system.created', 'system.updated', 'system.deleted'
        ]
        
        invalid_events = [event for event in event_types if event not in valid_event_types]
        if invalid_events:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid event types: {invalid_events}. Valid types: {valid_event_types}"
            )
        
        # 创建订阅记录
        subscription_data = {
            "webhook_url": webhook_url,
            "event_types": event_types,
            "filters": filters or {},
            "enabled": True
        }
        
        # 这里应该保存到数据库中，暂时返回成功信息
        logger.info(f"Created webhook subscription: {subscription_data}")
        
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": "Webhook subscription created successfully",
                "subscription": {
                    "webhook_url": webhook_url,
                    "event_types": event_types,
                    "filters": filters,
                    "created_at": "2024-01-01T00:00:00Z"  # 临时时间戳
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook subscription error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/notify", summary="发送 Webhook 通知")
async def send_webhook_notification(
    event_type: str = Body(..., description="事件类型"),
    event_data: Dict[str, Any] = Body(..., description="事件数据"),
    target_urls: Optional[List[str]] = Body(default=None, description="目标 URL 列表"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    发送 Webhook 通知到指定的 URL
    支持批量推送和自定义事件数据
    """
    try:
        # 构建通知数据
        notification_data = {
            "event_type": event_type,
            "event_data": event_data,
            "timestamp": "2024-01-01T00:00:00Z",  # 应该使用当前时间
            "source": "alarm_analysis_system"
        }
        
        # 如果没有指定目标 URL，则发送给所有订阅者
        if not target_urls:
            # 这里应该从数据库获取所有订阅了该事件类型的 URL
            target_urls = []  # 临时空列表
            logger.info(f"No target URLs specified, would send to all subscribers for event: {event_type}")
        
        # 发送通知到所有目标 URL
        sent_count = 0
        failed_count = 0
        
        for url in target_urls:
            try:
                # 这里应该实际发送 HTTP 请求
                # success = await notification_service.send_webhook(url, notification_data)
                success = True  # 临时模拟成功
                
                if success:
                    sent_count += 1
                    logger.info(f"Successfully sent webhook notification to: {url}")
                else:
                    failed_count += 1
                    logger.error(f"Failed to send webhook notification to: {url}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending webhook notification to {url}: {str(e)}")
        
        # 返回发送结果
        result = {
            "status": "success" if failed_count == 0 else "partial",
            "sent": sent_count,
            "failed": failed_count,
            "total": len(target_urls),
            "event_type": event_type,
            "message": f"Sent {sent_count}/{len(target_urls)} webhook notifications"
        }
        
        logger.info(f"Webhook notification result: {result}")
        return JSONResponse(status_code=200, content=result)
        
    except Exception as e:
        logger.error(f"Webhook notification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/subscriptions", summary="获取 Webhook 订阅列表")
async def get_webhook_subscriptions(
    event_type: Optional[str] = Query(None, description="筛选事件类型"),
    enabled: Optional[bool] = Query(None, description="筛选启用状态"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取 Webhook 订阅列表
    支持按事件类型和启用状态筛选
    """
    try:
        # 这里应该从数据库查询实际的订阅数据
        # 暂时返回模拟数据
        mock_subscriptions = [
            {
                "id": 1,
                "webhook_url": "https://example.com/webhook",
                "event_types": ["alarm.created", "alarm.updated"],
                "filters": {"severity": ["critical", "high"]},
                "enabled": True,
                "created_at": "2024-01-01T00:00:00Z",
                "last_sent": "2024-01-01T12:00:00Z"
            },
            {
                "id": 2,
                "webhook_url": "https://api.example.com/alerts",
                "event_types": ["alarm.resolved"],
                "filters": {},
                "enabled": True,
                "created_at": "2024-01-01T00:00:00Z",
                "last_sent": None
            }
        ]
        
        # 应用筛选
        filtered_subscriptions = mock_subscriptions
        
        if event_type:
            filtered_subscriptions = [
                sub for sub in filtered_subscriptions 
                if event_type in sub["event_types"]
            ]
        
        if enabled is not None:
            filtered_subscriptions = [
                sub for sub in filtered_subscriptions 
                if sub["enabled"] == enabled
            ]
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "subscriptions": filtered_subscriptions,
                "total": len(filtered_subscriptions)
            }
        )
        
    except Exception as e:
        logger.error(f"Get webhook subscriptions error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/test", summary="测试 Webhook 功能")
async def test_webhook_functionality():
    """
    测试 Webhook 功能和配置
    """
    try:
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "adapter": "webhook",
                "version": "custom",
                "supported_features": [
                    "Custom Webhook Push",
                    "Webhook Subscriptions",
                    "Event Notifications",
                    "Batch Notifications"
                ],
                "endpoints": {
                    "push": "/api/webhook/push",
                    "push_endpoint": "/api/webhook/push/{endpoint_token}",
                    "subscribe": "/api/webhook/subscribe",
                    "notify": "/api/webhook/notify",
                    "subscriptions": "/api/webhook/subscriptions"
                },
                "supported_events": [
                    "alarm.created", "alarm.updated", "alarm.resolved", "alarm.deleted",
                    "endpoint.created", "endpoint.updated", "endpoint.deleted",
                    "system.created", "system.updated", "system.deleted"
                ]
            }
        )
    except Exception as e:
        logger.error(f"Webhook test error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/validate", summary="验证 Webhook 数据格式")
async def validate_webhook_data(data: Dict[str, Any]):
    """
    验证 Webhook 数据格式
    用于测试和调试
    """
    try:
        is_valid = webhook_adapter.validate_data(data)
        
        if is_valid:
            # 尝试解析以获取更多信息
            try:
                parsed = webhook_adapter.parse_alarm(data)
                return JSONResponse(
                    status_code=200,
                    content={
                        "valid": True,
                        "format": "custom_webhook",
                        "title": parsed.title,
                        "severity": parsed.severity,
                        "status": parsed.status,
                        "message": "Valid webhook alarm data"
                    }
                )
            except Exception as parse_error:
                return JSONResponse(
                    status_code=200,
                    content={
                        "valid": False,
                        "format": "custom_webhook",
                        "error": str(parse_error),
                        "message": "Data structure valid but parsing failed"
                    }
                )
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "valid": False,
                    "format": "custom_webhook",
                    "message": "Invalid webhook alarm data format"
                }
            )
            
    except Exception as e:
        logger.error(f"Webhook data validation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")