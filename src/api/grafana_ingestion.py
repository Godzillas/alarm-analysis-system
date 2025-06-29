"""
Grafana 告警接入 API 路由
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse

from src.adapters.grafana import GrafanaAdapter
from src.services.collector import AlarmCollector
from src.services.endpoint_manager import endpoint_manager
from src.core.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/grafana", tags=["grafana"])

# 全局实例
grafana_adapter = GrafanaAdapter()
collector = AlarmCollector()


@router.post("/webhook", summary="Grafana Webhook 接入")
async def receive_grafana_webhook(
    request: Request
):
    """
    接收 Grafana Webhook 告警
    支持 Grafana 8+ 统一告警和传统告警格式
    """
    try:
        # 获取原始数据
        raw_data = await request.json()
        logger.info(f"Received Grafana webhook: {raw_data}")
        
        # 验证数据格式
        if not grafana_adapter.validate_data(raw_data):
            logger.error(f"Invalid Grafana webhook data: {raw_data}")
            raise HTTPException(status_code=400, detail="Invalid Grafana webhook data format")
        
        # 解析告警
        alarm_data = grafana_adapter.parse_alarm(raw_data)
        
        # 收集告警
        success = await collector.collect_alarm(alarm_data)
        
        if success:
            logger.info(f"Successfully processed Grafana alarm: {alarm_data.title}")
            return JSONResponse(
                status_code=200,
                content={"status": "success", "message": "Grafana alarm processed successfully"}
            )
        else:
            logger.error(f"Failed to process Grafana alarm: {alarm_data.title}")
            raise HTTPException(status_code=500, detail="Failed to process Grafana alarm")
            
    except ValueError as e:
        logger.error(f"Grafana webhook validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Grafana webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook/batch", summary="Grafana 批量 Webhook 接入")
async def receive_grafana_webhook_batch(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    接收 Grafana 批量 Webhook 告警
    处理包含多个告警的 Grafana 通知
    """
    try:
        # 获取原始数据
        raw_data = await request.json()
        logger.info(f"Received Grafana batch webhook: {len(raw_data.get('alerts', []))} alerts")
        
        # 验证数据格式
        if not grafana_adapter.validate_data(raw_data):
            logger.error(f"Invalid Grafana batch webhook data: {raw_data}")
            raise HTTPException(status_code=400, detail="Invalid Grafana webhook data format")
        
        # 处理所有告警
        alerts = raw_data.get("alerts", [])
        processed_count = 0
        failed_count = 0
        
        for alert in alerts:
            try:
                # 为每个告警创建单独的数据结构
                single_alert_data = {
                    **raw_data,
                    "alerts": [alert]  # 只包含当前告警
                }
                
                # 解析并收集告警
                alarm_data = grafana_adapter.parse_alarm(single_alert_data)
                success = await collector.collect_alarm(alarm_data)
                
                if success:
                    processed_count += 1
                    logger.info(f"Processed Grafana alert: {alarm_data.title}")
                else:
                    failed_count += 1
                    logger.error(f"Failed to process Grafana alert: {alarm_data.title}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing Grafana alert: {str(e)}")
        
        # 返回处理结果
        result = {
            "status": "success" if failed_count == 0 else "partial",
            "processed": processed_count,
            "failed": failed_count,
            "total": len(alerts),
            "message": f"Processed {processed_count}/{len(alerts)} Grafana alerts"
        }
        
        logger.info(f"Grafana batch processing result: {result}")
        return JSONResponse(status_code=200, content=result)
        
    except ValueError as e:
        logger.error(f"Grafana batch webhook validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Grafana batch webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook/{endpoint_token}", summary="Grafana 指定接入点 Webhook")
async def receive_grafana_webhook_endpoint(
    endpoint_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    通过指定接入点接收 Grafana Webhook 告警
    支持接入点级别的配置和统计
    """
    try:
        # 验证接入点
        endpoint = await endpoint_manager.get_endpoint_by_token(endpoint_token)
        if not endpoint:
            logger.warning(f"Invalid endpoint token for Grafana webhook: {endpoint_token}")
            raise HTTPException(status_code=401, detail="Invalid endpoint token")
        
        if not endpoint.enabled:
            logger.warning(f"Disabled endpoint accessed for Grafana webhook: {endpoint_token}")
            raise HTTPException(status_code=403, detail="Endpoint is disabled")
        
        # 获取原始数据
        raw_data = await request.json()
        logger.info(f"Received Grafana webhook for endpoint {endpoint.name}: {raw_data}")
        
        # 验证数据格式
        if not grafana_adapter.validate_data(raw_data):
            logger.error(f"Invalid Grafana webhook data for endpoint {endpoint.name}: {raw_data}")
            raise HTTPException(status_code=400, detail="Invalid Grafana webhook data format")
        
        # 通过接入点处理告警
        success = await endpoint_manager.process_incoming_alarm(endpoint.id, raw_data)
        
        # 更新接入点统计
        await endpoint_manager.update_endpoint_stats(endpoint.id, 1)
        
        if success:
            logger.info(f"Successfully processed Grafana alarm via endpoint {endpoint.name}")
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success", 
                    "message": f"Grafana alarm processed via endpoint {endpoint.name}",
                    "endpoint": endpoint.name
                }
            )
        else:
            logger.error(f"Failed to process Grafana alarm via endpoint {endpoint.name}")
            raise HTTPException(status_code=500, detail="Failed to process Grafana alarm")
            
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Grafana endpoint webhook validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Grafana endpoint webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/test", summary="测试 Grafana 连接")
async def test_grafana_connection():
    """
    测试 Grafana 连接和配置
    """
    try:
        # 返回 Grafana 适配器状态
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "adapter": "grafana",
                "version": "unified+legacy",
                "supported_formats": [
                    "Grafana 8+ Unified Alerting",
                    "Grafana 7- Legacy Alerting"
                ],
                "endpoints": {
                    "webhook": "/api/grafana/webhook",
                    "batch": "/api/grafana/webhook/batch",
                    "endpoint_specific": "/api/grafana/webhook/{endpoint_token}"
                }
            }
        )
    except Exception as e:
        logger.error(f"Grafana connection test error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/validate", summary="验证 Grafana 数据格式")
async def validate_grafana_data(data: Dict[str, Any]):
    """
    验证 Grafana 告警数据格式
    用于测试和调试
    """
    try:
        is_valid = grafana_adapter.validate_data(data)
        
        if is_valid:
            # 尝试解析以获取更多信息
            try:
                parsed = grafana_adapter.parse_alarm(data)
                return JSONResponse(
                    status_code=200,
                    content={
                        "valid": True,
                        "format": "grafana",
                        "title": parsed.title,
                        "severity": parsed.severity,
                        "status": parsed.status,
                        "message": "Valid Grafana alarm data"
                    }
                )
            except Exception as parse_error:
                return JSONResponse(
                    status_code=200,
                    content={
                        "valid": False,
                        "format": "grafana",
                        "error": str(parse_error),
                        "message": "Data structure valid but parsing failed"
                    }
                )
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "valid": False,
                    "format": "grafana",
                    "message": "Invalid Grafana alarm data format"
                }
            )
            
    except Exception as e:
        logger.error(f"Grafana data validation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")