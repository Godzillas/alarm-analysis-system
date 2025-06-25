"""
邮件通知器
"""

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from .base_notifier import BaseNotifier


class EmailNotifier(BaseNotifier):
    """邮件通知器"""
    
    async def send_message(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """发送邮件消息"""
        try:
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._send_email_sync, 
                config, 
                message
            )
            return result
            
        except Exception as e:
            self.logger.error(f"发送邮件失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_test_message(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """发送测试邮件"""
        test_message = {
            **message,
            "title": f"[测试] {message.get('title', '告警通知')}",
            "content": f"{message.get('content', '')}\n\n这是一条测试消息，请忽略。"
        }
        return await self.send_message(config, test_message)
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证邮件配置"""
        required_fields = ["smtp_server", "smtp_port", "username", "password", "to_addresses"]
        
        for field in required_fields:
            if field not in config:
                return False
        
        # 验证邮箱地址格式
        to_addresses = config.get("to_addresses", [])
        if not isinstance(to_addresses, list) or not to_addresses:
            return False
        
        return True
    
    def _send_email_sync(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """同步发送邮件"""
        try:
            smtp_server = config["smtp_server"]
            smtp_port = config["smtp_port"]
            username = config["username"]
            password = config["password"]
            to_addresses = config["to_addresses"]
            from_address = config.get("from_address", username)
            
            # 创建邮件内容
            msg = MIMEMultipart()
            msg["From"] = from_address
            msg["To"] = ", ".join(to_addresses)
            msg["Subject"] = message.get("title", "告警通知")
            
            # 邮件正文
            body = self.format_message(message)
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            # 连接SMTP服务器并发送
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                # 如果需要TLS
                if config.get("use_tls", True):
                    server.starttls()
                
                # 登录
                server.login(username, password)
                
                # 发送邮件
                text = msg.as_string()
                server.sendmail(from_address, to_addresses, text)
            
            self.logger.info(f"邮件发送成功，收件人: {', '.join(to_addresses)}")
            return {
                "success": True, 
                "message": f"邮件已发送到 {len(to_addresses)} 个地址"
            }
            
        except Exception as e:
            self.logger.error(f"邮件发送失败: {str(e)}")
            return {"success": False, "error": str(e)}