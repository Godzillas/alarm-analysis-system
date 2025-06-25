"""
Webhook通知器
"""

import aiohttp
import asyncio
from typing import Dict, Any
from .base_notifier import BaseNotifier


class WebhookNotifier(BaseNotifier):
    """Webhook通知器"""
    
    async def send_message(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """发送Webhook消息"""
        try:
            url = config["url"]
            method = config.get("method", "POST").upper()
            headers = config.get("headers", {})
            timeout = config.get("timeout", 30)
            
            # 准备请求数据
            payload = self._prepare_payload(config, message)
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                if method == "POST":
                    async with session.post(url, json=payload, headers=headers) as response:
                        response_text = await response.text()
                        
                        if response.status >= 400:
                            raise Exception(f"HTTP {response.status}: {response_text}")
                        
                        self.logger.info(f"Webhook发送成功: {url}")
                        return {
                            "success": True,
                            "message": f"Webhook发送成功，状态码: {response.status}",
                            "response": response_text[:500]  # 限制响应长度
                        }
                        
                elif method == "GET":
                    # GET请求将参数作为查询参数
                    async with session.get(url, params=payload, headers=headers) as response:
                        response_text = await response.text()
                        
                        if response.status >= 400:
                            raise Exception(f"HTTP {response.status}: {response_text}")
                        
                        self.logger.info(f"Webhook发送成功: {url}")
                        return {
                            "success": True,
                            "message": f"Webhook发送成功，状态码: {response.status}",
                            "response": response_text[:500]
                        }
                else:
                    raise Exception(f"不支持的HTTP方法: {method}")
            
        except asyncio.TimeoutError:
            error_msg = f"Webhook请求超时: {url}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"Webhook发送失败: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def send_test_message(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """发送测试Webhook"""
        test_message = {
            **message,
            "title": f"[测试] {message.get('title', '告警通知')}",
            "content": f"{message.get('content', '')}\n\n这是一条测试消息，请忽略。",
            "is_test": True
        }
        return await self.send_message(config, test_message)
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证Webhook配置"""
        url = config.get("url", "")
        if not url or not url.startswith(("http://", "https://")):
            return False
        
        method = config.get("method", "POST").upper()
        if method not in ["GET", "POST", "PUT", "PATCH"]:
            return False
        
        return True
    
    def _prepare_payload(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """准备请求载荷"""
        # 默认载荷格式
        payload = {
            "title": message.get("title", ""),
            "content": message.get("content", ""),
            "severity": message.get("severity", "info"),
            "timestamp": message.get("timestamp", ""),
            "is_test": message.get("is_test", False)
        }
        
        # 如果配置中指定了自定义载荷格式
        custom_payload = config.get("payload_template")
        if custom_payload:
            try:
                # 支持简单的模板替换
                import json
                if isinstance(custom_payload, dict):
                    payload.update(custom_payload)
                elif isinstance(custom_payload, str):
                    # 尝试作为JSON模板解析
                    template = json.loads(custom_payload)
                    if isinstance(template, dict):
                        payload.update(template)
            except Exception as e:
                self.logger.warning(f"自定义载荷模板解析失败: {str(e)}")
        
        # 添加额外字段
        extra_fields = config.get("extra_fields", {})
        if isinstance(extra_fields, dict):
            payload.update(extra_fields)
        
        return payload