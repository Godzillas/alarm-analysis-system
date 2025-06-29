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
from src.core.middleware import ErrorHandlerMiddleware, LoggingMiddleware, SecurityHeadersMiddleware

# 全局服务实例
_global_collector = None
_global_analyzer = None

from src.api.routers import (
    alarm_router, dashboard_router, config_router,
    endpoint_router, user_router, rule_router, analytics_router,
    websocket_router, webhook_router, api_v1_router
)
from src.api.system import router as system_router
from src.api.contact_point import router as contact_point_router
from src.api.alert_template import router as alert_template_router
from src.api.oncall import router as oncall_router
from src.api.auth import router as auth_router
from src.api.deduplication import router as deduplication_router
from src.api.health import router as health_router
from src.api.alarm_processing import router as alarm_processing_router
from src.api.solutions import router as solutions_router
# from src.api.subscriptions import router as subscriptions_router  # Replaced by notifications API
from src.api.data_lifecycle import router as data_lifecycle_router
from src.api.rbac import router as rbac_router
# from src.api.alarms_rbac_example import router as alarms_rbac_router  # File deleted
from src.api.noise_reduction import router as noise_reduction_router
from src.api.suppression import router as suppression_router
from src.api.webhook_ingestion import router as webhook_ingestion_router
from src.api.prometheus_ingestion import router as prometheus_ingestion_router
from src.api.grafana_ingestion import router as grafana_ingestion_router
from src.api.alarm_lifecycle import router as alarm_lifecycle_router
from src.api.notifications import router as notifications_router
from src.core.config import settings
from src.core.database import init_db
from src.services.collector import AlarmCollector
from src.services.analyzer import AlarmAnalyzer
from src.services.scheduler import start_scheduler
from src.services.endpoint_manager import endpoint_manager


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
        
        await endpoint_manager._initialize_enabled_endpoints()
        logger.info("✅ 接入点管理器初始化完成")
        
        # 保存全局引用
        _global_collector = collector
        _global_analyzer = analyzer
        
        start_scheduler()
        logger.info("✅ 调度器启动完成")
        
        # 启动WebSocket实时更新器
        from src.services.websocket_manager import real_time_updater
        await real_time_updater.start()
        logger.info("✅ WebSocket实时更新器启动完成")
        
        # 启动升级引擎
        from src.services.escalation_engine import escalation_engine
        await escalation_engine.start()
        logger.info("✅ 告警升级引擎启动完成")
        
        # 启动去重引擎
        from src.services.deduplication_engine import initialize_deduplication_engine
        await initialize_deduplication_engine()
        logger.info("✅ 告警去重引擎启动完成")
        
        # 启动通知引擎
        from src.services.notification_engine import start_notification_engine
        await start_notification_engine()
        logger.info("✅ 通知发送引擎启动完成")
        
        # 启动告警分发服务
        from src.services.alarm_dispatch import alarm_dispatch_service
        await alarm_dispatch_service.start()
        logger.info("✅ 告警分发服务启动完成")
        
        # 创建默认通知模板
        from src.services.default_templates import ensure_default_templates_exist
        from src.core.database import async_session_maker
        async with async_session_maker() as template_session:
            await ensure_default_templates_exist(template_session)
        logger.info("✅ 默认通知模板检查完成")
        
        # 加载抑制规则缓存
        from src.services.suppression_service import suppression_service
        async with async_session_maker() as db:
            await suppression_service.load_active_suppressions(db)
        logger.info("✅ 抑制规则缓存加载完成")
        
        # 启动生命周期管理引擎
        from src.services.alarm_lifecycle_manager import lifecycle_manager
        from src.services.lifecycle_scheduler import lifecycle_scheduler
        await lifecycle_scheduler.start()
        logger.info("✅ 告警生命周期管理引擎和调度器启动完成")
        
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
        
        from src.services.escalation_engine import escalation_engine
        await escalation_engine.stop()
        
        # 停止通知引擎
        from src.services.notification_engine import stop_notification_engine
        await stop_notification_engine()
        
        # 停止告警分发服务
        from src.services.alarm_dispatch import alarm_dispatch_service
        await alarm_dispatch_service.stop()
        
        # 停止生命周期调度器
        from src.services.lifecycle_scheduler import lifecycle_scheduler
        await lifecycle_scheduler.stop()
        
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

# 添加中间件（注意顺序：最后添加的最先执行）
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlerMiddleware)

