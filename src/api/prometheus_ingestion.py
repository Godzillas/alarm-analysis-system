"""
Prometheus AlertManager 告警接入 API 路由
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse

from src.adapters.prometheus import PrometheusAdapter
from src.adapters.prometheus_webhook import PrometheusWebhookAdapter
from src.services.collector import AlarmCollector
from src.services.endpoint_manager import endpoint_manager
from src.core.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prometheus", tags=["prometheus"])

# 全局实例
prometheus_adapter = PrometheusAdapter()
prometheus_webhook_adapter = PrometheusWebhookAdapter()
collector = AlarmCollector()


@router.post("/webhook", summary="Prometheus AlertManager Webhook 接入")
async def receive_prometheus_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    接收 Prometheus AlertManager Webhook 告警
    支持标准 AlertManager webhook 格式
    """
    try:
        # 获取原始数据
        raw_data = await request.json()
        logger.info(f"Received Prometheus webhook: {len(raw_data.get('alerts', []))} alerts")
        
        # 验证数据格式
        if not prometheus_adapter.validate_data(raw_data):
            logger.error(f"Invalid Prometheus webhook data: {raw_data}")
            raise HTTPException(status_code=400, detail="Invalid Prometheus AlertManager webhook data format")
        
        # 解析告警
        alarm_data = prometheus_adapter.parse_alarm(raw_data)
        
        # 收集告警
        success = await collector.collect_alarm(alarm_data)
        
        if success:
            logger.info(f"Successfully processed Prometheus alarm: {alarm_data.title}")
            return JSONResponse(
                status_code=200,
                content={"status": "success", "message": "Prometheus alarm processed successfully"}
            )
        else:
            logger.error(f"Failed to process Prometheus alarm: {alarm_data.title}")
            raise HTTPException(status_code=500, detail="Failed to process Prometheus alarm")
            
    except ValueError as e:
        logger.error(f"Prometheus webhook validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prometheus webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook/batch", summary="Prometheus 批量 Webhook 接入")
