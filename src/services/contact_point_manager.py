"""
联络点管理服务
"""

import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from src.models.alarm import ContactPoint, ContactPointType, System
from src.utils.logger import get_logger
from src.core.database import async_session_maker


class ContactPointManager:
    """联络点管理器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._notifiers = {}
        self._initialize_notifiers()
    
    def _initialize_notifiers(self):
        """初始化通知器"""
        from src.services.notifiers.email_notifier import EmailNotifier
        from src.services.notifiers.webhook_notifier import WebhookNotifier
        from src.services.notifiers.feishu_notifier import FeishuNotifier
        
        self._notifiers = {
            ContactPointType.EMAIL: EmailNotifier(),
            ContactPointType.WEBHOOK: WebhookNotifier(),
            ContactPointType.FEISHU: FeishuNotifier(),
            # 其他通知器可以在这里添加
        }
    
    async def create_contact_point(
        self,
        name: str,
        contact_type: ContactPointType,
        config: Dict[str, Any],
        system_id: Optional[int] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> ContactPoint:
        """创建联络点"""
        async with async_session_maker() as db:
            try:
                # 检查名称是否已存在
                existing = await db.execute(
                    select(ContactPoint).where(ContactPoint.name == name)
                )
                if existing.scalar_one_or_none():
                    raise ValueError(f"联络点名称 '{name}' 已存在")
                
                # 验证配置
                await self._validate_config(contact_type, config)
                
                # 创建联络点
                contact_point = ContactPoint(
                    name=name,
                    description=description,
                    contact_type=contact_type.value,
                    config=config,
                    system_id=system_id,
                    **kwargs
                )
                
                db.add(contact_point)
                await db.commit()
                await db.refresh(contact_point)
                
                self.logger.info(f"创建联络点成功: {name} ({contact_type.value})")
                return contact_point
                
            except Exception as e:
                await db.rollback()
                self.logger.error(f"创建联络点失败: {str(e)}")
                raise
    
    async def update_contact_point(
        self,
        contact_point_id: int,
        **update_data
    ) -> ContactPoint:
        """更新联络点"""
        async with async_session_maker() as db:
            try:
                contact_point = await db.get(ContactPoint, contact_point_id)
                if not contact_point:
                    raise ValueError(f"联络点 ID {contact_point_id} 不存在")
                
                # 验证配置更新
                if 'config' in update_data:
                    contact_type = ContactPointType(contact_point.contact_type)
                    await self._validate_config(contact_type, update_data['config'])
                
                # 更新字段
                for field, value in update_data.items():
                    if hasattr(contact_point, field):
                        setattr(contact_point, field, value)
                
                contact_point.updated_at = datetime.utcnow()
                await db.commit()
                await db.refresh(contact_point)
                
                self.logger.info(f"更新联络点成功: {contact_point.name}")
                return contact_point
                
            except Exception as e:
                await db.rollback()
                self.logger.error(f"更新联络点失败: {str(e)}")
                raise
    
    async def delete_contact_point(self, contact_point_id: int) -> bool:
        """删除联络点"""
        async with async_session_maker() as db:
            try:
                contact_point = await db.get(ContactPoint, contact_point_id)
                if not contact_point:
                    raise ValueError(f"联络点 ID {contact_point_id} 不存在")
                
                # 检查是否有关联的规则或模板
                # TODO: 实现关联检查
                
                await db.delete(contact_point)
                await db.commit()
                
                self.logger.info(f"删除联络点成功: {contact_point.name}")
                return True
                
            except Exception as e:
                await db.rollback()
                self.logger.error(f"删除联络点失败: {str(e)}")
                raise
    
    async def get_contact_points(
        self,
        system_id: Optional[int] = None,
        contact_type: Optional[ContactPointType] = None,
        enabled: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ContactPoint]:
        """获取联络点列表"""
        async with async_session_maker() as db:
            try:
                query = select(ContactPoint).options(selectinload(ContactPoint.system))
                
                conditions = []
                if system_id is not None:
                    conditions.append(ContactPoint.system_id == system_id)
                if contact_type is not None:
                    conditions.append(ContactPoint.contact_type == contact_type.value)
                if enabled is not None:
                    conditions.append(ContactPoint.enabled == enabled)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                query = query.offset(skip).limit(limit)
                query = query.order_by(ContactPoint.created_at.desc())
                
                result = await db.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                self.logger.error(f"获取联络点列表失败: {str(e)}")
                raise
    
    async def get_contact_point_by_id(self, contact_point_id: int) -> Optional[ContactPoint]:
        """根据ID获取联络点"""
        async with async_session_maker() as db:
            try:
                query = select(ContactPoint).options(selectinload(ContactPoint.system))
                query = query.where(ContactPoint.id == contact_point_id)
                
                result = await db.execute(query)
                return result.scalar_one_or_none()
                
            except Exception as e:
                self.logger.error(f"获取联络点失败: {str(e)}")
                raise
    
    async def test_contact_point(self, contact_point_id: int) -> Dict[str, Any]:
        """测试联络点连接"""
        try:
            contact_point = await self.get_contact_point_by_id(contact_point_id)
            if not contact_point:
                return {"success": False, "error": "联络点不存在"}
            
            if not contact_point.enabled:
                return {"success": False, "error": "联络点已禁用"}
            
            contact_type = ContactPointType(contact_point.contact_type)
            notifier = self._notifiers.get(contact_type)
            
            if not notifier:
                return {"success": False, "error": f"不支持的联络点类型: {contact_type.value}"}
            
            # 发送测试消息
            test_message = {
                "title": "测试消息",
                "content": f"这是来自联络点 '{contact_point.name}' 的测试消息",
                "timestamp": datetime.utcnow().isoformat(),
                "severity": "info"
            }
            
            result = await notifier.send_test_message(contact_point.config, test_message)
            
            # 更新统计信息
            await self._update_contact_point_stats(contact_point_id, result["success"])
            
            return result
            
        except Exception as e:
            self.logger.error(f"测试联络点失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_notification(
        self,
        contact_point_id: int,
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """发送通知"""
        try:
            contact_point = await self.get_contact_point_by_id(contact_point_id)
            if not contact_point:
                return {"success": False, "error": "联络点不存在"}
            
            if not contact_point.enabled:
                return {"success": False, "error": "联络点已禁用"}
            
            contact_type = ContactPointType(contact_point.contact_type)
            notifier = self._notifiers.get(contact_type)
            
            if not notifier:
                return {"success": False, "error": f"不支持的联络点类型: {contact_type.value}"}
            
            # 发送消息
            result = await notifier.send_message(contact_point.config, message)
            
            # 更新统计信息
            await self._update_contact_point_stats(contact_point_id, result["success"])
            
            return result
            
        except Exception as e:
            self.logger.error(f"发送通知失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _validate_config(self, contact_type: ContactPointType, config: Dict[str, Any]):
        """验证联络点配置"""
        required_fields = {
            ContactPointType.EMAIL: ["smtp_server", "smtp_port", "username", "password", "to_addresses"],
            ContactPointType.WEBHOOK: ["url"],
            ContactPointType.FEISHU: ["webhook_url"],
            ContactPointType.SLACK: ["webhook_url"],
            ContactPointType.TEAMS: ["webhook_url"],
            ContactPointType.DINGTALK: ["webhook_url"],
            ContactPointType.SMS: ["api_key", "api_secret", "phone_numbers"],
            ContactPointType.WECHAT: ["corp_id", "corp_secret", "agent_id", "to_users"]
        }
        
        required = required_fields.get(contact_type, [])
        missing = [field for field in required if field not in config]
        
        if missing:
            raise ValueError(f"联络点配置缺少必需字段: {', '.join(missing)}")
        
        # 特定类型的配置验证
        if contact_type == ContactPointType.EMAIL:
            if not isinstance(config.get("to_addresses"), list):
                raise ValueError("to_addresses 必须是邮箱地址列表")
        
        elif contact_type == ContactPointType.WEBHOOK:
            if not config.get("url", "").startswith(("http://", "https://")):
                raise ValueError("webhook URL 必须以 http:// 或 https:// 开头")
        
        elif contact_type == ContactPointType.SMS:
            if not isinstance(config.get("phone_numbers"), list):
                raise ValueError("phone_numbers 必须是手机号码列表")
    
    async def _update_contact_point_stats(self, contact_point_id: int, success: bool):
        """更新联络点统计信息"""
        async with async_session_maker() as db:
            try:
                contact_point = await db.get(ContactPoint, contact_point_id)
                if not contact_point:
                    return
                
                contact_point.total_sent += 1
                contact_point.last_sent = datetime.utcnow()
                
                if success:
                    contact_point.success_count += 1
                    contact_point.last_success = datetime.utcnow()
                else:
                    contact_point.failure_count += 1
                    contact_point.last_failure = datetime.utcnow()
                
                await db.commit()
                
            except Exception as e:
                await db.rollback()
                self.logger.error(f"更新联络点统计失败: {str(e)}")
    
    async def get_contact_point_stats(self, contact_point_id: int) -> Dict[str, Any]:
        """获取联络点统计信息"""
        try:
            contact_point = await self.get_contact_point_by_id(contact_point_id)
            if not contact_point:
                return {}
            
            success_rate = 0
            if contact_point.total_sent > 0:
                success_rate = (contact_point.success_count / contact_point.total_sent) * 100
            
            return {
                "contact_point_id": contact_point_id,
                "name": contact_point.name,
                "contact_type": contact_point.contact_type,
                "total_sent": contact_point.total_sent,
                "success_count": contact_point.success_count,
                "failure_count": contact_point.failure_count,
                "success_rate": round(success_rate, 2),
                "last_sent": contact_point.last_sent.isoformat() if contact_point.last_sent else None,
                "last_success": contact_point.last_success.isoformat() if contact_point.last_success else None,
                "last_failure": contact_point.last_failure.isoformat() if contact_point.last_failure else None,
                "enabled": contact_point.enabled
            }
            
        except Exception as e:
            self.logger.error(f"获取联络点统计失败: {str(e)}")
            return {}