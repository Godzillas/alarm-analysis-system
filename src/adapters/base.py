"""
告警适配器基类
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
import json

from src.models.alarm import AlarmCreate


class BaseAlarmAdapter(ABC):
    """告警适配器基类"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
    
    @abstractmethod
    def parse_alarm(self, raw_data: Dict[str, Any]) -> AlarmCreate:
        """
        解析原始告警数据为标准告警格式
        
        Args:
            raw_data: 原始告警数据
            
        Returns:
            AlarmCreate: 标准化的告警数据
        """
        pass
    
    @abstractmethod 
    def validate_data(self, raw_data: Dict[str, Any]) -> bool:
        """
        验证原始数据格式是否正确
        
        Args:
            raw_data: 原始告警数据
            
        Returns:
            bool: 数据是否有效
        """
        pass
    
    def generate_fingerprint(self, alarm_data: Dict[str, Any]) -> str:
        """
        生成告警指纹用于去重
        
        Args:
            alarm_data: 告警数据
            
        Returns:
            str: 告警指纹
        """
        # 基于关键字段生成指纹
        key_fields = [
            alarm_data.get("title", ""),
            alarm_data.get("source", ""),
            str(alarm_data.get("tags", {})),
            alarm_data.get("severity", "")
        ]
        
        fingerprint_str = "|".join(key_fields)
        return hashlib.md5(fingerprint_str.encode()).hexdigest()
    
    def normalize_severity(self, severity: str) -> str:
        """
        标准化严重程度
        
        Args:
            severity: 原始严重程度
            
        Returns:
            str: 标准化的严重程度 (critical, high, medium, low, info)
        """
        severity_lower = severity.lower().strip()
        
        # 常见的严重程度映射
        severity_mapping = {
            # Critical级别
            "critical": "critical",
            "fatal": "critical", 
            "emergency": "critical",
            "p1": "critical",
            "severity1": "critical",
            
            # High级别
            "high": "high",
            "error": "high",
            "major": "high",
            "p2": "high", 
            "severity2": "high",
            
            # Medium级别
            "medium": "medium",
            "warning": "medium",
            "minor": "medium",
            "warn": "medium",
            "p3": "medium",
            "severity3": "medium",
            
            # Low级别
            "low": "low",
            "notice": "low",
            "p4": "low",
            "severity4": "low",
            
            # Info级别
            "info": "info",
            "information": "info",
            "debug": "info",
            "p5": "info",
            "severity5": "info"
        }
        
        return severity_mapping.get(severity_lower, "medium")
    
    def extract_system_info(self, raw_data: Dict[str, Any]) -> Dict[str, str]:
        """
        从原始数据中提取系统信息
        
        Args:
            raw_data: 原始数据
            
        Returns:
            Dict[str, str]: 系统信息字典
        """
        system_info = {}
        
        # 尝试从不同字段提取系统信息
        labels = raw_data.get("labels", {})
        tags = raw_data.get("tags", {})
        
        # 提取服务名
        service_fields = ["service", "service_name", "app", "application", "job"]
        for field in service_fields:
            if field in labels:
                system_info["service"] = labels[field]
                break
            elif field in tags:
                system_info["service"] = tags[field]
                break
        
        # 提取环境
        env_fields = ["environment", "env", "stage", "tier"]
        for field in env_fields:
            if field in labels:
                system_info["environment"] = labels[field]
                break
            elif field in tags:
                system_info["environment"] = tags[field]
                break
        
        # 提取实例
        instance_fields = ["instance", "host", "hostname", "node"]
        for field in instance_fields:
            if field in labels:
                system_info["instance"] = labels[field]
                break
            elif field in tags:
                system_info["instance"] = tags[field]
                break
        
        # 提取团队
        team_fields = ["team", "owner", "responsible_team"]
        for field in team_fields:
            if field in labels:
                system_info["team"] = labels[field]
                break
            elif field in tags:
                system_info["team"] = tags[field]
                break
        
        return system_info
    
    def merge_tags(self, *tag_dicts: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并多个标签字典
        
        Args:
            *tag_dicts: 标签字典列表
            
        Returns:
            Dict[str, Any]: 合并后的标签字典
        """
        merged = {}
        for tag_dict in tag_dicts:
            if isinstance(tag_dict, dict):
                merged.update(tag_dict)
        return merged
    
    def format_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """
        格式化时间戳
        
        Args:
            timestamp: 时间戳（多种格式）
            
        Returns:
            Optional[datetime]: 格式化后的时间
        """
        if not timestamp:
            return None
            
        try:
            # 如果已经是datetime对象
            if isinstance(timestamp, datetime):
                return timestamp
            
            # 如果是字符串
            if isinstance(timestamp, str):
                # ISO格式
                if 'T' in timestamp:
                    return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                # 尝试常见格式
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S.%f"
                ]
                
                for fmt in formats:
                    try:
                        return datetime.strptime(timestamp, fmt)
                    except ValueError:
                        continue
            
            # 如果是数字（Unix时间戳）
            if isinstance(timestamp, (int, float)):
                # 判断是秒还是毫秒
                if timestamp > 1e10:  # 毫秒级时间戳
                    timestamp = timestamp / 1000
                return datetime.fromtimestamp(timestamp)
                
        except Exception:
            pass
        
        return None


BaseAdapter = BaseAlarmAdapter