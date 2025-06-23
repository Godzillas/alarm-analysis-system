#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
告警分析系统主入口
"""

import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from src.api.routers import (
    alarm_router, dashboard_router, config_router,
    endpoint_router, user_router, rule_router, analytics_router,
    websocket_router, webhook_router
)
from src.core.config import settings
from src.core.database import init_db
from src.services.collector import AlarmCollector
from src.services.analyzer import AlarmAnalyzer
from src.services.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    
    collector = AlarmCollector()
    analyzer = AlarmAnalyzer()
    
    await collector.start()
    await analyzer.start()
    
    start_scheduler()
    
    # 启动WebSocket实时更新器
    from src.services.websocket_manager import real_time_updater
    await real_time_updater.start()
    
    yield
    
    await collector.stop()
    await analyzer.stop()
    await real_time_updater.stop()


app = FastAPI(
    title="告警分析系统",
    description="智能告警收集、分析和展示系统",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(alarm_router, prefix="/api/alarms", tags=["告警管理"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["仪表板"])
app.include_router(config_router, prefix="/api/config", tags=["配置管理"])
app.include_router(endpoint_router, prefix="/api/endpoints", tags=["接入点管理"])
app.include_router(user_router, prefix="/api/users", tags=["用户管理"])
app.include_router(rule_router, prefix="/api/rules", tags=["规则管理"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["分析统计"])
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])
app.include_router(webhook_router, prefix="/api/webhook", tags=["Webhook接收"])


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>告警分析系统</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>告警分析系统</h1>
        <p><a href="/docs">API 文档</a></p>
        <p><a href="/dashboard">仪表板</a></p>
        <p><a href="/admin">管理后台</a></p>
    </body>
    </html>
    """


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    """现代化管理后台界面"""
    with open("templates/modern-admin.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/admin/classic", response_class=HTMLResponse)
async def classic_admin_panel():
    """经典管理后台界面"""
    with open("templates/admin.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )