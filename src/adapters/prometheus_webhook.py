"""
Prometheus Webhook告警适配器
用于接收Prometheus/Alertmanager发送的告警
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import HTTPException

from src.models.alarm import AlarmSeverity, AlarmStatus
from src.services.collector import AlarmCollector

logger = logging.getLogger(__name__)

class PrometheusWebhookAdapter:
    """Prometheus Webhook告警适配器"""
    
    def __init__(self, collector: Optional[AlarmCollector] = None):
        self.collector = collector or AlarmCollector()
        self.severity_mapping = {
            'critical': AlarmSeverity.CRITICAL,
            'high': AlarmSeverity.HIGH,
            'warning': AlarmSeverity.MEDIUM,
            'info': AlarmSeverity.INFO,
            'low': AlarmSeverity.LOW
        }
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理Prometheus/Alertmanager webhook数据
        
        Args:
            webhook_data: Webhook载荷数据
            
        Returns:
            处理结果
        """
        try:
            logger.info(f"Received Prometheus webhook: {json.dumps(webhook_data, indent=2)}")
            
            # 检查数据格式
            if 'alerts' not in webhook_data:
                raise ValueError("Invalid webhook format: missing 'alerts' field")
            
            alerts = webhook_data.get('alerts', [])
            processed_count = 0
            failed_count = 0
            
            for alert_data in alerts:
                try:
                    # 转换单个告警
                    alarm_dict = self._convert_alert_to_alarm(alert_data, webhook_data)
                    
                    # Debug: 打印处理的告警数据
                    logger.info(f"Processing alarm data: {json.dumps(alarm_dict, indent=2, default=str)}")
                    
                    # 提交到告警收集器
                    success = await self.collector.collect_alarm_dict(alarm_dict)
                    
                    if success:
                        processed_count += 1
                        logger.info(f"Successfully processed alert: {alarm_dict.get('title', 'Unknown')}")
                    else:
                        failed_count += 1
                        logger.error(f"Failed to process alert: {alarm_dict.get('title', 'Unknown')}")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error processing individual alert: {str(e)}")
                    continue
            
            result = {
                'status': 'success',
                'message': 'Prometheus webhook processed',
                'total_alerts': len(alerts),
                'processed': processed_count,
                'failed': failed_count
            }
            
            logger.info(f"Webhook processing completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing Prometheus webhook: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Webhook processing failed: {str(e)}")
    
    def _convert_alert_to_alarm(self, alert_data: Dict[str, Any], webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将Prometheus告警数据转换为系统告警格式
        
        Args:
            alert_data: 单个告警数据
            webhook_data: 完整webhook数据
            
        Returns:
            转换后的告警数据
        """
        labels = alert_data.get('labels', {})
        annotations = alert_data.get('annotations', {})
        
        # 提取基本信息
        alert_name = labels.get('alertname', 'Unknown')
        instance = labels.get('instance', 'unknown')
        job = labels.get('job', 'unknown')
        severity = labels.get('severity', 'warning')
        
        # 构造标题和描述
        title = annotations.get('summary', f"{alert_name} - {instance}")
        description = annotations.get('description', 
                                   f"Alert {alert_name} triggered on {instance}")
        
        # 确定告警状态
        status = AlarmStatus.ACTIVE
        if alert_data.get('status') == 'resolved':
            status = AlarmStatus.RESOLVED
        
        # 解析时间
        starts_at = alert_data.get('startsAt')
        ends_at = alert_data.get('endsAt')
        
        # 提取环境和服务信息
        service = labels.get('service', labels.get('job', 'prometheus'))
        environment = labels.get('environment', labels.get('env', 'production'))
        
        # 构造告警数据
        alarm_dict = {
            'title': title,
            'description': description,
            'severity': self.severity_mapping.get(severity, AlarmSeverity.MEDIUM),
            'status': status,
            'source': 'prometheus',
            'source_id': alert_data.get('fingerprint', f"{alert_name}_{instance}"),
            'host': instance.split(':')[0] if ':' in instance else instance,
            'service': service,
            'environment': environment,
            'tags': {
                'source': 'prometheus',
                'alertname': alert_name,
                'severity': severity,
                'job': job,
                'alert_type': labels.get('alert_type', 'unknown')
            },
            'metadata': {
                'prometheus_alert': alert_data,
                'webhook_data': {
                    'receiver': webhook_data.get('receiver'),
                    'status': webhook_data.get('status'),
                    'externalURL': webhook_data.get('externalURL'),
                    'version': webhook_data.get('version'),
                    'groupKey': webhook_data.get('groupKey')
                },
                'labels': {
                    'alertname': alert_name,
                    'job': job,
                    'instance': instance,
                    'severity': severity,
                    **labels  # 包含所有原始标签
                }
            }
        }
        
        # 处理时间信息
        if starts_at:
            try:
                # Prometheus时间格式: 2025-06-24T11:21:14.774Z
                alarm_dict['created_at'] = datetime.fromisoformat(
                    starts_at.replace('Z', '+00:00')
                ).isoformat()
            except Exception as e:
                logger.warning(f"Failed to parse startsAt time {starts_at}: {e}")
        
        if ends_at and status == AlarmStatus.RESOLVED:
            try:
                alarm_dict['resolved_at'] = datetime.fromisoformat(
                    ends_at.replace('Z', '+00:00')
                ).isoformat()
            except Exception as e:
                logger.warning(f"Failed to parse endsAt time {ends_at}: {e}")
        
        # 添加Prometheus特定的元数据
        if 'generatorURL' in alert_data:
            alarm_dict['external_url'] = alert_data['generatorURL']
        
        # 设置系统ID（这里可以根据标签或服务名来确定）
        system_id = self._determine_system_id(labels, service)
        if system_id:
            alarm_dict['system_id'] = system_id
        
        return alarm_dict
    
    def _determine_system_id(self, labels: Dict[str, Any], service: str) -> Optional[int]:
        """
        根据标签和服务名确定系统ID
        
        Args:
            labels: Prometheus标签
            service: 服务名
            
        Returns:
            系统ID或None
        """
        # 简单的映射规则，可以根据实际需求调整
        service_to_system = {
            'prometheus': 1,    # 监控系统
            'node': 1,          # 基础设施
            'alarm-system': 1,  # 告警系统自身
        }
        
        # 也可以通过标签中的system字段确定
        if 'system' in labels:
            try:
                return int(labels['system'])
            except (ValueError, TypeError):
                pass
        
        # 通过服务名映射
        return service_to_system.get(service)
    
    def create_test_alert(self) -> Dict[str, Any]:
        """
        创建测试告警数据
        
        Returns:
            测试告警数据
        """
        test_webhook = {
            'receiver': 'alarm-system-webhook',
            'status': 'firing',
            'alerts': [
                {
                    'status': 'firing',
                    'labels': {
                        'alertname': 'TestAlert',
                        'instance': 'localhost:9100',
                        'job': 'node',
                        'severity': 'warning',
                        'service': 'system'
                    },
                    'annotations': {
                        'summary': 'Test alert from Prometheus',
                        'description': 'This is a test alert to verify webhook integration'
                    },
                    'startsAt': datetime.utcnow().isoformat() + 'Z',
                    'endsAt': '0001-01-01T00:00:00Z',
                    'generatorURL': 'http://localhost:9090/graph?g0.expr=up%7Bjob%3D%22node%22%7D+%3D%3D+0',
                    'fingerprint': 'test123456'
                }
            ],
            'groupKey': 'test-group',
            'version': '4',
            'externalURL': 'http://localhost:9093'
        }
        
        return test_webhook