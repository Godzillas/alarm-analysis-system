"""
Grafana 告警适配器
支持解析 Grafana Webhook 告警格式
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .base import BaseAlarmAdapter
from src.models.alarm import AlarmCreate


class GrafanaAdapter(BaseAlarmAdapter):
    """Grafana 告警适配器"""
    
    def __init__(self):
        super().__init__("grafana")
    
    def validate_data(self, raw_data: Dict[str, Any]) -> bool:
        """验证 Grafana 告警数据格式"""
        # 检查必要字段
        required_fields = ["title", "state", "message"]
        
        # Grafana 新版本格式
        if "alerts" in raw_data:
            return True
            
        # Grafana 旧版本格式
        for field in required_fields:
            if field not in raw_data:
                return False
                
        return True
    
    def parse_alarm(self, raw_data: Dict[str, Any]) -> AlarmCreate:
        """解析 Grafana 告警数据"""
        
        # 处理新版本格式（Grafana 8+）
        if "alerts" in raw_data:
            return self._parse_unified_alerting(raw_data)
        else:
            return self._parse_legacy_alerting(raw_data)
    
    def _parse_unified_alerting(self, raw_data: Dict[str, Any]) -> AlarmCreate:
        """解析统一告警格式（Grafana 8+）"""
        
        # 获取第一个告警的详细信息（如果有多个告警，后续可以批量处理）
        alerts = raw_data.get("alerts", [])
        if not alerts:
            raise ValueError("No alerts found in Grafana webhook data")
        
        alert = alerts[0]  # 取第一个告警
        
        # 基础信息
        title = raw_data.get("title", "") or alert.get("labels", {}).get("alertname", "Grafana Alert")
        message = raw_data.get("message", "") or alert.get("annotations", {}).get("summary", "")
        
        # 状态映射
        state = raw_data.get("state", alert.get("state", "firing"))
        status = self._map_grafana_state(state)
        
        # 严重程度
        severity = self._extract_severity(alert, raw_data)
        
        # 标签和注解
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        
        # 提取系统信息
        system_info = self.extract_system_info({"labels": labels, "annotations": annotations})
        
        # 构建标签
        tags = self.merge_tags(
            labels,
            annotations,
            system_info,
            {
                "source": "grafana",
                "alert_state": state,
                "rule_uid": raw_data.get("ruleId", ""),
                "orgId": str(raw_data.get("orgId", "")),
                "dashboard_uid": self._extract_dashboard_uid(alert),
                "panel_id": str(self._extract_panel_id(alert))
            }
        )
        
        # 构建元数据
        metadata = {
            "grafana_url": raw_data.get("ruleUrl", ""),
            "dashboard_url": self._build_dashboard_url(alert, raw_data),
            "panel_url": self._build_panel_url(alert, raw_data),
            "rule_name": labels.get("alertname", ""),
            "rule_uid": raw_data.get("ruleId", ""),
            "org_id": raw_data.get("orgId"),
            "values": alert.get("values", {}),
            "generator_url": alert.get("generatorURL", ""),
            "fingerprint": alert.get("fingerprint", "")
        }
        
        # 时间信息
        starts_at = self.format_timestamp(alert.get("startsAt"))
        ends_at = self.format_timestamp(alert.get("endsAt"))
        
        # 生成描述
        description = self._build_description(alert, annotations, message)
        
        # 生成指纹
        fingerprint_data = {
            "title": title,
            "source": "grafana",
            "tags": tags,
            "severity": severity
        }
        fingerprint = self.generate_fingerprint(fingerprint_data)
        
        return AlarmCreate(
            title=title,
            description=description,
            severity=severity,
            status=status,
            source="grafana",
            tags=tags,
            metadata=metadata,
            fingerprint=fingerprint,
            created_at=starts_at or datetime.now()
        )
    
    def _parse_legacy_alerting(self, raw_data: Dict[str, Any]) -> AlarmCreate:
        """解析传统告警格式（Grafana 7-）"""
        
        # 基础信息
        title = raw_data.get("title", "Grafana Legacy Alert")
        message = raw_data.get("message", "")
        
        # 状态映射
        state = raw_data.get("state", "alerting")
        status = self._map_grafana_state(state)
        
        # 严重程度
        severity = self._extract_legacy_severity(raw_data)
        
        # 规则信息
        rule = raw_data.get("rule", {})
        
        # 标签
        tags = self.merge_tags(
            rule.get("tags", {}),
            {
                "source": "grafana",
                "alert_state": state,
                "rule_id": str(rule.get("id", "")),
                "rule_name": rule.get("name", ""),
                "dashboard_id": str(raw_data.get("dashboardId", "")),
                "panel_id": str(raw_data.get("panelId", ""))
            }
        )
        
        # 元数据
        metadata = {
            "rule_url": raw_data.get("ruleUrl", ""),
            "dashboard_url": f"https://grafana.example.com/d/{raw_data.get('dashboardId', '')}",
            "panel_url": f"https://grafana.example.com/d/{raw_data.get('dashboardId', '')}?panelId={raw_data.get('panelId', '')}",
            "rule_id": rule.get("id"),
            "rule_name": rule.get("name"),
            "dashboard_id": raw_data.get("dashboardId"),
            "panel_id": raw_data.get("panelId"),
            "eval_matches": raw_data.get("evalMatches", [])
        }
        
        # 构建描述
        description = self._build_legacy_description(raw_data, message)
        
        # 生成指纹
        fingerprint_data = {
            "title": title,
            "source": "grafana", 
            "tags": tags,
            "severity": severity
        }
        fingerprint = self.generate_fingerprint(fingerprint_data)
        
        return AlarmCreate(
            title=title,
            description=description,
            severity=severity,
            status=status,
            source="grafana",
            tags=tags,
            metadata=metadata,
            fingerprint=fingerprint,
            created_at=datetime.now()
        )
    
    def _map_grafana_state(self, state: str) -> str:
        """映射 Grafana 状态到标准状态"""
        state_mapping = {
            "firing": "active",
            "alerting": "active", 
            "resolved": "resolved",
            "ok": "resolved",
            "no_data": "active",
            "paused": "acknowledged",
            "pending": "active"
        }
        return state_mapping.get(state.lower(), "active")
    
    def _extract_severity(self, alert: Dict[str, Any], raw_data: Dict[str, Any]) -> str:
        """提取严重程度"""
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        
        # 从多个可能的字段提取严重程度
        severity_fields = ["severity", "priority", "level"]
        
        for field in severity_fields:
            if field in labels:
                return self.normalize_severity(labels[field])
            elif field in annotations:
                return self.normalize_severity(annotations[field])
        
        # 从规则名称推断严重程度
        rule_name = labels.get("alertname", "").lower()
        if any(word in rule_name for word in ["critical", "fatal", "emergency"]):
            return "critical"
        elif any(word in rule_name for word in ["high", "error", "major"]):
            return "high"
        elif any(word in rule_name for word in ["warning", "warn", "medium"]):
            return "medium"
        elif any(word in rule_name for word in ["low", "minor", "notice"]):
            return "low"
        
        return "medium"  # 默认中等严重程度
    
    def _extract_legacy_severity(self, raw_data: Dict[str, Any]) -> str:
        """提取传统告警的严重程度"""
        # 从规则或标签中提取
        rule = raw_data.get("rule", {})
        tags = rule.get("tags", {})
        
        if "severity" in tags:
            return self.normalize_severity(tags["severity"])
        
        # 从标题推断
        title = raw_data.get("title", "").lower()
        if any(word in title for word in ["critical", "fatal", "emergency"]):
            return "critical"
        elif any(word in title for word in ["high", "error", "major"]):
            return "high"
        elif any(word in title for word in ["warning", "warn"]):
            return "medium"
        
        return "medium"
    
    def _extract_dashboard_uid(self, alert: Dict[str, Any]) -> str:
        """提取仪表板UID"""
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        
        # 尝试从不同字段提取
        for field in ["dashboard_uid", "dashboardUID", "grafana_dashboard"]:
            if field in labels:
                return labels[field]
            elif field in annotations:
                return annotations[field]
        
        return ""
    
    def _extract_panel_id(self, alert: Dict[str, Any]) -> int:
        """提取面板ID"""
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        
        # 尝试从不同字段提取
        for field in ["panel_id", "panelId", "grafana_panel"]:
            if field in labels:
                try:
                    return int(labels[field])
                except (ValueError, TypeError):
                    pass
            elif field in annotations:
                try:
                    return int(annotations[field])
                except (ValueError, TypeError):
                    pass
        
        return 0
    
    def _build_dashboard_url(self, alert: Dict[str, Any], raw_data: Dict[str, Any]) -> str:
        """构建仪表板URL"""
        dashboard_uid = self._extract_dashboard_uid(alert)
        if dashboard_uid:
            base_url = raw_data.get("externalURL", "https://grafana.example.com")
            return f"{base_url}/d/{dashboard_uid}"
        return ""
    
    def _build_panel_url(self, alert: Dict[str, Any], raw_data: Dict[str, Any]) -> str:
        """构建面板URL"""
        dashboard_uid = self._extract_dashboard_uid(alert)
        panel_id = self._extract_panel_id(alert)
        
        if dashboard_uid and panel_id:
            base_url = raw_data.get("externalURL", "https://grafana.example.com")
            return f"{base_url}/d/{dashboard_uid}?panelId={panel_id}"
        return ""
    
    def _build_description(self, alert: Dict[str, Any], annotations: Dict[str, Any], message: str) -> str:
        """构建告警描述"""
        description_parts = []
        
        # 优先使用注解中的描述
        if "description" in annotations:
            description_parts.append(annotations["description"])
        elif "summary" in annotations:
            description_parts.append(annotations["summary"])
        elif message:
            description_parts.append(message)
        
        # 添加值信息
        values = alert.get("values", {})
        if values:
            value_strs = []
            for key, value in values.items():
                if value is not None:
                    value_strs.append(f"{key}: {value}")
            if value_strs:
                description_parts.append(f"Values: {', '.join(value_strs)}")
        
        # 添加标签信息
        labels = alert.get("labels", {})
        important_labels = ["instance", "job", "service", "environment"]
        label_info = []
        for label in important_labels:
            if label in labels:
                label_info.append(f"{label}: {labels[label]}")
        
        if label_info:
            description_parts.append(f"Labels: {', '.join(label_info)}")
        
        return "\n\n".join(description_parts) if description_parts else "Grafana alert triggered"
    
    def _build_legacy_description(self, raw_data: Dict[str, Any], message: str) -> str:
        """构建传统告警描述"""
        description_parts = []
        
        if message:
            description_parts.append(message)
        
        # 添加匹配结果
        eval_matches = raw_data.get("evalMatches", [])
        if eval_matches:
            match_strs = []
            for match in eval_matches:
                metric = match.get("metric", "unknown")
                value = match.get("value", "N/A")
                match_strs.append(f"{metric}: {value}")
            
            if match_strs:
                description_parts.append(f"Matches: {', '.join(match_strs)}")
        
        return "\n\n".join(description_parts) if description_parts else "Grafana legacy alert triggered"