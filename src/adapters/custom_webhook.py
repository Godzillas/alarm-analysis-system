"""
自定义 Webhook 告警适配器
支持自定义格式的 Webhook 告警数据解析
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from .base import BaseAlarmAdapter
from src.models.alarm import AlarmCreate


class CustomWebhookAdapter(BaseAlarmAdapter):
    """自定义 Webhook 告警适配器"""
    
    def __init__(self, field_mapping: Optional[Dict[str, str]] = None):
        super().__init__("custom_webhook")
        # 字段映射配置，支持自定义字段映射
        self.field_mapping = field_mapping or self._get_default_mapping()
    
    def _get_default_mapping(self) -> Dict[str, str]:
        """获取默认字段映射"""
        return {
            "title": ["title", "subject", "name", "alert_name", "summary"],
            "description": ["description", "message", "details", "content", "body"],
            "severity": ["severity", "level", "priority", "criticality"],
            "status": ["status", "state", "alert_state"],
            "source": ["source", "origin", "from", "sender"],
            "timestamp": ["timestamp", "time", "created_at", "occurred_at", "event_time"],
            "instance": ["instance", "host", "hostname", "server", "node"],
            "service": ["service", "application", "app", "component"],
            "environment": ["environment", "env", "stage", "tier"],
            "team": ["team", "owner", "responsible", "group"]
        }
    
    def validate_data(self, raw_data: Dict[str, Any]) -> bool:
        """验证自定义 Webhook 数据格式"""
        if not isinstance(raw_data, dict):
            return False
        
        # 至少需要包含标题或描述信息
        title_fields = self.field_mapping.get("title", [])
        description_fields = self.field_mapping.get("description", [])
        
        has_title = any(field in raw_data for field in title_fields)
        has_description = any(field in raw_data for field in description_fields)
        
        return has_title or has_description
    
    def parse_alarm(self, raw_data: Dict[str, Any]) -> AlarmCreate:
        """解析自定义 Webhook 告警数据"""
        
        # 提取基础字段
        title = self._extract_field(raw_data, "title") or "Custom Webhook Alert"
        description = self._extract_field(raw_data, "description") or ""
        severity = self._extract_severity(raw_data)
        status = self._extract_status(raw_data)
        source = self._extract_field(raw_data, "source") or "custom_webhook"
        
        # 提取时间信息
        timestamp_str = self._extract_field(raw_data, "timestamp")
        created_at = self.format_timestamp(timestamp_str) if timestamp_str else datetime.now()
        
        # 构建标签
        tags = self._build_custom_tags(raw_data)
        
        # 构建元数据
        metadata = self._build_custom_metadata(raw_data)
        
        # 生成指纹
        fingerprint_data = {
            "title": title,
            "source": source,
            "tags": tags,
            "severity": severity
        }
        fingerprint = self.generate_fingerprint(fingerprint_data)
        
        return AlarmCreate(
            title=title,
            description=description,
            severity=severity,
            status=status,
            source=source,
            tags=tags,
            metadata=metadata,
            fingerprint=fingerprint,
            created_at=created_at
        )
    
    def _extract_field(self, raw_data: Dict[str, Any], field_type: str) -> Optional[str]:
        """根据字段映射提取字段值"""
        possible_fields = self.field_mapping.get(field_type, [])
        
        for field in possible_fields:
            if field in raw_data:
                value = raw_data[field]
                if value is not None:
                    return str(value)
        
        return None
    
    def _extract_severity(self, raw_data: Dict[str, Any]) -> str:
        """提取严重程度"""
        severity_str = self._extract_field(raw_data, "severity")
        
        if severity_str:
            return self.normalize_severity(severity_str)
        
        # 尝试从标题推断严重程度
        title = self._extract_field(raw_data, "title") or ""
        description = self._extract_field(raw_data, "description") or ""
        
        text_to_check = f"{title} {description}".lower()
        
        if any(word in text_to_check for word in ["critical", "fatal", "emergency", "urgent"]):
            return "critical"
        elif any(word in text_to_check for word in ["high", "error", "major", "severe"]):
            return "high"
        elif any(word in text_to_check for word in ["warning", "warn", "medium", "moderate"]):
            return "medium"
        elif any(word in text_to_check for word in ["low", "minor", "notice"]):
            return "low"
        elif any(word in text_to_check for word in ["info", "information", "debug"]):
            return "info"
        
        return "medium"  # 默认值
    
    def _extract_status(self, raw_data: Dict[str, Any]) -> str:
        """提取告警状态"""
        status_str = self._extract_field(raw_data, "status")
        
        if not status_str:
            return "active"  # 默认状态
        
        status_lower = status_str.lower()
        
        # 状态映射
        if status_lower in ["resolved", "ok", "clear", "closed", "fixed"]:
            return "resolved"
        elif status_lower in ["acknowledged", "ack", "assigned", "investigating"]:
            return "acknowledged"
        else:
            return "active"
    
    def _build_custom_tags(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建自定义标签"""
        tags = {"source": "custom_webhook"}
        
        # 添加系统信息标签
        system_fields = ["instance", "service", "environment", "team"]
        for field in system_fields:
            value = self._extract_field(raw_data, field)
            if value:
                tags[field] = value
        
        # 添加其他有用的字段
        additional_fields = [
            "category", "type", "region", "cluster", "namespace", 
            "component", "version", "build", "deployment"
        ]
        
        for field in additional_fields:
            if field in raw_data and raw_data[field]:
                tags[field] = str(raw_data[field])
        
        # 添加嵌套对象中的标签
        if "tags" in raw_data and isinstance(raw_data["tags"], dict):
            tags.update(raw_data["tags"])
        
        if "labels" in raw_data and isinstance(raw_data["labels"], dict):
            tags.update(raw_data["labels"])
        
        return tags
    
    def _build_custom_metadata(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建自定义元数据"""
        metadata = {}
        
        # 保留原始数据的关键信息
        important_fields = [
            "id", "uuid", "correlation_id", "trace_id", "session_id",
            "url", "api_endpoint", "method", "user_agent", "ip_address",
            "version", "build_number", "commit_hash", "branch",
            "dashboard_url", "runbook_url", "documentation_url"
        ]
        
        for field in important_fields:
            if field in raw_data and raw_data[field] is not None:
                metadata[field] = raw_data[field]
        
        # 添加嵌套的元数据
        if "metadata" in raw_data and isinstance(raw_data["metadata"], dict):
            metadata.update(raw_data["metadata"])
        
        if "extra" in raw_data and isinstance(raw_data["extra"], dict):
            metadata.update(raw_data["extra"])
        
        # 添加数值类型的字段
        numeric_fields = [
            "count", "duration", "response_time", "error_rate", 
            "cpu_usage", "memory_usage", "disk_usage"
        ]
        
        for field in numeric_fields:
            if field in raw_data:
                try:
                    metadata[field] = float(raw_data[field])
                except (ValueError, TypeError):
                    metadata[field] = raw_data[field]
        
        return metadata
    
    def update_field_mapping(self, new_mapping: Dict[str, List[str]]):
        """更新字段映射配置"""
        for field_type, fields in new_mapping.items():
            if field_type in self.field_mapping:
                # 合并字段列表，新字段优先
                self.field_mapping[field_type] = fields + self.field_mapping[field_type]
            else:
                self.field_mapping[field_type] = fields
    
    def auto_detect_fields(self, sample_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """自动检测字段映射"""
        if not sample_data:
            return {}
        
        field_frequency = {}
        
        # 统计字段出现频率
        for data in sample_data:
            for field in data.keys():
                field_frequency[field] = field_frequency.get(field, 0) + 1
        
        # 推荐字段映射
        recommendations = {}
        
        # 标题字段推荐
        title_candidates = [
            field for field in field_frequency.keys() 
            if any(keyword in field.lower() for keyword in ["title", "name", "subject", "summary"])
        ]
        if title_candidates:
            recommendations["title"] = max(title_candidates, key=lambda x: field_frequency[x])
        
        # 描述字段推荐
        desc_candidates = [
            field for field in field_frequency.keys()
            if any(keyword in field.lower() for keyword in ["description", "message", "details", "content"])
        ]
        if desc_candidates:
            recommendations["description"] = max(desc_candidates, key=lambda x: field_frequency[x])
        
        # 严重程度字段推荐
        severity_candidates = [
            field for field in field_frequency.keys()
            if any(keyword in field.lower() for keyword in ["severity", "level", "priority"])
        ]
        if severity_candidates:
            recommendations["severity"] = max(severity_candidates, key=lambda x: field_frequency[x])
        
        return recommendations
    
    def validate_field_mapping(self, sample_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """验证字段映射的有效性"""
        if not sample_data:
            return {}
        
        validation_results = {}
        
        for field_type, possible_fields in self.field_mapping.items():
            found_count = 0
            total_count = len(sample_data)
            
            for data in sample_data:
                if any(field in data for field in possible_fields):
                    found_count += 1
            
            coverage = found_count / total_count if total_count > 0 else 0
            validation_results[field_type] = coverage
        
        return validation_results