# 创建自定义静态文件处理器
class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except:
            # 如果文件不存在且不是真实的静态文件，返回index.html
            if not path.endswith(('.html', '.js', '.css', '.ico', '.png', '.jpg', '.svg', '.woff', '.woff2', '.ttf', '.eot', '.json', '.txt')):
                index_path = "index.html"
                return await super().get_response(index_path, scope)
            raise

# 挂载静态文件 (仅在非开发模式下)
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
if not DEV_MODE and os.path.exists("static/dist"):
    # Vue.js构建的静态文件 - 使用自定义处理器支持SPA路由
    app.mount("/static/dist", SPAStaticFiles(directory="static/dist"), name="vue-static")
    # 原始静态文件(兼容性)
    app.mount("/static", StaticFiles(directory="static"), name="static")
elif not DEV_MODE:
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
app.include_router(deduplication_router, prefix="/api/deduplication", tags=["告警去重"])
app.include_router(system_router, prefix="/api/systems", tags=["系统管理"])
app.include_router(contact_point_router, prefix="/api/contact-points", tags=["联络点管理"])
app.include_router(alert_template_router, prefix="/api/alert-templates", tags=["告警模板管理"])
app.include_router(oncall_router, tags=["值班管理"])
app.include_router(websocket_router, tags=["WebSocket"])
app.include_router(webhook_router, prefix="/api/webhook", tags=["Webhook接收"])
app.include_router(health_router, tags=["系统监控"])
app.include_router(alarm_processing_router, prefix="/api", tags=["告警处理"])
app.include_router(solutions_router, prefix="/api/solutions", tags=["解决方案管理"])
# app.include_router(subscriptions_router, prefix="/api", tags=["告警订阅"])  # Replaced by notifications API
app.include_router(data_lifecycle_router, tags=["数据生命周期管理"])
app.include_router(rbac_router, tags=["权限管理"])
# app.include_router(alarms_rbac_router, tags=["告警管理(RBAC示例)"])  # File deleted
app.include_router(noise_reduction_router, tags=["告警降噪"])
app.include_router(suppression_router, prefix="/api/suppression", tags=["告警抑制"])
app.include_router(notifications_router, prefix="/api/notifications", tags=["通知管理"])
app.include_router(api_v1_router, prefix="/api/v1", tags=["API v1"])


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
    
    # 在开发模式下，对于前端路径返回重定向提示
    if DEV_MODE:
        return f"""
        <html>
            <head><title>开发模式 - 告警分析系统</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>🚧 开发模式</h1>
                <p>你正在尝试访问: <code style="background: #f5f5f5; padding: 2px 6px;">/{full_path}</code></p>
                <p>请访问前端开发服务器查看最新修改:</p>
                <p><a href="http://localhost:3001/#{full_path}" style="font-size: 18px; color: #409eff;">http://localhost:3001/#{full_path}</a></p>
                <p><small>后端API运行在: <a href="/docs">http://localhost:8000/docs</a></small></p>
            </body>
        </html>
        """
    
    # 生产模式：处理静态文件路径
    if full_path.startswith("static/"):
        static_file_path = full_path
        if os.path.exists(static_file_path):
            # 文件存在，直接返回
            return FileResponse(static_file_path)
        elif full_path.startswith("static/dist/") and not full_path.endswith(('.html', '.js', '.css', '.ico', '.png', '.jpg', '.svg', '.woff', '.woff2', '.ttf', '.eot')):
            # 这是前端路由（如 static/dist/dashboard），返回 index.html
            vue_index_path = "static/dist/index.html"
            if os.path.exists(vue_index_path):
                return FileResponse(vue_index_path, media_type="text/html")
            else:
                # index.html 不存在，返回简单页面
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
        else:
            # 其他静态文件不存在，返回404
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
    # 在开发模式下，提供重定向提示
    if DEV_MODE:
        return """
        <html>
            <head><title>开发模式 - 告警分析系统</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>🚧 开发模式</h1>
                <p>请访问前端开发服务器查看最新修改:</p>
                <p><a href="http://localhost:3001" style="font-size: 18px; color: #409eff;">http://localhost:3001</a></p>
                <p><small>后端API运行在: <a href="/docs">http://localhost:8000/docs</a></small></p>
            </body>
        </html>
        """
    
    # 生产模式：优先返回Vue.js构建的index.html
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