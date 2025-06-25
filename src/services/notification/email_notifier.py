"""
邮件通知适配器
支持发送HTML格式的告警邮件
"""

import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, Optional, List
from datetime import datetime
import jinja2
import logging

from src.models.alarm import AlarmTable
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EmailNotifier:
    """邮件通知器"""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        use_tls: bool = True,
        from_email: str = "",
        from_name: str = "告警系统"
    ):
        """
        初始化邮件通知器
        
        Args:
            smtp_host: SMTP服务器地址
            smtp_port: SMTP端口
            username: 用户名
            password: 密码
            use_tls: 是否使用TLS
            from_email: 发件人邮箱
            from_name: 发件人名称
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_email = from_email or username
        self.from_name = from_name
        
        # 初始化Jinja2模板环境
        self.template_env = jinja2.Environment(
            loader=jinja2.DictLoader(self._get_email_templates())
        )
    
    def _get_email_templates(self) -> Dict[str, str]:
        """获取邮件模板"""
        return {
            "alarm_notification": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>告警通知</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header.critical { background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); }
        .header.high { background: linear-gradient(135deg, #ffa726 0%, #ff9800 100%); }
        .header.medium { background: linear-gradient(135deg, #ffeb3b 0%, #ffc107 100%); color: #333; }
        .header.low { background: linear-gradient(135deg, #42a5f5 0%, #2196f3 100%); }
        .header.info { background: linear-gradient(135deg, #78909c 0%, #607d8b 100%); }
        
        .content {
            padding: 30px;
        }
        .alarm-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #2c3e50;
        }
        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 20px 0;
        }
        .info-item {
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }
        .info-item.critical { border-left-color: #ff6b6b; }
        .info-item.high { border-left-color: #ffa726; }
        .info-item.medium { border-left-color: #ffeb3b; }
        .info-item.low { border-left-color: #42a5f5; }
        .info-item.info { border-left-color: #78909c; }
        
        .info-label {
            font-weight: bold;
            color: #5a6c7d;
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        .info-value {
            font-size: 16px;
            color: #2c3e50;
        }
        .description {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
            white-space: pre-wrap;
        }
        .tags {
            margin: 20px 0;
        }
        .tag {
            display: inline-block;
            background-color: #e3f2fd;
            color: #1976d2;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin: 2px;
        }
        .actions {
            text-align: center;
            margin: 30px 0;
        }
        .btn {
            display: inline-block;
            padding: 12px 24px;
            background-color: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            margin: 0 10px;
            font-weight: 500;
        }
        .btn:hover {
            background-color: #5a67d8;
        }
        .footer {
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-size: 14px;
        }
        @media (max-width: 600px) {
            .info-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header {{ severity }}">
            <h1>{{ status_icon }} 告警通知</h1>
            <p>{{ severity_text }} | {{ source }}</p>
        </div>
        
        <div class="content">
            <div class="alarm-title">{{ title }}</div>
            
            <div class="info-grid">
                <div class="info-item {{ severity }}">
                    <div class="info-label">严重程度</div>
                    <div class="info-value">{{ severity.upper() }}</div>
                </div>
                <div class="info-item {{ severity }}">
                    <div class="info-label">状态</div>
                    <div class="info-value">{{ status.upper() }}</div>
                </div>
                <div class="info-item {{ severity }}">
                    <div class="info-label">来源</div>
                    <div class="info-value">{{ source }}</div>
                </div>
                <div class="info-item {{ severity }}">
                    <div class="info-label">时间</div>
                    <div class="info-value">{{ created_at }}</div>
                </div>
            </div>
            
            {% if description %}
            <div class="description">
                <strong>详细描述:</strong><br>
                {{ description }}
            </div>
            {% endif %}
            
            {% if tags %}
            <div class="tags">
                <strong>标签:</strong><br>
                {% for key, value in tags.items() %}
                <span class="tag">{{ key }}: {{ value }}</span>
                {% endfor %}
            </div>
            {% endif %}
            
            {% if rule_name %}
            <div class="info-item {{ severity }}">
                <div class="info-label">触发规则</div>
                <div class="info-value">{{ rule_name }}</div>
            </div>
            {% endif %}
            
            <div class="actions">
                <a href="{{ detail_url }}" class="btn">查看详情</a>
                {% if dashboard_url %}
                <a href="{{ dashboard_url }}" class="btn">Dashboard</a>
                {% endif %}
            </div>
        </div>
        
        <div class="footer">
            <p>此邮件由告警监控系统自动发送</p>
            <p>发送时间: {{ now }}</p>
            {% if user_info %}
            <p>通知用户: {{ user_info.name or user_info.username }}</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
            """,
            "alarm_summary": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>告警汇总报告</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .content {
            padding: 30px;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .summary-card {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #667eea;
        }
        .summary-card.critical { border-left-color: #ff6b6b; }
        .summary-card.high { border-left-color: #ffa726; }
        .summary-card.medium { border-left-color: #ffeb3b; }
        .summary-card.low { border-left-color: #42a5f5; }
        
        .summary-number {
            font-size: 36px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        .summary-label {
            font-size: 14px;
            color: #6c757d;
            text-transform: uppercase;
        }
        .chart-section {
            margin: 30px 0;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }
        .trend-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #e9ecef;
        }
        .trend-item:last-child {
            border-bottom: none;
        }
        .footer {
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {{ time_desc }}告警汇总报告</h1>
            <p>总计 {{ total_alarms }} 条告警</p>
        </div>
        
        <div class="content">
            <h2>严重程度分布</h2>
            <div class="summary-grid">
                <div class="summary-card critical">
                    <div class="summary-number">{{ severity_counts.critical or 0 }}</div>
                    <div class="summary-label">Critical</div>
                </div>
                <div class="summary-card high">
                    <div class="summary-number">{{ severity_counts.high or 0 }}</div>
                    <div class="summary-label">High</div>
                </div>
                <div class="summary-card medium">
                    <div class="summary-number">{{ severity_counts.medium or 0 }}</div>
                    <div class="summary-label">Medium</div>
                </div>
                <div class="summary-card low">
                    <div class="summary-number">{{ (severity_counts.low or 0) + (severity_counts.info or 0) }}</div>
                    <div class="summary-label">Low/Info</div>
                </div>
            </div>
            
            <h2>状态分布</h2>
            <div class="chart-section">
                {% for status, count in status_counts.items() %}
                <div class="trend-item">
                    <span>{{ status.upper() }}</span>
                    <span><strong>{{ count }}</strong></span>
                </div>
                {% endfor %}
            </div>
            
            <h2>告警来源</h2>
            <div class="chart-section">
                {% for source, count in source_counts.items() %}
                <div class="trend-item">
                    <span>{{ source }}</span>
                    <span><strong>{{ count }}</strong></span>
                </div>
                {% endfor %}
            </div>
            
            {% if top_alarms %}
            <h2>关键告警</h2>
            <div class="chart-section">
                {% for alarm in top_alarms %}
                <div class="trend-item">
                    <span>{{ alarm.title[:50] }}{% if alarm.title|length > 50 %}...{% endif %}</span>
                    <span class="tag {{ alarm.severity }}">{{ alarm.severity.upper() }}</span>
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
        
        <div class="footer">
            <p>此邮件由告警监控系统自动发送</p>
            <p>发送时间: {{ now }}</p>
        </div>
    </div>
</body>
</html>
            """
        }
    
    async def send_alarm_notification(
        self,
        alarm: AlarmTable,
        to_emails: List[str],
        user_info: Optional[Dict[str, Any]] = None,
        rule_name: Optional[str] = None
    ) -> bool:
        """
        发送告警通知邮件
        
        Args:
            alarm: 告警对象
            to_emails: 收件人邮箱列表
            user_info: 用户信息
            rule_name: 触发的规则名称
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 构建邮件内容
            subject = self._build_subject(alarm)
            html_content = self._build_alarm_html(alarm, user_info, rule_name)
            
            # 发送邮件
            success = await self._send_email(to_emails, subject, html_content)
            
            if success:
                logger.info(f"Email notification sent successfully for alarm: {alarm.title}")
            else:
                logger.error(f"Failed to send email notification for alarm: {alarm.title}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False
    
    def _build_subject(self, alarm: AlarmTable) -> str:
        """构建邮件主题"""
        # 状态图标
        status_icons = {
            "active": "🔥",
            "resolved": "✅", 
            "acknowledged": "👀"
        }
        status_icon = status_icons.get(alarm.status, "⚠️")
        
        # 严重程度前缀
        severity_prefix = {
            "critical": "[CRITICAL]",
            "high": "[HIGH]",
            "medium": "[MEDIUM]", 
            "low": "[LOW]",
            "info": "[INFO]"
        }
        prefix = severity_prefix.get(alarm.severity, "[ALERT]")
        
        return f"{status_icon} {prefix} {alarm.title[:50]}{'...' if len(alarm.title) > 50 else ''}"
    
    def _build_alarm_html(
        self,
        alarm: AlarmTable,
        user_info: Optional[Dict[str, Any]] = None,
        rule_name: Optional[str] = None
    ) -> str:
        """构建告警邮件HTML内容"""
        
        # 状态图标
        status_icons = {
            "active": "🔥",
            "resolved": "✅",
            "acknowledged": "👀"
        }
        
        # 严重程度文本
        severity_text = {
            "critical": "严重",
            "high": "高",
            "medium": "中",
            "low": "低", 
            "info": "信息"
        }
        
        template = self.template_env.get_template("alarm_notification")
        
        return template.render(
            title=alarm.title,
            description=alarm.description,
            severity=alarm.severity,
            severity_text=severity_text.get(alarm.severity, alarm.severity),
            status=alarm.status,
            status_icon=status_icons.get(alarm.status, "⚠️"),
            source=alarm.source,
            tags=alarm.tags or {},
            created_at=alarm.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            rule_name=rule_name,
            user_info=user_info,
            detail_url=f"/alarms/{alarm.id}",
            dashboard_url=alarm.metadata.get("dashboard_url") if alarm.metadata else None,
            now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    
    async def send_summary_notification(
        self,
        alarms: List[AlarmTable],
        to_emails: List[str],
        summary_type: str = "daily",
        user_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送告警汇总邮件
        
        Args:
            alarms: 告警列表
            to_emails: 收件人邮箱列表
            summary_type: 汇总类型（daily/weekly/monthly）
            user_info: 用户信息
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 构建邮件内容
            subject = self._build_summary_subject(alarms, summary_type)
            html_content = self._build_summary_html(alarms, summary_type, user_info)
            
            # 发送邮件
            success = await self._send_email(to_emails, subject, html_content)
            
            if success:
                logger.info(f"Summary email notification sent successfully")
            else:
                logger.error(f"Failed to send summary email notification")
                
            return success
            
        except Exception as e:
            logger.error(f"Error sending summary email notification: {e}")
            return False
    
    def _build_summary_subject(self, alarms: List[AlarmTable], summary_type: str) -> str:
        """构建汇总邮件主题"""
        time_mapping = {
            "daily": "日",
            "weekly": "周",
            "monthly": "月"
        }
        time_desc = time_mapping.get(summary_type, "期间")
        return f"📊 {time_desc}告警汇总报告 - 共{len(alarms)}条告警"
    
    def _build_summary_html(
        self,
        alarms: List[AlarmTable], 
        summary_type: str,
        user_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建汇总邮件HTML内容"""
        
        # 统计信息
        total_alarms = len(alarms)
        severity_counts = {}
        status_counts = {}
        source_counts = {}
        
        for alarm in alarms:
            severity_counts[alarm.severity] = severity_counts.get(alarm.severity, 0) + 1
            status_counts[alarm.status] = status_counts.get(alarm.status, 0) + 1
            source_counts[alarm.source] = source_counts.get(alarm.source, 0) + 1
        
        # 获取关键告警（critical和high）
        top_alarms = [alarm for alarm in alarms if alarm.severity in ["critical", "high"]][:10]
        
        # 时间描述
        time_mapping = {
            "daily": "日",
            "weekly": "周", 
            "monthly": "月"
        }
        time_desc = time_mapping.get(summary_type, "期间")
        
        template = self.template_env.get_template("alarm_summary")
        
        return template.render(
            time_desc=time_desc,
            total_alarms=total_alarms,
            severity_counts=severity_counts,
            status_counts=status_counts,
            source_counts=source_counts,
            top_alarms=top_alarms,
            user_info=user_info,
            now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    
    async def _send_email(self, to_emails: List[str], subject: str, html_content: str) -> bool:
        """发送邮件"""
        try:
            # 在异步环境中运行同步代码
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._send_email_sync,
                to_emails,
                subject, 
                html_content
            )
        except Exception as e:
            logger.error(f"Error in async email sending: {e}")
            return False
    
    def _send_email_sync(self, to_emails: List[str], subject: str, html_content: str) -> bool:
        """同步发送邮件"""
        try:
            # 创建邮件消息
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = ", ".join(to_emails)
            
            # 添加HTML内容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 连接SMTP服务器
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                if self.username and self.password:
                    server.login(self.username, self.password)
                
                # 发送邮件
                server.send_message(msg, to_addrs=to_emails)
                
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    async def test_connection(self, test_email: str) -> bool:
        """测试邮件连接"""
        try:
            subject = "🔔 告警系统邮件连接测试"
            content = """
            <html>
            <body>
                <h2>告警系统连接测试</h2>
                <p>如果您收到这封邮件，说明邮件通知功能正常工作。</p>
                <p>发送时间: {}</p>
            </body>
            </html>
            """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            return await self._send_email([test_email], subject, content)
            
        except Exception as e:
            logger.error(f"Error testing email connection: {e}")
            return False
    
    async def send_batch_notifications(
        self,
        alarms: List[AlarmTable],
        to_emails: List[str],
        user_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        批量发送告警通知
        
        Args:
            alarms: 告警列表
            to_emails: 收件人邮箱列表
            user_info: 用户信息
            
        Returns:
            Dict[str, bool]: 每个告警的发送结果
        """
        results = {}
        
        # 限制并发数量，避免SMTP服务器过载
        semaphore = asyncio.Semaphore(3)
        
        async def send_single(alarm):
            async with semaphore:
                success = await self.send_alarm_notification(alarm, to_emails, user_info)
                results[str(alarm.id)] = success
                # 避免频率限制
                await asyncio.sleep(1)
        
        # 并发发送
        tasks = [send_single(alarm) for alarm in alarms]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results