"""
告警处理API接口
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.responses import DataResponse, ListResponse, data_response, list_response
from src.core.exceptions import AlarmSystemException, to_http_exception
from src.models.alarm_processing import (
    AlarmProcessingCreate, AlarmProcessingUpdate, AlarmProcessingAction,
    CommentCreate, AlarmProcessingResponse, CommentResponse, ProcessingHistoryResponse,
    AlarmProcessingStatus, AlarmPriority, ProcessingActionType, ResolutionMethod
)
from src.services.alarm_processing_service import AlarmProcessingService

router = APIRouter()


def get_processing_service() -> AlarmProcessingService:
    """获取告警处理服务实例"""
    return AlarmProcessingService()


def get_current_user_id() -> int:
    """获取当前用户ID（简化版本，实际应该从JWT token中获取）"""
    # TODO: 实现真正的用户认证
    return 1


@router.post("/alarms/{alarm_id}/processing", response_model=DataResponse[AlarmProcessingResponse])
async def create_alarm_processing(
    alarm_id: int,
    processing_data: AlarmProcessingCreate,
    service: AlarmProcessingService = Depends(get_processing_service),
    current_user: int = Depends(get_current_user_id)
):
    """创建告警处理记录"""
    try:
        processing_data.alarm_id = alarm_id
        processing = await service.create_processing(alarm_id, current_user, processing_data)
        
        response = AlarmProcessingResponse.from_orm(processing)
        return data_response(response, "告警处理记录创建成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/alarms/{alarm_id}/processing", response_model=DataResponse[AlarmProcessingResponse])
async def get_alarm_processing(
    alarm_id: int,
    service: AlarmProcessingService = Depends(get_processing_service)
):
    """获取告警处理记录"""
    try:
        processing = await service.get_processing_by_alarm(alarm_id)
        if not processing:
            raise HTTPException(status_code=404, detail="告警处理记录未找到")
        
        response = AlarmProcessingResponse.from_orm(processing)
        return data_response(response, "获取成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.post("/processing/{processing_id}/acknowledge", response_model=DataResponse[AlarmProcessingResponse])
async def acknowledge_alarm(
    processing_id: int,
    note: Optional[str] = None,
    service: AlarmProcessingService = Depends(get_processing_service),
    current_user: int = Depends(get_current_user_id)
):
    """确认告警"""
    try:
        processing = await service.acknowledge_alarm(processing_id, current_user, note)
        
        response = AlarmProcessingResponse.from_orm(processing)
        return data_response(response, "告警确认成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.post("/processing/{processing_id}/assign", response_model=DataResponse[AlarmProcessingResponse])
async def assign_alarm(
    processing_id: int,
    assigned_to: int,
    notes: Optional[str] = None,
    service: AlarmProcessingService = Depends(get_processing_service),
    current_user: int = Depends(get_current_user_id)
):
    """分配告警"""
    try:
        processing = await service.assign_alarm(processing_id, current_user, assigned_to, notes)
        
        response = AlarmProcessingResponse.from_orm(processing)
        return data_response(response, "告警分配成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.put("/processing/{processing_id}/status", response_model=DataResponse[AlarmProcessingResponse])
async def update_processing_status(
    processing_id: int,
    new_status: AlarmProcessingStatus,
    notes: Optional[str] = None,
    service: AlarmProcessingService = Depends(get_processing_service),
    current_user: int = Depends(get_current_user_id)
):
    """更新处理状态"""
    try:
        processing = await service.update_status(processing_id, current_user, new_status, notes)
        
        response = AlarmProcessingResponse.from_orm(processing)
        return data_response(response, "状态更新成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.post("/processing/{processing_id}/resolve", response_model=DataResponse[AlarmProcessingResponse])
async def resolve_alarm(
    processing_id: int,
    resolution_method: ResolutionMethod,
    resolution_note: str,
    actual_effort_hours: Optional[int] = None,
    service: AlarmProcessingService = Depends(get_processing_service),
    current_user: int = Depends(get_current_user_id)
):
    """解决告警"""
    try:
        processing = await service.resolve_alarm(
            processing_id, 
            current_user, 
            resolution_method, 
            resolution_note,
            actual_effort_hours
        )
        
        response = AlarmProcessingResponse.from_orm(processing)
        return data_response(response, "告警解决成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.post("/processing/{processing_id}/escalate", response_model=DataResponse[AlarmProcessingResponse])
async def escalate_alarm(
    processing_id: int,
    escalated_to: int,
    escalation_reason: str,
    service: AlarmProcessingService = Depends(get_processing_service),
    current_user: int = Depends(get_current_user_id)
):
    """升级告警"""
    try:
        processing = await service.escalate_alarm(
            processing_id, 
            current_user, 
            escalated_to, 
            escalation_reason
        )
        
        response = AlarmProcessingResponse.from_orm(processing)
        return data_response(response, "告警升级成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.post("/processing/{processing_id}/comments", response_model=DataResponse[CommentResponse])
async def add_processing_comment(
    processing_id: int,
    comment_data: CommentCreate,
    service: AlarmProcessingService = Depends(get_processing_service),
    current_user: int = Depends(get_current_user_id)
):
    """添加处理评论"""
    try:
        comment = await service.add_comment(processing_id, current_user, comment_data)
        
        response = CommentResponse.from_orm(comment)
        return data_response(response, "评论添加成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/processing/{processing_id}/comments", response_model=ListResponse[CommentResponse])
async def get_processing_comments(
    processing_id: int,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """获取处理评论列表"""
    try:
        from sqlalchemy import select
        from src.models.alarm_processing import AlarmProcessingComment
        
        # 查询评论
        query = select(AlarmProcessingComment).where(
            AlarmProcessingComment.processing_id == processing_id
        ).order_by(AlarmProcessingComment.created_at.desc())
        
        result = await db.execute(query.limit(limit).offset(offset))
        comments = result.scalars().all()
        
        # 查询总数
        count_query = select(func.count()).select_from(AlarmProcessingComment).where(
            AlarmProcessingComment.processing_id == processing_id
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        responses = [CommentResponse.from_orm(comment) for comment in comments]
        return list_response(responses, total, "获取成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取评论失败: {str(e)}")


@router.get("/processing/{processing_id}/history", response_model=ListResponse[ProcessingHistoryResponse])
async def get_processing_history(
    processing_id: int,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """获取处理历史记录"""
    try:
        from sqlalchemy import select, func
        from src.models.alarm_processing import AlarmProcessingHistory
        
        # 查询历史记录
        query = select(AlarmProcessingHistory).where(
            AlarmProcessingHistory.processing_id == processing_id
        ).order_by(AlarmProcessingHistory.action_at.desc())
        
        result = await db.execute(query.limit(limit).offset(offset))
        history = result.scalars().all()
        
        # 查询总数
        count_query = select(func.count()).select_from(AlarmProcessingHistory).where(
            AlarmProcessingHistory.processing_id == processing_id
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        responses = [ProcessingHistoryResponse.from_orm(record) for record in history]
        return list_response(responses, total, "获取成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")


@router.get("/users/{user_id}/assignments", response_model=ListResponse[AlarmProcessingResponse])
async def get_user_assignments(
    user_id: int,
    status_filter: Optional[List[AlarmProcessingStatus]] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    service: AlarmProcessingService = Depends(get_processing_service)
):
    """获取用户分配的处理任务"""
    try:
        status_list = [s.value for s in status_filter] if status_filter else None
        assignments = await service.get_user_assignments(user_id, status_list, limit, offset)
        
        responses = [AlarmProcessingResponse.from_orm(assignment) for assignment in assignments]
        return list_response(responses, len(responses), "获取成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/my-assignments", response_model=ListResponse[AlarmProcessingResponse])
async def get_my_assignments(
    status_filter: Optional[List[AlarmProcessingStatus]] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    service: AlarmProcessingService = Depends(get_processing_service),
    current_user: int = Depends(get_current_user_id)
):
    """获取我的处理任务"""
    try:
        status_list = [s.value for s in status_filter] if status_filter else None
        assignments = await service.get_user_assignments(current_user, status_list, limit, offset)
        
        responses = [AlarmProcessingResponse.from_orm(assignment) for assignment in assignments]
        return list_response(responses, len(responses), "获取成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/processing/statistics")
async def get_processing_statistics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db_session)
):
    """获取处理统计信息"""
    try:
        from sqlalchemy import select, func, and_
        from src.models.alarm_processing import AlarmProcessing
        from datetime import datetime, timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 基础统计
        base_query = select(AlarmProcessing).where(
            AlarmProcessing.created_at >= start_date
        )
        
        # 总数统计
        stats = {}
        
        # 按状态统计
        status_stats = await db.execute(
            select(
                AlarmProcessing.status,
                func.count(AlarmProcessing.id).label('count')
            ).where(
                AlarmProcessing.created_at >= start_date
            ).group_by(AlarmProcessing.status)
        )
        
        stats['by_status'] = {row.status: row.count for row in status_stats}
        
        # 按优先级统计
        priority_stats = await db.execute(
            select(
                AlarmProcessing.priority,
                func.count(AlarmProcessing.id).label('count')
            ).where(
                AlarmProcessing.created_at >= start_date
            ).group_by(AlarmProcessing.priority)
        )
        
        stats['by_priority'] = {row.priority: row.count for row in priority_stats}
        
        # SLA统计
        sla_stats = await db.execute(
            select(
                func.count().label('total'),
                func.sum(func.case((AlarmProcessing.sla_breached == True, 1), else_=0)).label('breached'),
                func.avg(AlarmProcessing.response_time_minutes).label('avg_response_time'),
                func.avg(AlarmProcessing.resolution_time_minutes).label('avg_resolution_time')
            ).where(
                AlarmProcessing.created_at >= start_date
            )
        )
        
        sla_row = sla_stats.first()
        stats['sla'] = {
            'total': sla_row.total or 0,
            'breached': sla_row.breached or 0,
            'breach_rate': (sla_row.breached / sla_row.total * 100) if sla_row.total else 0,
            'avg_response_time_minutes': sla_row.avg_response_time,
            'avg_resolution_time_minutes': sla_row.avg_resolution_time
        }
        
        return data_response(stats, "统计信息获取成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


# 枚举值端点，用于前端下拉选择
@router.get("/enums/processing-status")
async def get_processing_status_options():
    """获取处理状态选项"""
    options = [
        {"value": status.value, "label": status.value} 
        for status in AlarmProcessingStatus
    ]
    return data_response(options, "获取成功")


@router.get("/enums/priority")
async def get_priority_options():
    """获取优先级选项"""
    options = [
        {"value": priority.value, "label": priority.value} 
        for priority in AlarmPriority
    ]
    return data_response(options, "获取成功")


@router.get("/enums/resolution-method")
async def get_resolution_method_options():
    """获取解决方法选项"""
    options = [
        {"value": method.value, "label": method.value} 
        for method in ResolutionMethod
    ]
    return data_response(options, "获取成功")