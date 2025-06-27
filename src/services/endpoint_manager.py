"""
接入点管理服务
"""

import asyncio
import json
import logging
import secrets
import string
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_maker
from src.models.alarm import Endpoint, EndpointType
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EndpointManager:
    def __init__(self):
        self.active_endpoints: Dict[int, Dict] = {}
        self.endpoint_stats: Dict[int, Dict] = {}
        self._initialized = False
        
    async def _initialize_enabled_endpoints(self):
        """初始化已启用的接入点"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Endpoint).where(Endpoint.enabled == True)
                )
                enabled_endpoints = result.scalars().all()
                
                for endpoint in enabled_endpoints:
                    await self._activate_endpoint(endpoint)
                    
                logger.info(f"Initialized {len(enabled_endpoints)} enabled endpoints")
                
        except Exception as e:
            logger.error(f"Failed to initialize enabled endpoints: {str(e)}")
        
    async def create_endpoint(self, endpoint_data: Dict[str, Any]) -> Optional[Endpoint]:
        """创建新的接入点"""
        try:
            async with async_session_maker() as session:
                endpoint = Endpoint(**endpoint_data)
                
                # 生成API令牌和接入URL
                endpoint.api_token = self._generate_api_token()
                endpoint.webhook_url = self._generate_webhook_url(endpoint.api_token)
                
                session.add(endpoint)
                await session.commit()
                await session.refresh(endpoint)
                
                if endpoint.enabled:
                    await self._activate_endpoint(endpoint)
                
                logger.info(f"Created endpoint: {endpoint.name} with URL: {endpoint.webhook_url}")
                return endpoint
                
        except Exception as e:
            logger.error(f"Failed to create endpoint: {str(e)}")
            return None
            
    async def update_endpoint(self, endpoint_id: int, update_data: Dict[str, Any]) -> Optional[Endpoint]:
        """更新接入点"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Endpoint).where(Endpoint.id == endpoint_id)
                )
                endpoint = result.scalars().first()
                
                if not endpoint:
                    return None
                    
                was_enabled = endpoint.enabled
                
                for key, value in update_data.items():
                    if hasattr(endpoint, key):
                        setattr(endpoint, key, value)
                        
                endpoint.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(endpoint)
                
                if was_enabled and not endpoint.enabled:
                    await self._deactivate_endpoint(endpoint_id)
                elif not was_enabled and endpoint.enabled:
                    await self._activate_endpoint(endpoint)
                elif endpoint.enabled:
                    await self._update_active_endpoint(endpoint)
                    
                logger.info(f"Updated endpoint: {endpoint.name}")
                return endpoint
                
        except Exception as e:
            logger.error(f"Failed to update endpoint {endpoint_id}: {str(e)}")
            return None
            
    async def delete_endpoint(self, endpoint_id: int) -> bool:
        """删除接入点"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Endpoint).where(Endpoint.id == endpoint_id)
                )
                endpoint = result.scalars().first()
                
                if not endpoint:
                    return False
                    
                await self._deactivate_endpoint(endpoint_id)
                
                await session.delete(endpoint)
                await session.commit()
                
                logger.info(f"Deleted endpoint: {endpoint.name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete endpoint {endpoint_id}: {str(e)}")
            return False
            
    async def get_endpoint(self, endpoint_id: int) -> Optional[Endpoint]:
        """获取单个接入点"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Endpoint).where(Endpoint.id == endpoint_id)
                )
                return result.scalars().first()
                
        except Exception as e:
            logger.error(f"Failed to get endpoint {endpoint_id}: {str(e)}")
            return None
            
    async def list_endpoints(self, endpoint_type: Optional[str] = None, enabled: Optional[bool] = None) -> List[Endpoint]:
        """获取接入点列表"""
        try:
            async with async_session_maker() as session:
                query = select(Endpoint)
                
                filters = []
                if endpoint_type:
                    filters.append(Endpoint.endpoint_type == endpoint_type)
                if enabled is not None:
                    filters.append(Endpoint.enabled == enabled)
                    
                if filters:
                    query = query.where(and_(*filters))
                    
                result = await session.execute(query)
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"Failed to list endpoints: {str(e)}")
            return []
            
    async def list_endpoints_paginated(self, endpoint_type: Optional[str] = None, enabled: Optional[bool] = None, skip: int = 0, limit: int = 20) -> tuple[List[Endpoint], int]:
        """获取分页接入点列表"""
        try:
            async with async_session_maker() as session:
                from sqlalchemy import func
                
                # 构建基础查询
                base_query = select(Endpoint)
                count_query = select(func.count(Endpoint.id))
                
                filters = []
                if endpoint_type:
                    filters.append(Endpoint.endpoint_type == endpoint_type)
                if enabled is not None:
                    filters.append(Endpoint.enabled == enabled)
                    
                if filters:
                    base_query = base_query.where(and_(*filters))
                    count_query = count_query.where(and_(*filters))
                
                # 获取总数
                total_result = await session.execute(count_query)
                total = total_result.scalar()
                
                # 获取分页数据
                data_query = base_query.order_by(Endpoint.created_at.desc()).offset(skip).limit(limit)
                result = await session.execute(data_query)
                endpoints = result.scalars().all()
                
                return endpoints, total
                
        except Exception as e:
            logger.error(f"Failed to list endpoints paginated: {str(e)}")
            return [], 0
            
    async def test_endpoint(self, endpoint_id: int) -> Dict[str, Any]:
        """测试接入点连接"""
        try:
            endpoint = await self.get_endpoint(endpoint_id)
            if not endpoint:
                return {"success": False, "error": "Endpoint not found"}
                
            test_result = await self._test_endpoint_connection(endpoint)
            return test_result
            
        except Exception as e:
            logger.error(f"Failed to test endpoint {endpoint_id}: {str(e)}")
            return {"success": False, "error": str(e)}
            
    async def get_endpoint_stats(self, endpoint_id: int) -> Dict[str, Any]:
        """获取接入点统计信息"""
        if endpoint_id in self.endpoint_stats:
            return self.endpoint_stats[endpoint_id]
        else:
            return {
                "messages_received": 0,
                "messages_processed": 0,
                "messages_failed": 0,
                "last_activity": None,
                "status": "inactive"
            }
            
    async def _activate_endpoint(self, endpoint: Endpoint):
        """激活接入点"""
        try:
            self.active_endpoints[endpoint.id] = {
                "endpoint": endpoint,
                "config": endpoint.config,
                "last_activity": datetime.utcnow(),
                "status": "active"
            }
            
            self.endpoint_stats[endpoint.id] = {
                "messages_received": 0,
                "messages_processed": 0,
                "messages_failed": 0,
                "last_activity": datetime.utcnow(),
                "status": "active"
            }
            
            logger.info(f"Activated endpoint: {endpoint.name}")
            
        except Exception as e:
            logger.error(f"Failed to activate endpoint {endpoint.id}: {str(e)}")
            
    async def _deactivate_endpoint(self, endpoint_id: int):
        """停用接入点"""
        try:
            if endpoint_id in self.active_endpoints:
                del self.active_endpoints[endpoint_id]
                
            if endpoint_id in self.endpoint_stats:
                self.endpoint_stats[endpoint_id]["status"] = "inactive"
                
            logger.info(f"Deactivated endpoint: {endpoint_id}")
            
        except Exception as e:
            logger.error(f"Failed to deactivate endpoint {endpoint_id}: {str(e)}")
            
    async def _update_active_endpoint(self, endpoint: Endpoint):
        """更新活跃接入点"""
        try:
            if endpoint.id in self.active_endpoints:
                self.active_endpoints[endpoint.id]["endpoint"] = endpoint
                self.active_endpoints[endpoint.id]["config"] = endpoint.config
                
        except Exception as e:
            logger.error(f"Failed to update active endpoint {endpoint.id}: {str(e)}")
            
    async def _test_endpoint_connection(self, endpoint: Endpoint) -> Dict[str, Any]:
        """测试接入点连接"""
        try:
            if endpoint.endpoint_type == EndpointType.HTTP:
                return await self._test_http_endpoint(endpoint)
            elif endpoint.endpoint_type == EndpointType.WEBHOOK:
                return await self._test_webhook_endpoint(endpoint)
            elif endpoint.endpoint_type == EndpointType.EMAIL:
                return await self._test_email_endpoint(endpoint)
            else:
                return {"success": True, "message": "Test not implemented for this endpoint type"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _test_http_endpoint(self, endpoint: Endpoint) -> Dict[str, Any]:
        """测试HTTP接入点"""
        try:
            import aiohttp
            
            config = endpoint.config
            url = config.get("url", "")
            headers = config.get("headers", {})
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=endpoint.timeout) as response:
                    if response.status == 200:
                        return {"success": True, "status_code": response.status}
                    else:
                        return {"success": False, "status_code": response.status}
                        
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _test_webhook_endpoint(self, endpoint: Endpoint) -> Dict[str, Any]:
        """测试Webhook接入点"""
        return {"success": True, "message": "Webhook endpoint configured"}
        
    async def _test_email_endpoint(self, endpoint: Endpoint) -> Dict[str, Any]:
        """测试邮件接入点"""
        try:
            config = endpoint.config
            smtp_server = config.get("smtp_server", "")
            smtp_port = config.get("smtp_port", 587)
            username = config.get("username", "")
            
            import aiosmtplib
            
            smtp_client = aiosmtplib.SMTP(hostname=smtp_server, port=smtp_port)
            await smtp_client.connect()
            
            if username:
                password = config.get("password", "")
                await smtp_client.starttls()
                await smtp_client.login(username, password)
                
            await smtp_client.quit()
            
            return {"success": True, "message": "Email endpoint connection successful"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def _generate_api_token(self) -> str:
        """生成API令牌"""
        # 生成32字节的随机令牌
        return secrets.token_urlsafe(32)
        
    def _generate_webhook_url(self, api_token: str) -> str:
        """生成Webhook接入URL"""
        return f"/api/webhook/alarm/{api_token}"
        
    async def get_endpoint_by_token(self, api_token: str) -> Optional[Endpoint]:
        """通过API令牌获取接入点"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Endpoint).where(
                        and_(
                            Endpoint.api_token == api_token,
                            Endpoint.enabled == True
                        )
                    )
                )
                return result.scalars().first()
                
        except Exception as e:
            logger.error(f"Failed to get endpoint by token: {str(e)}")
            return None
            
    async def update_endpoint_stats(self, endpoint_id: int, request_count: int = 1):
        """更新接入点使用统计"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Endpoint).where(Endpoint.id == endpoint_id)
                )
                endpoint = result.scalars().first()
                
                if endpoint:
                    endpoint.total_requests = (endpoint.total_requests or 0) + request_count
                    endpoint.last_used = datetime.utcnow()
                    
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"Failed to update endpoint stats: {str(e)}")
        
    async def process_incoming_alarm(self, endpoint_id: int, alarm_data: Dict[str, Any]) -> bool:
        """处理接入点接收的告警"""
        try:
            # 如果接入点不在活跃列表中，尝试获取并激活
            if endpoint_id not in self.active_endpoints:
                endpoint = await self.get_endpoint(endpoint_id)
                if not endpoint or not endpoint.enabled:
                    logger.warning(f"Received alarm from inactive or disabled endpoint: {endpoint_id}")
                    return False
                # 激活接入点
                await self._activate_endpoint(endpoint)
                
            endpoint_info = self.active_endpoints[endpoint_id]
            endpoint = endpoint_info["endpoint"]
            
            self.endpoint_stats[endpoint_id]["messages_received"] += 1
            self.endpoint_stats[endpoint_id]["last_activity"] = datetime.utcnow()
            
            transformed_data = await self._transform_alarm_data(endpoint, alarm_data)
            
            from src.services.collector import AlarmCollector
            collector = AlarmCollector()
            success = await collector.collect_alarm_dict(transformed_data)
            
            if success:
                self.endpoint_stats[endpoint_id]["messages_processed"] += 1
            else:
                self.endpoint_stats[endpoint_id]["messages_failed"] += 1
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to process alarm from endpoint {endpoint_id}: {str(e)}")
            if endpoint_id in self.endpoint_stats:
                self.endpoint_stats[endpoint_id]["messages_failed"] += 1
            return False
            
    async def _transform_alarm_data(self, endpoint: Endpoint, alarm_data: Dict[str, Any]) -> Dict[str, Any]:
        """转换告警数据格式"""
        try:
            config = endpoint.config
            field_mapping = config.get("field_mapping", {})
            
            transformed = {}
            
            for target_field, source_field in field_mapping.items():
                if source_field in alarm_data:
                    transformed[target_field] = alarm_data[source_field]
                    
            if "source" not in transformed:
                transformed["source"] = endpoint.name
                
            required_fields = ["title", "description", "severity"]
            for field in required_fields:
                if field not in transformed:
                    transformed[field] = alarm_data.get(field, f"Unknown {field}")
                    
            return transformed
            
        except Exception as e:
            logger.error(f"Failed to transform alarm data: {str(e)}")
            return alarm_data