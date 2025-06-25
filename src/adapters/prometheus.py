"""
Prometheus AlertManager 告警适配器
支持解析 Prometheus AlertManager Webhook 告警格式
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .base import BaseAlarmAdapter
from src.models.alarm import AlarmCreate


class PrometheusAdapter(BaseAlarmAdapter):
    """Prometheus AlertManager 告警适配器"""
    
    def __init__(self):
        super().__init__("prometheus")
    
    def validate_data(self, raw_data: Dict[str, Any]) -> bool:
        """验证 Prometheus AlertManager 数据格式"""
        # 检查必要字段
        required_fields = ["alerts", "status"]
        
        for field in required_fields:
            if field not in raw_data:
                return False
        
        # 检查alerts是否为列表且不为空
        alerts = raw_data.get("alerts", [])
        if not isinstance(alerts, list) or len(alerts) == 0:
            return False
        
        # 检查第一个告警的基本结构
        first_alert = alerts[0]
        if not isinstance(first_alert, dict):
            return False
            
        # 检查告警必要字段
        alert_required = ["status", "labels"]
        for field in alert_required:
            if field not in first_alert:
                return False
                
        return True
    
    def parse_alarm(self, raw_data: Dict[str, Any]) -> AlarmCreate:
        """解析 Prometheus AlertManager 告警数据"""
        
        # 获取告警列表
        alerts = raw_data.get("alerts", [])
        if not alerts:
            raise ValueError("No alerts found in Prometheus webhook data")
        
        # 取第一个告警进行处理（批量处理可以后续扩展）
        alert = alerts[0]
        
        # 基础信息
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        
        # 告警名称和描述
        alertname = labels.get("alertname", "Prometheus Alert")
        title = self._build_title(labels, annotations, alertname)
        description = self._build_description(labels, annotations, alert)
        
        # 状态映射
        status = self._map_prometheus_status(alert.get("status", "firing"))
        
        # 严重程度
        severity = self._extract_severity(labels, annotations)
        
        # 提取系统信息
        system_info = self.extract_system_info({"labels": labels, "annotations": annotations})
        
        # 构建标签
        tags = self.merge_tags(
            labels,
            {
                "source": "prometheus",
                "alertname": alertname,
                "status": alert.get("status", ""),
                "generator_url": alert.get("generatorURL", "")
            },
            system_info
        )
        
        # 移除一些可能很长的标签值，放到metadata中
        sensitive_labels = ["__name__", "__alerts_path__", "__alerts_for__"]
        filtered_tags = {k: v for k, v in tags.items() if k not in sensitive_labels}
        
        # 构建元数据
        metadata = {
            "alertname": alertname,
            "generator_url": alert.get("generatorURL", ""),
            "fingerprint": alert.get("fingerprint", ""),
            "starts_at": alert.get("startsAt", ""),
            "ends_at": alert.get("endsAt", ""),
            "prometheus_labels": labels,
            "prometheus_annotations": annotations,
            "receiver": raw_data.get("receiver", ""),
            "external_url": raw_data.get("externalURL", ""),
            "group_key": raw_data.get("groupKey", ""),
            "group_labels": raw_data.get("groupLabels", {}),
            "common_labels": raw_data.get("commonLabels", {}),
            "common_annotations": raw_data.get("commonAnnotations", {})
        }
        
        # 时间信息
        starts_at = self.format_timestamp(alert.get("startsAt"))
        ends_at = self.format_timestamp(alert.get("endsAt"))
        
        # 生成指纹
        fingerprint_data = {
            "title": title,
            "source": "prometheus",
            "tags": filtered_tags,
            "severity": severity,
            "alertname": alertname
        }
        fingerprint = self.generate_fingerprint(fingerprint_data)
        
        return AlarmCreate(
            title=title,
            description=description,
            severity=severity,
            status=status,
            source="prometheus",
            tags=filtered_tags,
            metadata=metadata,
            fingerprint=fingerprint,
            created_at=starts_at or datetime.now()
        )
    
    def _map_prometheus_status(self, status: str) -> str:
        """映射 Prometheus 状态到标准状态"""
        status_mapping = {
            "firing": "active",
            "resolved": "resolved",
            "pending": "active",
            "inactive": "resolved"
        }
        return status_mapping.get(status.lower(), "active")
    
    def _extract_severity(self, labels: Dict[str, Any], annotations: Dict[str, Any]) -> str:
        """提取严重程度"""
        # 优先从labels中提取
        severity_fields = ["severity", "priority", "level", "criticality"]
        
        for field in severity_fields:
            if field in labels:
                return self.normalize_severity(str(labels[field]))
            elif field in annotations:
                return self.normalize_severity(str(annotations[field]))
        
        # 从告警名称推断严重程度
        alertname = labels.get("alertname", "").lower()
        
        # 关键词匹配
        if any(word in alertname for word in ["critical", "fatal", "emergency", "down", "dead"]):
            return "critical"
        elif any(word in alertname for word in ["high", "error", "failed", "timeout"]):
            return "high"
        elif any(word in alertname for word in ["warning", "warn", "slow", "degraded"]):
            return "medium"
        elif any(word in alertname for word in ["info", "notice", "low"]):
            return "low"
        
        # 根据指标类型推断
        if "cpu" in alertname or "memory" in alertname or "disk" in alertname:
            return "high"
        elif "network" in alertname or "io" in alertname:
            return "medium"
        
        return "medium"  # 默认中等严重程度
    
    def _build_title(self, labels: Dict[str, Any], annotations: Dict[str, Any], alertname: str) -> str:
        """构建告警标题"""
        # 优先使用annotations中的summary
        if "summary" in annotations:
            return annotations["summary"]
        
        # 使用annotations中的title
        if "title" in annotations:
            return annotations["title"]
        
        # 构建自定义标题
        instance = labels.get("instance", "")
        job = labels.get("job", "")
        service = labels.get("service", "")
        
        title_parts = [alertname]
        
        if service:
            title_parts.append(f"on {service}")
        elif job:
            title_parts.append(f"on {job}")
        
        if instance:
            title_parts.append(f"({instance})")
        
        return " ".join(title_parts)
    
    def _build_description(self, labels: Dict[str, Any], annotations: Dict[str, Any], alert: Dict[str, Any]) -> str:
        """构建告警描述"""
        description_parts = []
        
        # 使用annotations中的description
        if "description" in annotations:
            description_parts.append(annotations["description"])
        elif "message" in annotations:
            description_parts.append(annotations["message"])
        
        # 添加关键标签信息
        important_labels = [
            "instance", "job", "service", "environment", "team", 
            "cluster", "namespace", "pod", "container", "node"
        ]
        
        label_info = []
        for label in important_labels:
            if label in labels and labels[label]:
                label_info.append(f"{label}: {labels[label]}")
        
        if label_info:
            description_parts.append("Labels: " + ", ".join(label_info))
        
        # 添加指标查询信息
        if "runbook_url" in annotations:
            description_parts.append(f"Runbook: {annotations['runbook_url']}")
        
        if "dashboard_url" in annotations:
            description_parts.append(f"Dashboard: {annotations['dashboard_url']}")
        
        # 添加时间信息
        starts_at = alert.get("startsAt")
        if starts_at:
            starts_time = self.format_timestamp(starts_at)
            if starts_time:
                description_parts.append(f"Started at: {starts_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return "\n\n".join(description_parts) if description_parts else f"Prometheus alert: {labels.get('alertname', 'Unknown')}"
    
    def parse_multiple_alerts(self, raw_data: Dict[str, Any]) -> List[AlarmCreate]:
        """解析多个告警（批量处理）"""
        alerts = raw_data.get("alerts", [])
        if not alerts:
            return []
        
        alarm_list = []
        
        for alert in alerts:
            try:
                # 构造单个告警的数据格式
                single_alert_data = {
                    "alerts": [alert],
                    "status": raw_data.get("status", ""),
                    "receiver": raw_data.get("receiver", ""),
                    "externalURL": raw_data.get("externalURL", ""),
                    "groupKey": raw_data.get("groupKey", ""),
                    "groupLabels": raw_data.get("groupLabels", {}),
                    "commonLabels": raw_data.get("commonLabels", {}),
                    "commonAnnotations": raw_data.get("commonAnnotations", {})
                }
                
                alarm = self.parse_alarm(single_alert_data)
                alarm_list.append(alarm)
                
            except Exception as e:
                # 记录错误但继续处理其他告警
                print(f"Error parsing alert: {e}")
                continue
        
        return alarm_list
    
    def extract_metric_info(self, labels: Dict[str, Any], annotations: Dict[str, Any]) -> Dict[str, Any]:
        """提取指标相关信息"""
        metric_info = {}
        
        # 提取查询表达式
        if "expr" in annotations:
            metric_info["query"] = annotations["expr"]
        elif "query" in annotations:
            metric_info["query"] = annotations["query"]
        
        # 提取阈值信息
        threshold_fields = ["threshold", "for", "value"]
        for field in threshold_fields:
            if field in annotations:
                metric_info[field] = annotations[field]
        
        # 提取指标名称
        if "__name__" in labels:
            metric_info["metric_name"] = labels["__name__"]
        
        return metric_info
    
    def group_related_alerts(self, alerts_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """将相关告警分组"""
        groups = {}
        
        for alert_data in alerts_data:
            alerts = alert_data.get("alerts", [])
            group_key = alert_data.get("groupKey", "default")
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].extend(alerts)
        
        return groups