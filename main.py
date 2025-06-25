#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
告警分析系统主入口
"""

import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from contextlib import asynccontextmanager
import os

# 全局服务实例
_global_collector = None
_global_analyzer = None

from src.api.routers import (
    alarm_router, dashboard_router, config_router,
    endpoint_router, user_router, rule_router, analytics_router,
    websocket_router, webhook_router
)
from src.api.system import router as system_router
from src.api.contact_point import router as contact_point_router
from src.api.alert_template import router as alert_template_router
from src.core.config import settings
from src.core.database import init_db
from src.services.collector import AlarmCollector
from src.services.analyzer import AlarmAnalyzer
from src.services.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _global_collector, _global_analyzer
    
    await init_db()
    
    collector = AlarmCollector()
    analyzer = AlarmAnalyzer()
    
    await collector.start()
    await analyzer.start()
    
    # 保存全局引用
    _global_collector = collector
    _global_analyzer = analyzer
    
    start_scheduler()
    
    # 启动WebSocket实时更新器
    from src.services.websocket_manager import real_time_updater
    await real_time_updater.start()
    
    yield
    
    await collector.stop()
    await analyzer.stop()
    await real_time_updater.stop()


def get_global_collector():
    """获取全局启动的collector实例"""
    return _global_collector


def get_global_analyzer():
    """获取全局启动的analyzer实例"""
    return _global_analyzer


app = FastAPI(
    title="告警分析系统",
    description="智能告警收集、分析和展示系统",
    version="1.0.0",
    lifespan=lifespan
)

# 挂载静态文件
if os.path.exists("static/dist"):
    # Vue.js构建的静态文件
    app.mount("/static/dist", StaticFiles(directory="static/dist"), name="vue-static")
    # 原始静态文件(兼容性)
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    # 回退到原始静态文件
    app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(alarm_router, prefix="/api/alarms", tags=["告警管理"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["仪表板"])
app.include_router(config_router, prefix="/api/config", tags=["配置管理"])
app.include_router(endpoint_router, prefix="/api/endpoints", tags=["接入点管理"])
app.include_router(user_router, prefix="/api/users", tags=["用户管理"])
app.include_router(rule_router, prefix="/api/rules", tags=["规则管理"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["分析统计"])
app.include_router(system_router, prefix="/api/systems", tags=["系统管理"])
app.include_router(contact_point_router, prefix="/api/contact-points", tags=["联络点管理"])
app.include_router(alert_template_router, prefix="/api/alert-templates", tags=["告警模板管理"])
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])
app.include_router(webhook_router, prefix="/api/webhook", tags=["Webhook接收"])


@app.get("/", response_class=HTMLResponse)
async def root():
    # 优先返回Vue.js构建的index.html
    vue_index_path = "static/dist/index.html"
    if os.path.exists(vue_index_path):
        return FileResponse(vue_index_path)
    
    # 回退到简单的HTML页面
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <title>告警分析系统</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { color: #409eff; margin-bottom: 30px; }
            .links { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
            .link-card { padding: 20px; border: 1px solid #ddd; border-radius: 8px; text-decoration: none; color: inherit; }
            .link-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚨 告警分析系统</h1>
            <div class="links">
                <a href="/docs" class="link-card">
                    <h3>📚 API 文档</h3>
                    <p>查看系统API接口文档</p>
                </a>
                <a href="/admin" class="link-card">
                    <h3>⚙️ 管理后台</h3>
                    <p>系统管理和配置</p>
                </a>
            </div>
        </div>
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