async def receive_prometheus_webhook_batch(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    接收 Prometheus 批量 Webhook 告警
    处理包含多个告警的 AlertManager 通知
    """
    try:
        # 获取原始数据
        raw_data = await request.json()
        alerts = raw_data.get("alerts", [])
        logger.info(f"Received Prometheus batch webhook: {len(alerts)} alerts")
        
        # 验证数据格式
        if not prometheus_adapter.validate_data(raw_data):
            logger.error(f"Invalid Prometheus batch webhook data: {raw_data}")
            raise HTTPException(status_code=400, detail="Invalid Prometheus AlertManager webhook data format")
        
        # 处理所有告警
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
                alarm_data = prometheus_adapter.parse_alarm(single_alert_data)
                success = await collector.collect_alarm(alarm_data)
                
                if success:
                    processed_count += 1
                    logger.info(f"Processed Prometheus alert: {alarm_data.title}")
                else:
                    failed_count += 1
                    logger.error(f"Failed to process Prometheus alert: {alarm_data.title}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing Prometheus alert: {str(e)}")
        
        # 返回处理结果
        result = {
            "status": "success" if failed_count == 0 else "partial",
            "processed": processed_count,
            "failed": failed_count,
            "total": len(alerts),
            "message": f"Processed {processed_count}/{len(alerts)} Prometheus alerts"
        }
        
        logger.info(f"Prometheus batch processing result: {result}")
        return JSONResponse(status_code=200, content=result)
        
    except ValueError as e:
        logger.error(f"Prometheus batch webhook validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prometheus batch webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook/{endpoint_token}", summary="Prometheus 指定接入点 Webhook")
async def receive_prometheus_webhook_endpoint(
    endpoint_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    通过指定接入点接收 Prometheus Webhook 告警
    支持接入点级别的配置和统计
    """
    try:
        # 验证接入点
        endpoint = await endpoint_manager.get_endpoint_by_token(endpoint_token)
        if not endpoint:
            logger.warning(f"Invalid endpoint token for Prometheus webhook: {endpoint_token}")
            raise HTTPException(status_code=401, detail="Invalid endpoint token")
        
        if not endpoint.enabled:
            logger.warning(f"Disabled endpoint accessed for Prometheus webhook: {endpoint_token}")
            raise HTTPException(status_code=403, detail="Endpoint is disabled")
        
        # 获取原始数据
        raw_data = await request.json()
        logger.info(f"Received Prometheus webhook for endpoint {endpoint.name}: {len(raw_data.get('alerts', []))} alerts")
        
        # 验证数据格式
        if not prometheus_adapter.validate_data(raw_data):
            logger.error(f"Invalid Prometheus webhook data for endpoint {endpoint.name}: {raw_data}")
            raise HTTPException(status_code=400, detail="Invalid Prometheus AlertManager webhook data format")
        
        # 通过接入点处理告警
        success = await endpoint_manager.process_incoming_alarm(endpoint.id, raw_data)
        
        # 更新接入点统计
        await endpoint_manager.update_endpoint_stats(endpoint.id, 1)
        
        if success:
            logger.info(f"Successfully processed Prometheus alarm via endpoint {endpoint.name}")
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success", 
                    "message": f"Prometheus alarm processed via endpoint {endpoint.name}",
                    "endpoint": endpoint.name
                }
            )
        else:
            logger.error(f"Failed to process Prometheus alarm via endpoint {endpoint.name}")
            raise HTTPException(status_code=500, detail="Failed to process Prometheus alarm")
            
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Prometheus endpoint webhook validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prometheus endpoint webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook/simple", summary="简化 Prometheus Webhook 接入")
async def receive_prometheus_simple_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    接收简化的 Prometheus Webhook 告警
    使用专用的简化适配器处理
    """
    try:
        # 获取原始数据
        raw_data = await request.json()
        logger.info(f"Received Prometheus simple webhook: {raw_data}")
        
        # 使用简化适配器验证数据格式
        if not prometheus_webhook_adapter.validate_data(raw_data):
            logger.error(f"Invalid Prometheus simple webhook data: {raw_data}")
            raise HTTPException(status_code=400, detail="Invalid Prometheus simple webhook data format")
        
        # 解析告警
        alarm_data = prometheus_webhook_adapter.parse_alarm(raw_data)
        
        # 收集告警
        success = await collector.collect_alarm(alarm_data)
        
        if success:
            logger.info(f"Successfully processed Prometheus simple alarm: {alarm_data.title}")
            return JSONResponse(
                status_code=200,
                content={"status": "success", "message": "Prometheus simple alarm processed successfully"}
            )
        else:
            logger.error(f"Failed to process Prometheus simple alarm: {alarm_data.title}")
            raise HTTPException(status_code=500, detail="Failed to process Prometheus simple alarm")
            
    except ValueError as e:
        logger.error(f"Prometheus simple webhook validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prometheus simple webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/test", summary="测试 Prometheus 连接")
async def test_prometheus_connection():
    """
    测试 Prometheus 连接和配置
    """
    try:
        # 返回 Prometheus 适配器状态
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "adapter": "prometheus",
                "version": "alertmanager",
                "supported_formats": [
                    "Prometheus AlertManager Webhook",
                    "Prometheus Simple Webhook"
                ],
                "endpoints": {
                    "webhook": "/api/prometheus/webhook",
                    "batch": "/api/prometheus/webhook/batch",
                    "simple": "/api/prometheus/webhook/simple",
                    "endpoint_specific": "/api/prometheus/webhook/{endpoint_token}"
                }
            }
        )
    except Exception as e:
        logger.error(f"Prometheus connection test error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/validate", summary="验证 Prometheus 数据格式")
async def validate_prometheus_data(data: Dict[str, Any]):
    """
    验证 Prometheus 告警数据格式
    用于测试和调试
    """
    try:
        # 尝试标准格式验证
        is_valid_standard = prometheus_adapter.validate_data(data)
        is_valid_simple = prometheus_webhook_adapter.validate_data(data)
        
        if is_valid_standard:
            # 尝试解析标准格式
            try:
                parsed = prometheus_adapter.parse_alarm(data)
                return JSONResponse(
                    status_code=200,
                    content={
                        "valid": True,
                        "format": "prometheus_alertmanager",
                        "title": parsed.title,
                        "severity": parsed.severity,
                        "status": parsed.status,
                        "alerts_count": len(data.get("alerts", [])),
                        "message": "Valid Prometheus AlertManager data"
                    }
                )
            except Exception as parse_error:
                return JSONResponse(
                    status_code=200,
                    content={
                        "valid": False,
                        "format": "prometheus_alertmanager",
                        "error": str(parse_error),
                        "message": "Data structure valid but parsing failed"
                    }
                )
        elif is_valid_simple:
            # 尝试解析简化格式
            try:
                parsed = prometheus_webhook_adapter.parse_alarm(data)
                return JSONResponse(
                    status_code=200,
                    content={
                        "valid": True,
                        "format": "prometheus_simple",
                        "title": parsed.title,
                        "severity": parsed.severity,
                        "status": parsed.status,
                        "message": "Valid Prometheus simple webhook data"
                    }
                )
            except Exception as parse_error:
                return JSONResponse(
                    status_code=200,
                    content={
                        "valid": False,
                        "format": "prometheus_simple",
                        "error": str(parse_error),
                        "message": "Data structure valid but parsing failed"
                    }
                )
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "valid": False,
                    "format": "prometheus",
                    "message": "Invalid Prometheus alarm data format (neither AlertManager nor simple format)"
                }
            )
            
    except Exception as e:
        logger.error(f"Prometheus data validation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/metrics", summary="Prometheus 指标端点")
async def prometheus_metrics():
    """
    提供 Prometheus 格式的指标
    供 Prometheus 抓取系统运行状态
    """
    try:
        # 这里可以实现 Prometheus 指标输出
        # 暂时返回基本信息
        metrics = [
            "# HELP alarm_system_status System status",
            "# TYPE alarm_system_status gauge", 
            "alarm_system_status{component=\"prometheus_ingestion\"} 1",
            "",
            "# HELP alarm_processed_total Total processed alarms",
            "# TYPE alarm_processed_total counter",
            "alarm_processed_total{source=\"prometheus\"} 0",
            ""
        ]
        
        return "\n".join(metrics)
        
    except Exception as e:
        logger.error(f"Prometheus metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")