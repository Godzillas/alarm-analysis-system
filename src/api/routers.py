"""
API路由定义
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.sql import case
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.models.alarm import (
    AlarmTable, AlarmCreate, AlarmUpdate, AlarmResponse, AlarmStats,
    AlarmStatus, AlarmSeverity, Endpoint, EndpointCreate, EndpointUpdate, 
    EndpointResponse, User, UserCreate, UserUpdate, UserResponse,
    UserSubscription, SubscriptionCreate, SubscriptionResponse,
    RuleGroup, DistributionRule
)
from src.services.collector import AlarmCollector
from src.services.analyzer import AlarmAnalyzer
from src.services.endpoint_manager import EndpointManager
from src.services.user_manager import UserManager
from src.services.rule_engine import RuleEngine
from src.services.aggregator import AlarmAggregator

alarm_router = APIRouter()
dashboard_router = APIRouter()
config_router = APIRouter()
endpoint_router = APIRouter()
user_router = APIRouter()
rule_router = APIRouter()
analytics_router = APIRouter()
websocket_router = APIRouter()
webhook_router = APIRouter()

# 全局服务实例
collector = None
analyzer = None
endpoint_manager = None
user_manager = None
rule_engine = None
aggregator = None


def get_collector():
    global collector
    if collector is None:
        collector = AlarmCollector()
    return collector


def get_analyzer():
    global analyzer
    if analyzer is None:
        analyzer = AlarmAnalyzer()
    return analyzer


def get_endpoint_manager():
    global endpoint_manager
    if endpoint_manager is None:
        endpoint_manager = EndpointManager()
    return endpoint_manager


def get_user_manager():
    global user_manager
    if user_manager is None:
        user_manager = UserManager()
    return user_manager


def get_rule_engine():
    global rule_engine
    if rule_engine is None:
        rule_engine = RuleEngine()
    return rule_engine


def get_aggregator():
    global aggregator
    if aggregator is None:
        aggregator = AlarmAggregator()
    return aggregator


@alarm_router.post("/", response_model=AlarmResponse)
async def create_alarm(
    alarm: AlarmCreate,
    db: AsyncSession = Depends(get_db_session),
    collector: AlarmCollector = Depends(get_collector)
):
    """创建新告警"""
    try:
        await collector.collect_alarm_dict(alarm.dict())
        
        new_alarm = AlarmTable(**alarm.dict())
        db.add(new_alarm)
        await db.commit()
        await db.refresh(new_alarm)
        
        return new_alarm
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建告警失败: {str(e)}")


@alarm_router.get("/", response_model=List[AlarmResponse])
async def get_alarms(
    db: AsyncSession = Depends(get_db_session),
    status: Optional[AlarmStatus] = None,
    severity: Optional[AlarmSeverity] = None,
    source: Optional[str] = None,
    host: Optional[str] = None,
    service: Optional[str] = None,
    environment: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """获取告警列表"""
    query = select(AlarmTable)
    
    filters = []
    if status:
        filters.append(AlarmTable.status == status)
    if severity:
        filters.append(AlarmTable.severity == severity)
    if source:
        filters.append(AlarmTable.source == source)
    if host:
        filters.append(AlarmTable.host == host)
    if service:
        filters.append(AlarmTable.service == service)
    if environment:
        filters.append(AlarmTable.environment == environment)
        
    if filters:
        query = query.where(and_(*filters))
        
    query = query.order_by(desc(AlarmTable.created_at)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@alarm_router.get("/{alarm_id}", response_model=AlarmResponse)
async def get_alarm(alarm_id: int, db: AsyncSession = Depends(get_db_session)):
    """获取单个告警详情"""
    result = await db.execute(select(AlarmTable).where(AlarmTable.id == alarm_id))
    alarm = result.scalars().first()
    
    if not alarm:
        raise HTTPException(status_code=404, detail="告警不存在")
        
    return alarm


@alarm_router.put("/{alarm_id}", response_model=AlarmResponse)
async def update_alarm(
    alarm_id: int,
    alarm_update: AlarmUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """更新告警"""
    result = await db.execute(select(AlarmTable).where(AlarmTable.id == alarm_id))
    alarm = result.scalars().first()
    
    if not alarm:
        raise HTTPException(status_code=404, detail="告警不存在")
        
    update_data = alarm_update.dict(exclude_unset=True)
    
    if update_data.get('status') == AlarmStatus.RESOLVED:
        update_data['resolved_at'] = datetime.utcnow()
    elif update_data.get('status') == AlarmStatus.ACKNOWLEDGED:
        update_data['acknowledged_at'] = datetime.utcnow()
        
    for key, value in update_data.items():
        setattr(alarm, key, value)
        
    alarm.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(alarm)
    
    return alarm


@alarm_router.delete("/{alarm_id}")
async def delete_alarm(alarm_id: int, db: AsyncSession = Depends(get_db_session)):
    """删除告警"""
    result = await db.execute(select(AlarmTable).where(AlarmTable.id == alarm_id))
    alarm = result.scalars().first()
    
    if not alarm:
        raise HTTPException(status_code=404, detail="告警不存在")
        
    await db.delete(alarm)
    await db.commit()
    
    return {"message": "告警删除成功"}


@alarm_router.get("/stats/summary", response_model=AlarmStats)
async def get_alarm_stats(db: AsyncSession = Depends(get_db_session)):
    """获取告警统计"""
    result = await db.execute(
        select(
            func.count(AlarmTable.id).label('total'),
            func.sum(case((AlarmTable.status == AlarmStatus.ACTIVE, 1), else_=0)).label('active'),
            func.sum(case((AlarmTable.status == AlarmStatus.RESOLVED, 1), else_=0)).label('resolved'),
            func.sum(case((AlarmTable.status == AlarmStatus.ACKNOWLEDGED, 1), else_=0)).label('acknowledged'),
            func.sum(case((AlarmTable.status == AlarmStatus.SUPPRESSED, 1), else_=0)).label('suppressed'),
            func.sum(case((AlarmTable.severity == AlarmSeverity.CRITICAL, 1), else_=0)).label('critical'),
            func.sum(case((AlarmTable.severity == AlarmSeverity.HIGH, 1), else_=0)).label('high'),
            func.sum(case((AlarmTable.severity == AlarmSeverity.MEDIUM, 1), else_=0)).label('medium'),
            func.sum(case((AlarmTable.severity == AlarmSeverity.LOW, 1), else_=0)).label('low'),
            func.sum(case((AlarmTable.severity == AlarmSeverity.INFO, 1), else_=0)).label('info')
        )
    )
    
    stats = result.first()
    
    return AlarmStats(
        total=stats.total or 0,
        active=stats.active or 0,
        resolved=stats.resolved or 0,
        acknowledged=stats.acknowledged or 0,
        suppressed=stats.suppressed or 0,
        critical=stats.critical or 0,
        high=stats.high or 0,
        medium=stats.medium or 0,
        low=stats.low or 0,
        info=stats.info or 0
    )


@alarm_router.post("/batch")
async def create_batch_alarms(
    alarms: List[AlarmCreate],
    collector: AlarmCollector = Depends(get_collector)
):
    """批量创建告警"""
    success_count = 0
    
    for alarm in alarms:
        try:
            success = await collector.collect_alarm_dict(alarm.dict())
            if success:
                success_count += 1
        except Exception as e:
            continue
            
    return {
        "message": f"批量创建告警完成",
        "total": len(alarms),
        "success": success_count,
        "failed": len(alarms) - success_count
    }


@dashboard_router.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """仪表板首页"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>告警分析系统 - 仪表板</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .card { border: 1px solid #ddd; padding: 20px; margin: 10px; border-radius: 5px; }
            .stat { display: inline-block; margin: 10px; padding: 10px; background: #f5f5f5; }
            .critical { background-color: #ffebee; }
            .high { background-color: #fff3e0; }
            .medium { background-color: #f3e5f5; }
            .low { background-color: #e8f5e8; }
        </style>
    </head>
    <body>
        <h1>告警分析系统仪表板</h1>
        <div id="stats"></div>
        <div id="alarms"></div>
        
        <script>
            async function loadStats() {
                const response = await fetch('/api/alarms/stats/summary');
                const stats = await response.json();
                
                document.getElementById('stats').innerHTML = `
                    <div class="card">
                        <h3>告警统计</h3>
                        <div class="stat">总数: ${stats.total}</div>
                        <div class="stat">活跃: ${stats.active}</div>
                        <div class="stat">已解决: ${stats.resolved}</div>
                        <div class="stat critical">严重: ${stats.critical}</div>
                        <div class="stat high">高级: ${stats.high}</div>
                        <div class="stat medium">中级: ${stats.medium}</div>
                        <div class="stat low">低级: ${stats.low}</div>
                    </div>
                `;
            }
            
            async function loadAlarms() {
                const response = await fetch('/api/alarms/?limit=10');
                const alarms = await response.json();
                
                let html = '<div class="card"><h3>最新告警</h3>';
                alarms.forEach(alarm => {
                    html += `
                        <div class="alarm ${alarm.severity}">
                            <strong>${alarm.title}</strong> - ${alarm.source}
                            <br>状态: ${alarm.status} | 级别: ${alarm.severity}
                            <br>时间: ${new Date(alarm.created_at).toLocaleString()}
                        </div>
                    `;
                });
                html += '</div>';
                
                document.getElementById('alarms').innerHTML = html;
            }
            
            loadStats();
            loadAlarms();
            
            setInterval(() => {
                loadStats();
                loadAlarms();
            }, 30000);
        </script>
    </body>
    </html>
    """


@dashboard_router.get("/metrics")
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db_session),
    collector: AlarmCollector = Depends(get_collector),
    analyzer: AlarmAnalyzer = Depends(get_analyzer)
):
    """获取仪表板指标"""
    
    collector_stats = await collector.get_stats()
    analyzer_stats = await analyzer.get_analysis_summary()
    
    recent_alarms = await db.execute(
        select(
            AlarmTable.created_at,
            func.count(AlarmTable.id).label('count')
        ).where(
            AlarmTable.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).group_by(
            func.date_trunc('hour', AlarmTable.created_at)
        ).order_by(AlarmTable.created_at)
    )
    
    timeline_data = [
        {"time": row.created_at.isoformat(), "count": row.count}
        for row in recent_alarms.all()
    ]
    
    return {
        "collector": collector_stats,
        "analyzer": analyzer_stats,
        "timeline": timeline_data
    }


@config_router.get("/")
async def get_config():
    """获取系统配置"""
    from src.core.config import settings
    
    return {
        "collector_enabled": settings.COLLECTOR_ENABLED,
        "analyzer_enabled": settings.ANALYZER_ENABLED,
        "notification_enabled": settings.NOTIFICATION_ENABLED,
        "duplicate_threshold": settings.DUPLICATE_THRESHOLD,
        "correlation_window": settings.CORRELATION_WINDOW
    }


@config_router.put("/")
async def update_config(config: Dict[str, Any] = Body(...)):
    """更新系统配置"""
    
    return {"message": "配置更新成功", "config": config}


# 接入点管理路由
@endpoint_router.post("/", response_model=EndpointResponse)
async def create_endpoint(
    endpoint: EndpointCreate,
    manager: EndpointManager = Depends(get_endpoint_manager)
):
    """创建接入点"""
    result = await manager.create_endpoint(endpoint.dict())
    if not result:
        raise HTTPException(status_code=500, detail="创建接入点失败")
    return result


@endpoint_router.get("/", response_model=List[EndpointResponse])
async def list_endpoints(
    endpoint_type: Optional[str] = None,
    enabled: Optional[bool] = None,
    manager: EndpointManager = Depends(get_endpoint_manager)
):
    """获取接入点列表"""
    return await manager.list_endpoints(endpoint_type, enabled)


@endpoint_router.get("/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint(
    endpoint_id: int,
    manager: EndpointManager = Depends(get_endpoint_manager)
):
    """获取接入点详情"""
    result = await manager.get_endpoint(endpoint_id)
    if not result:
        raise HTTPException(status_code=404, detail="接入点不存在")
    return result


@endpoint_router.put("/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: int,
    endpoint_update: EndpointUpdate,
    manager: EndpointManager = Depends(get_endpoint_manager)
):
    """更新接入点"""
    result = await manager.update_endpoint(endpoint_id, endpoint_update.dict(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="接入点不存在")
    return result


@endpoint_router.delete("/{endpoint_id}")
async def delete_endpoint(
    endpoint_id: int,
    manager: EndpointManager = Depends(get_endpoint_manager)
):
    """删除接入点"""
    success = await manager.delete_endpoint(endpoint_id)
    if not success:
        raise HTTPException(status_code=404, detail="接入点不存在")
    return {"message": "接入点删除成功"}


@endpoint_router.post("/{endpoint_id}/test")
async def test_endpoint(
    endpoint_id: int,
    manager: EndpointManager = Depends(get_endpoint_manager)
):
    """测试接入点"""
    result = await manager.test_endpoint(endpoint_id)
    return result


@endpoint_router.get("/{endpoint_id}/stats")
async def get_endpoint_stats(
    endpoint_id: int,
    manager: EndpointManager = Depends(get_endpoint_manager)
):
    """获取接入点统计"""
    return await manager.get_endpoint_stats(endpoint_id)


# 用户管理路由
@user_router.post("/", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    manager: UserManager = Depends(get_user_manager)
):
    """创建用户"""
    result = await manager.create_user(user.dict())
    if not result:
        raise HTTPException(status_code=500, detail="创建用户失败")
    return result


@user_router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = False,
    manager: UserManager = Depends(get_user_manager)
):
    """获取用户列表"""
    return await manager.list_users(skip, limit, active_only)


@user_router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    manager: UserManager = Depends(get_user_manager)
):
    """获取用户详情"""
    result = await manager.get_user(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="用户不存在")
    return result


@user_router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    manager: UserManager = Depends(get_user_manager)
):
    """更新用户"""
    result = await manager.update_user(user_id, user_update.dict(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="用户不存在")
    return result


@user_router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    manager: UserManager = Depends(get_user_manager)
):
    """删除用户"""
    success = await manager.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"message": "用户删除成功"}


@user_router.post("/login")
async def login_user(
    username: str = Body(...),
    password: str = Body(...),
    manager: UserManager = Depends(get_user_manager)
):
    """用户登录"""
    user = await manager.authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    session_token = await manager.create_session(user.id)
    return {
        "user": UserResponse.from_orm(user),
        "session_token": session_token
    }


@user_router.post("/logout")
async def logout_user(
    session_token: str = Body(...),
    manager: UserManager = Depends(get_user_manager)
):
    """用户登出"""
    await manager.destroy_session(session_token)
    return {"message": "登出成功"}


@user_router.post("/{user_id}/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    user_id: int,
    subscription: SubscriptionCreate,
    manager: UserManager = Depends(get_user_manager)
):
    """创建用户订阅"""
    result = await manager.create_subscription(user_id, subscription.dict())
    if not result:
        raise HTTPException(status_code=500, detail="创建订阅失败")
    return result


@user_router.get("/{user_id}/subscriptions", response_model=List[SubscriptionResponse])
async def get_user_subscriptions(
    user_id: int,
    manager: UserManager = Depends(get_user_manager)
):
    """获取用户订阅列表"""
    return await manager.get_user_subscriptions(user_id)


# 规则管理路由
@rule_router.post("/groups")
async def create_rule_group(
    group_data: Dict[str, Any] = Body(...),
    engine: RuleEngine = Depends(get_rule_engine)
):
    """创建规则组"""
    result = await engine.create_rule_group(group_data)
    if not result:
        raise HTTPException(status_code=500, detail="创建规则组失败")
    return result


@rule_router.post("/rules")
async def create_distribution_rule(
    rule_data: Dict[str, Any] = Body(...),
    engine: RuleEngine = Depends(get_rule_engine)
):
    """创建分发规则"""
    result = await engine.create_distribution_rule(rule_data)
    if not result:
        raise HTTPException(status_code=500, detail="创建分发规则失败")
    return result


@rule_router.get("/stats")
async def get_rule_stats(
    engine: RuleEngine = Depends(get_rule_engine)
):
    """获取规则统计"""
    return await engine.get_rule_stats()


# 分析统计路由
@analytics_router.get("/summary")
async def get_alarm_summary(
    time_range: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
    aggregator: AlarmAggregator = Depends(get_aggregator)
):
    """获取告警汇总统计"""
    return await aggregator.get_alarm_summary(time_range)


@analytics_router.get("/trends")
async def get_alarm_trends(
    time_range: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
    interval: str = Query("1h", regex="^(1h|1d)$"),
    aggregator: AlarmAggregator = Depends(get_aggregator)
):
    """获取告警趋势"""
    return await aggregator.get_alarm_trends(time_range, interval)


@analytics_router.get("/top")
async def get_top_alarms(
    time_range: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
    limit: int = Query(10, ge=1, le=100),
    aggregator: AlarmAggregator = Depends(get_aggregator)
):
    """获取TOP告警"""
    return await aggregator.get_top_alarms(time_range, limit)


@analytics_router.get("/distribution")
async def get_distribution_stats(
    time_range: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
    aggregator: AlarmAggregator = Depends(get_aggregator)
):
    """获取分发统计"""
    return await aggregator.get_distribution_stats(time_range)


@analytics_router.get("/correlation")
async def get_correlation_analysis(
    time_range: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
    aggregator: AlarmAggregator = Depends(get_aggregator)
):
    """获取关联分析"""
    return await aggregator.get_correlation_analysis(time_range)


@analytics_router.post("/cache/clear")
async def clear_analytics_cache(
    aggregator: AlarmAggregator = Depends(get_aggregator)
):
    """清除分析缓存"""
    await aggregator.clear_cache()
    return {"message": "缓存清除成功"}


# WebSocket路由
@websocket_router.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str = "default"):
    """WebSocket连接端点"""
    from src.services.websocket_manager import connection_manager
    
    await connection_manager.connect(websocket, room)
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = {"type": "echo", "data": data}
            await connection_manager.send_personal_message(message, websocket)
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)


@websocket_router.get("/connections/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计"""
    from src.services.websocket_manager import connection_manager
    return connection_manager.get_connection_stats()


# Webhook告警接收路由
@webhook_router.post("/alarm/{api_token}")
async def receive_webhook_alarm(
    api_token: str,
    alarm_data: Dict[str, Any] = Body(...),
    manager: EndpointManager = Depends(get_endpoint_manager)
):
    """接收Webhook告警"""
    try:
        # 验证API令牌并获取接入点
        endpoint = await manager.get_endpoint_by_token(api_token)
        if not endpoint:
            raise HTTPException(status_code=401, detail="无效的API令牌")
            
        # 更新接入点统计
        await manager.update_endpoint_stats(endpoint.id)
        
        # 处理告警数据
        success = await manager.process_incoming_alarm(endpoint.id, alarm_data)
        
        if success:
            return {
                "status": "success",
                "message": "告警接收成功",
                "endpoint": endpoint.name
            }
        else:
            raise HTTPException(status_code=500, detail="告警处理失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to receive webhook alarm: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@webhook_router.get("/test/{api_token}")
async def test_webhook_endpoint(
    api_token: str,
    manager: EndpointManager = Depends(get_endpoint_manager)
):
    """测试Webhook接入点"""
    try:
        endpoint = await manager.get_endpoint_by_token(api_token)
        if not endpoint:
            raise HTTPException(status_code=401, detail="无效的API令牌")
            
        return {
            "status": "success",
            "message": "Webhook接入点验证成功",
            "endpoint": {
                "id": endpoint.id,
                "name": endpoint.name,
                "type": endpoint.endpoint_type,
                "url": endpoint.webhook_url
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test webhook endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@webhook_router.post("/batch/{api_token}")
async def receive_batch_webhook_alarms(
    api_token: str,
    alarms_data: List[Dict[str, Any]] = Body(...),
    manager: EndpointManager = Depends(get_endpoint_manager)
):
    """批量接收Webhook告警"""
    try:
        endpoint = await manager.get_endpoint_by_token(api_token)
        if not endpoint:
            raise HTTPException(status_code=401, detail="无效的API令牌")
            
        # 更新接入点统计
        await manager.update_endpoint_stats(endpoint.id, len(alarms_data))
        
        success_count = 0
        failed_count = 0
        
        for alarm_data in alarms_data:
            success = await manager.process_incoming_alarm(endpoint.id, alarm_data)
            if success:
                success_count += 1
            else:
                failed_count += 1
                
        return {
            "status": "completed",
            "message": f"批量告警处理完成",
            "endpoint": endpoint.name,
            "total": len(alarms_data),
            "success": success_count,
            "failed": failed_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to receive batch webhook alarms: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")