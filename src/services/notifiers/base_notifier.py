"""
基础通知器抽象类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from src.utils.logger import get_logger


class BaseNotifier(ABC):
    """基础通知器抽象类"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    async def send_message(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """发送消息
        
        Args:
            config: 联络点配置
            message: 消息内容
            
        Returns:
            Dict包含success状态和相关信息
        """
        pass
    
    @abstractmethod
    async def send_test_message(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """发送测试消息
        
        Args:
            config: 联络点配置
            message: 测试消息内容
            
        Returns:
            Dict包含success状态和相关信息
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置是否有效
        
        Args:
            config: 联络点配置
            
        Returns:
            配置是否有效
        """
        pass
    
    def format_message(self, message: Dict[str, Any]) -> str:
        """格式化消息内容
        
        Args:
            message: 原始消息
            
        Returns:
            格式化后的消息内容
        """
        title = message.get("title", "告警通知")
        content = message.get("content", "")
        severity = message.get("severity", "info")
        timestamp = message.get("timestamp", "")
        
        formatted = f"【{severity.upper()}】{title}\n"
        if content:
            formatted += f"\n{content}\n"
        if timestamp:
            formatted += f"\n时间: {timestamp}"
        
        return formatted