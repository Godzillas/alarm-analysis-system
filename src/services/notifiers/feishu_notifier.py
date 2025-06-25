"""
飞书通知器
"""

import aiohttp
import asyncio
from typing import Dict, Any
from .base_notifier import BaseNotifier


class FeishuNotifier(BaseNotifier):
    """飞书通知器"""
    
    async def send_message(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """发送飞书消息"""
        try:
            webhook_url = config["webhook_url"]
            timeout = config.get("timeout", 30)
            
            # 准备飞书消息载荷
            payload = self._prepare_feishu_payload(config, message)
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.post(webhook_url, json=payload) as response:
                    response_data = await response.json()
                    
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {response_data}")
                    
                    # 检查飞书API响应
                    if response_data.get("code") != 0:
                        raise Exception(f"飞书API错误: {response_data.get('msg', '未知错误')}")
                    
                    self.logger.info(f"飞书消息发送成功")
                    return {
                        "success": True,
                        "message": "飞书消息发送成功",
                        "response": response_data
                    }
            
        except asyncio.TimeoutError:
            error_msg = "飞书消息发送超时"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"飞书消息发送失败: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def send_test_message(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """发送测试飞书消息"""
        test_message = {
            **message,
            "title": f"[测试] {message.get('title', '告警通知')}",
            "content": f"{message.get('content', '')}\n\n这是一条测试消息，请忽略。"
        }
        return await self.send_message(config, test_message)
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证飞书配置"""
        webhook_url = config.get("webhook_url", "")
        if not webhook_url or not webhook_url.startswith("https://"):
            return False
        
        return True
    
    def _prepare_feishu_payload(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """准备飞书消息载荷"""
        title = message.get("title", "告警通知")
        content = message.get("content", "")
        severity = message.get("severity", "info")
        timestamp = message.get("timestamp", "")
        
        # 根据严重程度选择颜色
        color_map = {
            "critical": "red",
            "high": "orange", 
            "medium": "yellow",
            "low": "green",
            "info": "blue"
        }
        color = color_map.get(severity, "blue")
        
        # 消息类型：text, rich_text, interactive
        msg_type = config.get("msg_type", "rich_text")
        
        if msg_type == "text":
            # 简单文本消息
            payload = {
                "msg_type": "text",
                "content": {
                    "text": self.format_message(message)
                }
            }
        
        elif msg_type == "rich_text":
            # 富文本消息
            elements = [
                {
                    "tag": "text",
                    "text": f"【{severity.upper()}】",
                    "style": {
                        "bold": True,
                        "text_color": color
                    }
                },
                {
                    "tag": "text", 
                    "text": title,
                    "style": {
                        "bold": True
                    }
                }
            ]
            
            if content:
                elements.append({
                    "tag": "text",
                    "text": f"\n\n{content}"
                })
            
            if timestamp:
                elements.append({
                    "tag": "text",
                    "text": f"\n\n时间: {timestamp}",
                    "style": {
                        "text_color": "grey"
                    }
                })
            
            payload = {
                "msg_type": "rich_text",
                "content": {
                    "rich_text": {
                        "elements": elements
                    }
                }
            }
        
        elif msg_type == "interactive":
            # 交互式卡片消息
            card_elements = [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**【{severity.upper()}】{title}**"
                    }
                }
            ]
            
            if content:
                card_elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": content
                    }
                })
            
            if timestamp:
                card_elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": f"时间: {timestamp}"
                    }
                })
            
            payload = {
                "msg_type": "interactive",
                "card": {
                    "config": {
                        "wide_screen_mode": True
                    },
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": "告警通知"
                        },
                        "template": color
                    },
                    "elements": card_elements
                }
            }
        
        else:
            # 默认使用文本消息
            payload = {
                "msg_type": "text",
                "content": {
                    "text": self.format_message(message)
                }
            }
        
        return payload