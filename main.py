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
from src.core.logging import setup_logging, get_logger

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
from src.api.auth import router as auth_router
from src.core.config import settings
from src.core.database import init_db
from src.services.collector import AlarmCollector
from src.services.analyzer import AlarmAnalyzer
from src.services.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _global_collector, _global_analyzer
    
    # 设置日志
    setup_logging()
    logger = get_logger(__name__)
    logger.info("🚀 启动告警分析系统...")
    
    try:
        await init_db()
        logger.info("✅ 数据库初始化完成")
        
        collector = AlarmCollector()
        analyzer = AlarmAnalyzer()
        
        await collector.start()
        await analyzer.start()
        logger.info("✅ 告警收集器和分析器启动完成")
        
        # 保存全局引用
        _global_collector = collector
        _global_analyzer = analyzer
        
        start_scheduler()
        logger.info("✅ 调度器启动完成")
        
        # 启动WebSocket实时更新器
        from src.services.websocket_manager import real_time_updater
        await real_time_updater.start()
        logger.info("✅ WebSocket实时更新器启动完成")
        
        logger.info("🎉 告警分析系统启动成功")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ 系统启动失败: {str(e)}")
        raise
    finally:
        logger.info("🔄 正在关闭告警分析系统...")
        
        if _global_collector:
            await _global_collector.stop()
        if _global_analyzer:
            await _global_analyzer.stop()
        
        from src.services.websocket_manager import real_time_updater
        await real_time_updater.stop()
        
        logger.info("👋 告警分析系统已关闭")


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

app.include_router(auth_router, prefix="/api/auth", tags=["用户认证"])
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


# SPA路由fallback - 必须在所有API路由之后定义
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_fallback(full_path: str):
    """
    SPA路由fallback处理器
    当访问非API路径且文件不存在时，返回index.html让前端路由处理
    """
    # 如果是API路径，不处理（让FastAPI返回404）
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")
    
    # 如果是WebSocket路径，不处理
    if full_path.startswith("ws/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")
    
    # 处理静态文件路径的特殊情况：/static/dist/users 应该重定向到前端路由
    if full_path.startswith("static/dist/") and not full_path.endswith(('.html', '.js', '.css', '.ico', '.png', '.jpg', '.svg')):
        # 提取前端路由部分，例如 static/dist/users -> users
        frontend_route = full_path.replace("static/dist/", "")
        # 重定向到正确的前端路由
        vue_index_path = "static/dist/index.html"
        if os.path.exists(vue_index_path):
            return FileResponse(vue_index_path)
    
    # 如果是普通静态文件路径，检查文件是否存在
    if full_path.startswith("static/"):
        static_file_path = full_path
        if os.path.exists(static_file_path):
            return FileResponse(static_file_path)
        else:
            # 静态文件不存在，返回404
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Static file not found")
    
    # 对于其他所有路径（前端路由），返回index.html
    vue_index_path = "static/dist/index.html"
    if os.path.exists(vue_index_path):
        return FileResponse(vue_index_path)
    
    # 如果index.html不存在，返回简单页面
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <title>告警分析系统</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body>
        <h1>告警分析系统</h1>
        <p>前端页面尚未构建，请运行构建命令。</p>
        <a href="/docs">查看API文档</a>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
async def root():
    # 优先返回Vue.js构建的index.html
    vue_index_path = "static/dist/index.html"
    if os.path.exists(vue_index_path):
        return FileResponse(vue_index_path)
    
    # 检查是否有MVP页面
    mvp_path = "static/mvp.html"
    if os.path.exists(mvp_path):
        return FileResponse(mvp_path)
    
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


@app.get("/mvp", response_class=HTMLResponse)
async def mvp_dashboard():
    """MVP演示页面"""
    mvp_path = "static/mvp.html"
    if os.path.exists(mvp_path):
        return FileResponse(mvp_path)
    else:
        raise HTTPException(status_code=404, detail="MVP页面未找到")

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    """现代化管理后台界面"""
    try:
        with open("templates/modern-admin.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # 如果找不到管理页面，跳转到MVP页面
        return FileResponse("static/mvp.html") if os.path.exists("static/mvp.html") else HTMLResponse("管理页面开发中...")

@app.get("/admin/classic", response_class=HTMLResponse)
async def classic_admin_panel():
    """经典管理后台界面"""
    try:
        with open("templates/admin.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return FileResponse("static/mvp.html") if os.path.exists("static/mvp.html") else HTMLResponse("管理页面开发中...")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )