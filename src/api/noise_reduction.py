"""
告警降噪管理API
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.core.auth import get_current_user
from src.core.rbac import require_permission, require_any_permission
from src.core.exceptions import DatabaseException, ValidationException, ResourceNotFoundException
from src.services.noise_reduction_manager import NoiseReductionManager
from src.services.noise_reduction_service import noise_reduction_engine
from src.models.noise_reduction import (
    NoiseReductionRuleCreate, NoiseReductionRuleUpdate, NoiseReductionRuleResponse,
    NoiseRuleTestRequest, NoiseRuleTestResult, NoiseReductionStatsResponse
)
from src.models.alarm import User

router = APIRouter(prefix="/api/v1/noise-reduction", tags=["noise-reduction"])


# 规则管理 API

@router.post("/rules", response_model=NoiseReductionRuleResponse)
@require_permission("config.update")
async def create_noise_rule(
    rule_data: NoiseReductionRuleCreate,
    current_user: User = Depends(get_current_user)
):
    """创建降噪规则"""
    manager = NoiseReductionManager()
    
    try:
        rule = await manager.create_rule(rule_data, current_user.id)
        return NoiseReductionRuleResponse.from_orm(rule)
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules", response_model=List[NoiseReductionRuleResponse])
@require_any_permission(["config.read", "alarms.read"])
async def get_noise_rules(
    enabled_only: bool = Query(False, description="只返回启用的规则"),
    rule_type: Optional[str] = Query(None, description="规则类型过滤"),
    limit: int = Query(50, ge=1, le=100, description="限制数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user)
):
    """获取降噪规则列表"""
    manager = NoiseReductionManager()
    
    try:
        rules = await manager.get_rules(enabled_only, rule_type, limit, offset)
        return [NoiseReductionRuleResponse.from_orm(rule) for rule in rules]
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/{rule_id}", response_model=NoiseReductionRuleResponse)
@require_any_permission(["config.read", "alarms.read"])
async def get_noise_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user)
):
    """获取单个降噪规则详情"""
    manager = NoiseReductionManager()
    
    try:
        rule = await manager.get_rule(rule_id)
        return NoiseReductionRuleResponse.from_orm(rule)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}", response_model=NoiseReductionRuleResponse)
@require_permission("config.update")
async def update_noise_rule(
    rule_id: int,
    rule_data: NoiseReductionRuleUpdate,
    current_user: User = Depends(get_current_user)
):
    """更新降噪规则"""
    manager = NoiseReductionManager()
    
    try:
        rule = await manager.update_rule(rule_id, rule_data, current_user.id)
        return NoiseReductionRuleResponse.from_orm(rule)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}")
@require_permission("config.update")
async def delete_noise_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user)
):
    """删除降噪规则"""
    manager = NoiseReductionManager()
    
    try:
        success = await manager.delete_rule(rule_id, current_user.id)
        return {"success": success, "message": "Rule deleted successfully"}
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/{rule_id}/toggle")
@require_permission("config.update")
async def toggle_noise_rule(
    rule_id: int,
    enabled: bool,
    current_user: User = Depends(get_current_user)
):
    """启用/禁用降噪规则"""
    manager = NoiseReductionManager()
    
    try:
        rule = await manager.toggle_rule(rule_id, enabled, current_user.id)
        action = "enabled" if enabled else "disabled"
        return {
            "success": True,
            "message": f"Rule {action} successfully",
            "rule": NoiseReductionRuleResponse.from_orm(rule)
        }
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


# 规则测试 API

@router.post("/rules/test", response_model=NoiseRuleTestResult)
@require_permission("config.update")
async def test_noise_rule(
    test_request: NoiseRuleTestRequest,
    current_user: User = Depends(get_current_user)
):
    """测试降噪规则"""
    manager = NoiseReductionManager()
    
    try:
        result = await manager.test_rule(test_request)
        return result
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-alarm")
@require_permission("config.update")
async def test_alarm_processing(
    alarm_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """测试单个告警的降噪处理"""
    try:
        passed, action, result = await noise_reduction_engine.process_alarm(alarm_data)
        
        return {
            "alarm": alarm_data,
            "processing_result": {
                "passed": passed,
                "action": action,
                "details": result
            },
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


# 规则模板 API

@router.get("/templates")
@require_any_permission(["config.read", "config.update"])
async def get_rule_templates(
    current_user: User = Depends(get_current_user)
):
    """获取规则模板"""
    manager = NoiseReductionManager()
    
    try:
        templates = await manager.get_rule_templates()
        return {
            "templates": templates,
            "template_count": len(templates)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/{template_name}/create-rule", response_model=NoiseReductionRuleResponse)
@require_permission("config.update")
async def create_rule_from_template(
    template_name: str,
    rule_name: str,
    custom_params: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user)
):
    """从模板创建规则"""
    manager = NoiseReductionManager()
    
    try:
        rule = await manager.create_rule_from_template(
            template_name, rule_name, custom_params or {}, current_user.id
        )
        return NoiseReductionRuleResponse.from_orm(rule)
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


# 统计和监控 API

@router.get("/stats/rules/{rule_id}")
@require_any_permission(["analytics.read", "config.read"])
async def get_rule_stats(
    rule_id: int,
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: User = Depends(get_current_user)
):
    """获取单个规则的执行统计"""
    manager = NoiseReductionManager()
    
    try:
        stats = await manager.get_rule_stats(rule_id, start_date, end_date)
        return {
            "rule_id": rule_id,
            "stats": stats,
            "period": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/system")
@require_any_permission(["analytics.read", "config.read"])
async def get_system_noise_stats(
    current_user: User = Depends(get_current_user)
):
    """获取系统级降噪统计"""
    manager = NoiseReductionManager()
    
    try:
        stats = await manager.get_system_stats()
        return {
            "system_stats": stats,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/overview")
@require_any_permission(["analytics.read", "config.read"])
async def get_noise_reduction_overview(
    days: int = Query(7, ge=1, le=30, description="统计天数"),
    current_user: User = Depends(get_current_user)
):
    """获取降噪效果概览"""
    from src.core.database import async_session_maker
    from src.models.noise_reduction import NoiseRuleExecutionLog
    from sqlalchemy import select, func, and_
    
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        async with async_session_maker() as session:
            # 总体统计
            total_stats = await session.execute(
                select(
                    func.count(NoiseRuleExecutionLog.id).label('total_processed'),
                    func.sum(func.cast(NoiseRuleExecutionLog.matched, int)).label('total_matched'),
                    func.avg(NoiseRuleExecutionLog.execution_time_ms).label('avg_processing_time')
                ).where(NoiseRuleExecutionLog.executed_at >= start_date)
            )
            total_result = total_stats.first()
            
            # 按动作分组统计
            action_stats = await session.execute(
                select(
                    NoiseRuleExecutionLog.action_taken,
                    func.count(NoiseRuleExecutionLog.id).label('count')
                )
                .where(
                    and_(
                        NoiseRuleExecutionLog.executed_at >= start_date,
                        NoiseRuleExecutionLog.matched == True
                    )
                )
                .group_by(NoiseRuleExecutionLog.action_taken)
            )
            
            # 每日趋势
            daily_stats = await session.execute(
                select(
                    func.date(NoiseRuleExecutionLog.executed_at).label('date'),
                    func.count(NoiseRuleExecutionLog.id).label('processed'),
                    func.sum(func.cast(NoiseRuleExecutionLog.matched, int)).label('matched')
                )
                .where(NoiseRuleExecutionLog.executed_at >= start_date)
                .group_by(func.date(NoiseRuleExecutionLog.executed_at))
                .order_by(func.date(NoiseRuleExecutionLog.executed_at))
            )
            
            return {
                "period": {
                    "start_date": start_date,
                    "end_date": datetime.utcnow(),
                    "days": days
                },
                "summary": {
                    "total_processed": total_result.total_processed or 0,
                    "total_matched": total_result.total_matched or 0,
                    "match_rate": (total_result.total_matched or 0) / (total_result.total_processed or 1),
                    "avg_processing_time_ms": total_result.avg_processing_time or 0
                },
                "action_distribution": {
                    row.action_taken: row.count for row in action_stats
                },
                "daily_trend": [
                    {
                        "date": row.date.isoformat(),
                        "processed": row.processed,
                        "matched": row.matched,
                        "match_rate": row.matched / row.processed if row.processed > 0 else 0
                    }
                    for row in daily_stats
                ]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 系统管理 API

@router.post("/clear-cache")
@require_permission("config.update")
async def clear_noise_reduction_cache(
    current_user: User = Depends(get_current_user)
):
    """清除降噪规则缓存"""
    try:
        noise_reduction_engine.clear_cache()
        return {
            "success": True,
            "message": "Noise reduction cache cleared successfully",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engine-stats")
@require_any_permission(["analytics.read", "config.read"])
async def get_engine_stats(
    current_user: User = Depends(get_current_user)
):
    """获取降噪引擎统计"""
    try:
        stats = noise_reduction_engine.get_stats()
        return {
            "engine_stats": stats,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 批量操作 API

@router.post("/rules/batch-toggle")
@require_permission("config.update")
async def batch_toggle_rules(
    rule_ids: List[int],
    enabled: bool,
    current_user: User = Depends(get_current_user)
):
    """批量启用/禁用规则"""
    manager = NoiseReductionManager()
    
    try:
        results = []
        for rule_id in rule_ids:
            try:
                rule = await manager.toggle_rule(rule_id, enabled, current_user.id)
                results.append({
                    "rule_id": rule_id,
                    "success": True,
                    "rule": NoiseReductionRuleResponse.from_orm(rule)
                })
            except Exception as e:
                results.append({
                    "rule_id": rule_id,
                    "success": False,
                    "error": str(e)
                })
        
        successful = sum(1 for r in results if r["success"])
        action = "enabled" if enabled else "disabled"
        
        return {
            "total_rules": len(rule_ids),
            "successful": successful,
            "failed": len(rule_ids) - successful,
            "message": f"{successful} rules {action} successfully",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-alarms")
@require_permission("alarms.create")
async def process_alarms_with_noise_reduction(
    alarms: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
):
    """批量处理告警降噪"""
    try:
        start_time = datetime.utcnow()
        
        # 批量处理告警
        processed_alarms = await noise_reduction_engine.batch_process_alarms(alarms)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # 统计结果
        original_count = len(alarms)
        processed_count = len(processed_alarms)
        suppressed_count = original_count - processed_count
        
        return {
            "processing_summary": {
                "original_count": original_count,
                "processed_count": processed_count,
                "suppressed_count": suppressed_count,
                "suppression_rate": suppressed_count / original_count if original_count > 0 else 0,
                "processing_time_ms": processing_time
            },
            "processed_alarms": processed_alarms,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


# 健康检查

@router.get("/health")
async def noise_reduction_health():
    """降噪系统健康检查"""
    try:
        manager = NoiseReductionManager()
        
        # 检查活跃规则数量
        active_rules = await manager.get_rules(enabled_only=True, limit=1000)
        
        # 检查引擎统计
        engine_stats = noise_reduction_engine.get_stats()
        
        # 简单的健康检查
        health_status = "healthy"
        issues = []
        
        if len(active_rules) == 0:
            issues.append("No active noise reduction rules configured")
        
        if engine_stats["total_processed"] == 0:
            issues.append("No alarms have been processed yet")
        
        if issues:
            health_status = "warning"
        
        return {
            "status": health_status,
            "active_rules": len(active_rules),
            "engine_stats": engine_stats,
            "issues": issues,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }