"""
云厂商告警适配器
支持腾讯云、阿里云等云平台的告警格式
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from .base import BaseAlarmAdapter
from src.models.alarm import AlarmCreate


class TencentCloudAdapter(BaseAlarmAdapter):
    """腾讯云告警适配器"""
    
    def __init__(self, token: Optional[str] = None):
        super().__init__("tencent_cloud")
        self.token = token
    
    def validate_data(self, raw_data: Dict[str, Any]) -> bool:
        """验证腾讯云告警数据格式"""
        # 检查腾讯云特有字段
        tencent_fields = ["sessionId", "alarmStatus", "alarmType"]
        
        # 检查是否包含腾讯云特征字段
        has_tencent_fields = any(field in raw_data for field in tencent_fields)
        
        if has_tencent_fields:
            return True
        
        # 检查基础必要字段
        required_fields = ["alarmPolicyInfo", "alarmObjInfo"]
        return all(field in raw_data for field in required_fields)
    
    def parse_alarm(self, raw_data: Dict[str, Any]) -> AlarmCreate:
        """解析腾讯云告警数据"""
        
        # 获取告警策略信息
        policy_info = raw_data.get("alarmPolicyInfo", {})
        obj_info = raw_data.get("alarmObjInfo", {})
        
        # 基础信息
        policy_name = policy_info.get("policyName", "腾讯云告警")
        alarm_content = raw_data.get("alarmContent", "")
        
        # 构建标题
        title = self._build_tencent_title(policy_info, obj_info, raw_data)
        
        # 状态映射
        alarm_status = raw_data.get("alarmStatus", "1")
        status = self._map_tencent_status(alarm_status)
        
        # 严重程度
        severity = self._extract_tencent_severity(raw_data, policy_info)
        
        # 构建标签
        tags = self._build_tencent_tags(raw_data, policy_info, obj_info)
        
        # 构建描述
        description = self._build_tencent_description(raw_data, policy_info, obj_info)
        
        # 构建元数据
        metadata = {
            "session_id": raw_data.get("sessionId", ""),
            "alarm_type": raw_data.get("alarmType", ""),
            "policy_id": policy_info.get("policyId", ""),
            "policy_name": policy_info.get("policyName", ""),
            "policy_type": policy_info.get("policyType", ""),
            "policy_view_name": policy_info.get("policyViewName", ""),
            "obj_id": obj_info.get("objId", ""),
            "obj_name": obj_info.get("objName", ""),
            "region": obj_info.get("region", ""),
            "first_occur_time": raw_data.get("firstOccurTime", ""),
            "duration_time": raw_data.get("durationTime", ""),
            "occur_number": raw_data.get("occurNumber", "")
        }
        
        # 时间信息
        occur_time = self._parse_tencent_time(raw_data.get("firstOccurTime", ""))
        
        # 生成指纹
        fingerprint_data = {
            "title": title,
            "source": "tencent_cloud",
            "tags": tags,
            "severity": severity
        }
        fingerprint = self.generate_fingerprint(fingerprint_data)
        
        return AlarmCreate(
            title=title,
            description=description,
            severity=severity,
            status=status,
            source="tencent_cloud",
            tags=tags,
            metadata=metadata,
            fingerprint=fingerprint,
            created_at=occur_time or datetime.now()
        )
    
    def _build_tencent_title(self, policy_info: Dict, obj_info: Dict, raw_data: Dict) -> str:
        """构建腾讯云告警标题"""
        policy_name = policy_info.get("policyName", "")
        obj_name = obj_info.get("objName", "")
        
        if policy_name and obj_name:
            return f"{policy_name} - {obj_name}"
        elif policy_name:
            return f"腾讯云告警: {policy_name}"
        else:
            return "腾讯云告警"
    
    def _map_tencent_status(self, alarm_status: str) -> str:
        """映射腾讯云状态到标准状态"""
        # 腾讯云状态：1-告警，0-恢复
        status_mapping = {
            "1": "active",
            "0": "resolved",
            "ALARM": "active",
            "OK": "resolved"
        }
        return status_mapping.get(str(alarm_status), "active")
    
    def _extract_tencent_severity(self, raw_data: Dict, policy_info: Dict) -> str:
        """提取腾讯云告警严重程度"""
        # 从策略信息中推断
        policy_name = policy_info.get("policyName", "").lower()
        policy_view_name = policy_info.get("policyViewName", "").lower()
        
        # 关键词匹配
        critical_keywords = ["critical", "严重", "fatal", "emergency"]
        high_keywords = ["high", "高", "error", "错误", "major"]
        medium_keywords = ["medium", "中", "warning", "警告", "warn"]
        
        text_to_check = f"{policy_name} {policy_view_name}".lower()
        
        if any(keyword in text_to_check for keyword in critical_keywords):
            return "critical"
        elif any(keyword in text_to_check for keyword in high_keywords):
            return "high"
        elif any(keyword in text_to_check for keyword in medium_keywords):
            return "medium"
        
        return "medium"
    
    def _build_tencent_tags(self, raw_data: Dict, policy_info: Dict, obj_info: Dict) -> Dict[str, Any]:
        """构建腾讯云标签"""
        tags = {
            "source": "tencent_cloud",
            "cloud_provider": "tencent",
            "policy_type": policy_info.get("policyType", ""),
            "policy_view_name": policy_info.get("policyViewName", ""),
            "region": obj_info.get("region", ""),
            "obj_id": obj_info.get("objId", ""),
            "alarm_type": raw_data.get("alarmType", ""),
            "session_id": raw_data.get("sessionId", "")
        }
        
        # 移除空值
        return {k: v for k, v in tags.items() if v}
    
    def _build_tencent_description(self, raw_data: Dict, policy_info: Dict, obj_info: Dict) -> str:
        """构建腾讯云告警描述"""
        description_parts = []
        
        # 告警内容
        alarm_content = raw_data.get("alarmContent", "")
        if alarm_content:
            description_parts.append(f"告警内容: {alarm_content}")
        
        # 对象信息
        obj_name = obj_info.get("objName", "")
        if obj_name:
            description_parts.append(f"告警对象: {obj_name}")
        
        # 策略信息
        policy_name = policy_info.get("policyName", "")
        if policy_name:
            description_parts.append(f"告警策略: {policy_name}")
        
        # 持续时间
        duration = raw_data.get("durationTime", "")
        if duration:
            description_parts.append(f"持续时间: {duration}")
        
        # 发生次数
        occur_number = raw_data.get("occurNumber", "")
        if occur_number:
            description_parts.append(f"发生次数: {occur_number}")
        
        return "\n".join(description_parts) if description_parts else "腾讯云告警"
    
    def _parse_tencent_time(self, time_str: str) -> Optional[datetime]:
        """解析腾讯云时间格式"""
        if not time_str:
            return None
        
        try:
            # 腾讯云时间格式通常是：2023-01-01 12:00:00
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                # 尝试其他格式
                return datetime.fromisoformat(time_str)
            except ValueError:
                return None


class AliCloudAdapter(BaseAlarmAdapter):
    """阿里云告警适配器"""
    
    def __init__(self, token: Optional[str] = None):
        super().__init__("ali_cloud")
        self.token = token
    
    def validate_data(self, raw_data: Dict[str, Any]) -> bool:
        """验证阿里云告警数据格式"""
        # 检查阿里云特有字段
        ali_fields = ["alertName", "metricName", "namespace", "instanceName"]
        
        # 检查是否包含阿里云特征字段
        has_ali_fields = any(field in raw_data for field in ali_fields)
        
        if has_ali_fields:
            return True
        
        # 检查基础必要字段
        required_fields = ["alertName", "alertState"]
        return all(field in raw_data for field in required_fields)
    
    def parse_alarm(self, raw_data: Dict[str, Any]) -> AlarmCreate:
        """解析阿里云告警数据"""
        
        # 基础信息
        alert_name = raw_data.get("alertName", "阿里云告警")
        metric_name = raw_data.get("metricName", "")
        instance_name = raw_data.get("instanceName", "")
        
        # 构建标题
        title = self._build_ali_title(raw_data)
        
        # 状态映射
        alert_state = raw_data.get("alertState", "ALERT")
        status = self._map_ali_status(alert_state)
        
        # 严重程度
        severity = self._extract_ali_severity(raw_data)
        
        # 构建标签
        tags = self._build_ali_tags(raw_data)
        
        # 构建描述
        description = self._build_ali_description(raw_data)
        
        # 构建元数据
        metadata = {
            "alert_name": alert_name,
            "metric_name": metric_name,
            "namespace": raw_data.get("namespace", ""),
            "instance_name": instance_name,
            "region_id": raw_data.get("regionId", ""),
            "group_id": raw_data.get("groupId", ""),
            "level": raw_data.get("level", ""),
            "rule_id": raw_data.get("ruleId", ""),
            "last_time": raw_data.get("lastTime", ""),
            "expression": raw_data.get("expression", ""),
            "current_value": raw_data.get("curValue", ""),
            "pre_value": raw_data.get("preValue", "")
        }
        
        # 时间信息
        last_time = self._parse_ali_time(raw_data.get("lastTime", ""))
        
        # 生成指纹
        fingerprint_data = {
            "title": title,
            "source": "ali_cloud",
            "tags": tags,
            "severity": severity
        }
        fingerprint = self.generate_fingerprint(fingerprint_data)
        
        return AlarmCreate(
            title=title,
            description=description,
            severity=severity,
            status=status,
            source="ali_cloud",
            tags=tags,
            metadata=metadata,
            fingerprint=fingerprint,
            created_at=last_time or datetime.now()
        )
    
    def _build_ali_title(self, raw_data: Dict) -> str:
        """构建阿里云告警标题"""
        alert_name = raw_data.get("alertName", "")
        instance_name = raw_data.get("instanceName", "")
        metric_name = raw_data.get("metricName", "")
        
        if alert_name and instance_name:
            return f"{alert_name} - {instance_name}"
        elif alert_name:
            return f"阿里云告警: {alert_name}"
        elif metric_name:
            return f"阿里云告警: {metric_name}"
        else:
            return "阿里云告警"
    
    def _map_ali_status(self, alert_state: str) -> str:
        """映射阿里云状态到标准状态"""
        status_mapping = {
            "ALERT": "active",
            "OK": "resolved",
            "INSUFFICIENT_DATA": "active",
            "1": "active",
            "0": "resolved"
        }
        return status_mapping.get(str(alert_state), "active")
    
    def _extract_ali_severity(self, raw_data: Dict) -> str:
        """提取阿里云告警严重程度"""
        # 阿里云level字段映射
        level = raw_data.get("level", "").upper()
        level_mapping = {
            "CRITICAL": "critical",
            "WARN": "medium",
            "INFO": "low",
            "4": "critical",
            "3": "high", 
            "2": "medium",
            "1": "low"
        }
        
        if level in level_mapping:
            return level_mapping[level]
        
        # 从告警名称推断
        alert_name = raw_data.get("alertName", "").lower()
        
        if any(word in alert_name for word in ["critical", "严重", "fatal", "emergency"]):
            return "critical"
        elif any(word in alert_name for word in ["high", "高", "error", "错误"]):
            return "high"
        elif any(word in alert_name for word in ["warning", "警告", "warn"]):
            return "medium"
        
        return "medium"
    
    def _build_ali_tags(self, raw_data: Dict) -> Dict[str, Any]:
        """构建阿里云标签"""
        tags = {
            "source": "ali_cloud",
            "cloud_provider": "alibaba",
            "namespace": raw_data.get("namespace", ""),
            "metric_name": raw_data.get("metricName", ""),
            "region_id": raw_data.get("regionId", ""),
            "group_id": raw_data.get("groupId", ""),
            "instance_name": raw_data.get("instanceName", ""),
            "level": raw_data.get("level", ""),
            "rule_id": raw_data.get("ruleId", "")
        }
        
        # 移除空值
        return {k: v for k, v in tags.items() if v}
    
    def _build_ali_description(self, raw_data: Dict) -> str:
        """构建阿里云告警描述"""
        description_parts = []
        
        # 告警规则
        alert_name = raw_data.get("alertName", "")
        if alert_name:
            description_parts.append(f"告警规则: {alert_name}")
        
        # 监控项
        metric_name = raw_data.get("metricName", "")
        if metric_name:
            description_parts.append(f"监控项: {metric_name}")
        
        # 实例信息
        instance_name = raw_data.get("instanceName", "")
        if instance_name:
            description_parts.append(f"实例: {instance_name}")
        
        # 当前值
        cur_value = raw_data.get("curValue", "")
        if cur_value:
            description_parts.append(f"当前值: {cur_value}")
        
        # 阈值表达式
        expression = raw_data.get("expression", "")
        if expression:
            description_parts.append(f"阈值条件: {expression}")
        
        # 地域
        region_id = raw_data.get("regionId", "")
        if region_id:
            description_parts.append(f"地域: {region_id}")
        
        return "\n".join(description_parts) if description_parts else "阿里云告警"
    
    def _parse_ali_time(self, time_str: str) -> Optional[datetime]:
        """解析阿里云时间格式"""
        if not time_str:
            return None
        
        try:
            # 阿里云时间格式可能是毫秒时间戳
            if time_str.isdigit():
                timestamp = int(time_str)
                if timestamp > 1e10:  # 毫秒时间戳
                    timestamp = timestamp / 1000
                return datetime.fromtimestamp(timestamp)
            
            # 字符串格式
            return datetime.fromisoformat(time_str)
            
        except (ValueError, OSError):
            return None


# 默认使用腾讯云适配器作为CloudAdapter
CloudAdapter = TencentCloudAdapter