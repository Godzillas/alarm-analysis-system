"""
WebSocket连接管理器
"""

import json
import asyncio
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.room_connections: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, room: str = "default"):
        """建立WebSocket连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if room not in self.room_connections:
            self.room_connections[room] = set()
        self.room_connections[room].add(websocket)
        
        logger.info(f"WebSocket连接建立: room={room}, 当前连接数={len(self.active_connections)}")
        
        # 发送欢迎消息
        await self.send_personal_message({
            "type": "connected",
            "message": "连接建立成功",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
        # 从所有房间中移除
        for room_connections in self.room_connections.values():
            room_connections.discard(websocket)
            
        logger.info(f"WebSocket连接断开, 当前连接数={len(self.active_connections)}")
        
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"发送个人消息失败: {str(e)}")
            self.disconnect(websocket)
            
    async def broadcast_to_room(self, message: dict, room: str = "default"):
        """向房间广播消息"""
        if room not in self.room_connections:
            return
            
        disconnected = []
        for connection in self.room_connections[room].copy():
            try:
                await connection.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"广播消息失败: {str(e)}")
                disconnected.append(connection)
                
        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)
            
    async def broadcast_to_all(self, message: dict):
        """向所有连接广播消息"""
        disconnected = []
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"广播消息失败: {str(e)}")
                disconnected.append(connection)
                
        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)
            
    async def send_alarm_update(self, alarm_data: dict):
        """发送告警更新"""
        message = {
            "type": "alarm_update",
            "data": alarm_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_room(message, "dashboard")
        
    async def send_stats_update(self, stats_data: dict):
        """发送统计更新"""
        message = {
            "type": "stats_update",
            "data": stats_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_room(message, "dashboard")
        
    async def send_alarm_notification(self, alarm_data: dict):
        """发送告警通知"""
        message = {
            "type": "alarm_notification",
            "data": alarm_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_room(message, "alarms")
        
    async def send_system_notification(self, notification: dict):
        """发送系统通知"""
        message = {
            "type": "system_notification",
            "data": notification,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_all(message)
        
    def get_connection_stats(self) -> dict:
        """获取连接统计"""
        return {
            "total_connections": len(self.active_connections),
            "room_connections": {
                room: len(connections) 
                for room, connections in self.room_connections.items()
            }
        }


# 全局连接管理器实例
connection_manager = ConnectionManager()


class RealTimeUpdater:
    """实时数据更新器"""
    
    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.is_running = False
        self.update_task = None
        
    async def start(self):
        """启动实时更新"""
        if self.is_running:
            return
            
        self.is_running = True
        self.update_task = asyncio.create_task(self._update_loop())
        logger.info("实时数据更新器启动")
        
    async def stop(self):
        """停止实时更新"""
        self.is_running = False
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        logger.info("实时数据更新器停止")
        
    async def _update_loop(self):
        """更新循环"""
        while self.is_running:
            try:
                await self._send_periodic_updates()
                await asyncio.sleep(30)  # 每30秒更新一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"实时更新失败: {str(e)}")
                await asyncio.sleep(60)  # 出错后等待更长时间
                
    async def _send_periodic_updates(self):
        """发送周期性更新"""
        try:
            # 发送统计更新
            from src.api.routers import get_collector
            from sqlalchemy import select, func
            from sqlalchemy.sql import case
            from src.core.database import async_session_maker
            from src.models.alarm import AlarmTable, AlarmStatus, AlarmSeverity
            
            async with async_session_maker() as session:
                # 获取告警统计
                result = await session.execute(
                    select(
                        func.count(AlarmTable.id).label('total'),
                        func.sum(case((AlarmTable.status == AlarmStatus.ACTIVE, 1), else_=0)).label('active'),
                        func.sum(case((AlarmTable.status == AlarmStatus.RESOLVED, 1), else_=0)).label('resolved'),
                        func.sum(case((AlarmTable.severity == AlarmSeverity.CRITICAL, 1), else_=0)).label('critical')
                    )
                )
                stats = result.first()
                
                stats_data = {
                    "total": stats.total or 0,
                    "active": stats.active or 0,
                    "resolved": stats.resolved or 0,
                    "critical": stats.critical or 0
                }
                
                await self.manager.send_stats_update(stats_data)
                
        except Exception as e:
            logger.error(f"发送周期性更新失败: {str(e)}")


# 全局实时更新器实例
real_time_updater = RealTimeUpdater(connection_manager)