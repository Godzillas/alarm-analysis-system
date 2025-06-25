"""
飞书Webhook通知适配器
支持发送富文本告警消息到飞书群聊
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
import logging

from src.models.alarm import AlarmTable
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FeishuWebhookNotifier:
    """飞书Webhook通知器"""
    
    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        """
        初始化飞书通知器
        
        Args:
            webhook_url: 飞书机器人Webhook URL
            secret: 飞书机器人签名密钥（可选）
        """
        self.webhook_url = webhook_url
        self.secret = secret
        self.session = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def send_alarm_notification(
        self, 
        alarm: AlarmTable, 
        user_info: Optional[Dict[str, Any]] = None,
        rule_name: Optional[str] = None
    ) -> bool:
        """
        发送告警通知
        
        Args:
            alarm: 告警对象
            user_info: 用户信息
            rule_name: 触发的规则名称
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 构建消息内容
            message = self._build_alarm_message(alarm, user_info, rule_name)
            
            # 发送消息
            success = await self._send_message(message)
            
            if success:
                logger.info(f"Feishu notification sent successfully for alarm: {alarm.title}")
            else:
                logger.error(f"Failed to send Feishu notification for alarm: {alarm.title}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error sending Feishu notification: {e}")
            return False
    
    def _build_alarm_message(
        self, 
        alarm: AlarmTable, 
        user_info: Optional[Dict[str, Any]] = None,
        rule_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """构建告警消息"""
        
        # 根据严重程度设置颜色
        color_mapping = {
            "critical": "red",
            "high": "orange", 
            "medium": "yellow",
            "low": "blue",
            "info": "grey"
        }
        color = color_mapping.get(alarm.severity, "grey")
        
        # 状态图标
        status_icons = {
            "active": "🔥",
            "resolved": "✅",
            "acknowledged": "👀"
        }
        status_icon = status_icons.get(alarm.status, "⚠️")
        
        # 严重程度图标
        severity_icons = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "📢",
            "low": "ℹ️",
            "info": "💡"
        }
        severity_icon = severity_icons.get(alarm.severity, "⚠️")
        
        # 构建卡片消息
        card_message = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True,
                    "enable_forward": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"{status_icon} 告警通知"
                    },
                    "template": color
                },
                "elements": [
                    # 告警标题
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**{severity_icon} {alarm.title}**"
                        }
                    },
                    # 分割线
                    {
                        "tag": "hr"
                    },
                    # 基本信息
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**严重程度**\n{alarm.severity.upper()}"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**状态**\n{alarm.status.upper()}"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**来源**\n{alarm.source}"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**时间**\n{alarm.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                                }
                            }
                        ]
                    }
                ]
            }
        }
        
        # 添加描述信息
        if alarm.description:
            card_message["card"]["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**详情**\n{alarm.description[:500]}{'...' if len(alarm.description) > 500 else ''}"
                }
            })
        
        # 添加标签信息
        if alarm.tags:
            tag_info = self._format_tags(alarm.tags)
            if tag_info:
                card_message["card"]["elements"].extend([
                    {"tag": "hr"},
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**标签信息**\n{tag_info}"
                        }
                    }
                ])
        
        # 添加规则信息
        if rule_name:
            card_message["card"]["elements"].extend([
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**触发规则**\n{rule_name}"
                    }
                }
            ])
        
        # 添加用户信息
        if user_info:
            user_name = user_info.get("name", user_info.get("username", "未知用户"))
            card_message["card"]["elements"].extend([
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**通知用户**\n@{user_name}"
                    }
                }
            ])
        
        # 添加操作按钮
        actions = self._build_action_buttons(alarm)
        if actions:
            card_message["card"]["elements"].extend([
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": actions
                }
            ])
        
        return card_message
    
    def _format_tags(self, tags: Dict[str, Any]) -> str:
        """格式化标签信息"""
        tag_lines = []
        
        # 重要标签优先显示
        important_tags = ["environment", "service", "instance", "team", "system"]
        
        for tag in important_tags:
            if tag in tags and tags[tag]:
                tag_lines.append(f"• {tag}: {tags[tag]}")
        
        # 添加其他标签
        for key, value in tags.items():
            if key not in important_tags and value:
                tag_lines.append(f"• {key}: {value}")
        
        return "\n".join(tag_lines[:10])  # 最多显示10个标签
    
    def _build_action_buttons(self, alarm: AlarmTable) -> List[Dict[str, Any]]:
        """构建操作按钮"""
        buttons = []
        
        # 确认按钮（如果告警是活动状态）
        if alarm.status == "active":
            buttons.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "确认告警"
                },
                "type": "primary",
                "value": {
                    "action": "acknowledge",
                    "alarm_id": str(alarm.id)
                }
            })
        
        # 查看详情按钮
        buttons.append({
            "tag": "button", 
            "text": {
                "tag": "plain_text",
                "content": "查看详情"
            },
            "type": "default",
            "url": f"/alarms/{alarm.id}"
        })
        
        # Dashboard链接（如果有的话）
        if alarm.metadata and "dashboard_url" in alarm.metadata:
            buttons.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text", 
                    "content": "Dashboard"
                },
                "type": "default",
                "url": alarm.metadata["dashboard_url"]
            })
        
        return buttons
    
    async def _send_message(self, message: Dict[str, Any]) -> bool:
        """发送消息到飞书"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # 添加签名（如果有密钥）
            headers = {"Content-Type": "application/json"}
            if self.secret:
                # 飞书签名验证逻辑
                timestamp = str(int(datetime.now().timestamp()))
                sign = self._generate_sign(timestamp)
                message["timestamp"] = timestamp
                message["sign"] = sign
            
            async with self.session.post(
                self.webhook_url,
                json=message,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("StatusCode") == 0:
                        return True
                    else:
                        logger.error(f"Feishu API error: {result}")
                        return False
                else:
                    logger.error(f"Feishu webhook request failed: {response.status}")
                    return False
                    
        except asyncio.TimeoutError:
            logger.error("Feishu webhook request timeout")
            return False
        except Exception as e:
            logger.error(f"Error sending message to Feishu: {e}")
            return False
    
    def _generate_sign(self, timestamp: str) -> str:
        """生成飞书签名"""
        import hmac
        import hashlib
        import base64
        
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return sign
    
    async def send_batch_notifications(
        self, 
        alarms: List[AlarmTable], 
        user_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        批量发送告警通知
        
        Args:
            alarms: 告警列表
            user_info: 用户信息
            
        Returns:
            Dict[str, bool]: 每个告警的发送结果
        """
        results = {}
        
        # 限制并发数量
        semaphore = asyncio.Semaphore(5)
        
        async def send_single(alarm):
            async with semaphore:
                success = await self.send_alarm_notification(alarm, user_info)
                results[str(alarm.id)] = success
                # 避免频率限制
                await asyncio.sleep(0.5)
        
        # 并发发送
        tasks = [send_single(alarm) for alarm in alarms]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def send_summary_notification(
        self, 
        alarms: List[AlarmTable],
        summary_type: str = "daily",
        user_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送告警汇总通知
        
        Args:
            alarms: 告警列表
            summary_type: 汇总类型（daily/weekly/monthly）
            user_info: 用户信息
            
        Returns:
            bool: 发送是否成功
        """
        try:
            message = self._build_summary_message(alarms, summary_type, user_info)
            return await self._send_message(message)
        except Exception as e:
            logger.error(f"Error sending summary notification: {e}")
            return False
    
    def _build_summary_message(
        self, 
        alarms: List[AlarmTable],
        summary_type: str,
        user_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """构建汇总消息"""
        
        # 统计信息
        total_alarms = len(alarms)
        severity_counts = {}
        status_counts = {}
        source_counts = {}
        
        for alarm in alarms:
            severity_counts[alarm.severity] = severity_counts.get(alarm.severity, 0) + 1
            status_counts[alarm.status] = status_counts.get(alarm.status, 0) + 1 
            source_counts[alarm.source] = source_counts.get(alarm.source, 0) + 1
        
        # 时间范围
        time_mapping = {
            "daily": "日",
            "weekly": "周", 
            "monthly": "月"
        }
        time_desc = time_mapping.get(summary_type, "期间")
        
        # 构建汇总卡片
        card_message = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True,
                    "enable_forward": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"📊 {time_desc}告警汇总报告"
                    },
                    "template": "blue"
                },
                "elements": [
                    # 总体统计
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**总计告警数量**: {total_alarms}"
                        }
                    },
                    {"tag": "hr"},
                    # 严重程度分布
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md", 
                            "content": "**严重程度分布**"
                        }
                    },
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"🚨 Critical: {severity_counts.get('critical', 0)}"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"⚠️ High: {severity_counts.get('high', 0)}"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md", 
                                    "content": f"📢 Medium: {severity_counts.get('medium', 0)}"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"ℹ️ Low/Info: {severity_counts.get('low', 0) + severity_counts.get('info', 0)}"
                                }
                            }
                        ]
                    }
                ]
            }
        }
        
        # 添加状态分布
        if status_counts:
            card_message["card"]["elements"].extend([
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**状态分布**"
                    }
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"🔥 Active: {status_counts.get('active', 0)}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"✅ Resolved: {status_counts.get('resolved', 0)}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"👀 Acknowledged: {status_counts.get('acknowledged', 0)}"
                            }
                        }
                    ]
                }
            ])
        
        # 添加来源分布
        if source_counts:
            source_info = "\n".join([f"• {source}: {count}" for source, count in source_counts.items()])
            card_message["card"]["elements"].extend([
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**告警来源**\n{source_info}"
                    }
                }
            ])
        
        return card_message
    
    async def test_connection(self) -> bool:
        """测试连接"""
        test_message = {
            "msg_type": "text",
            "content": {
                "text": "🔔 告警系统连接测试成功！"
            }
        }
        
        return await self._send_message(test_message)