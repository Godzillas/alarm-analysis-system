"""
解决方案管理API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct, and_

from src.core.database import get_db_session
from src.core.responses import DataResponse, ListResponse, data_response, list_response
from src.core.exceptions import AlarmSystemException, to_http_exception
from src.models.alarm_processing import SolutionCreate, ProcessingSolution
from src.services.solution_service import SolutionService

router = APIRouter()


def get_solution_service() -> SolutionService:
    """获取解决方案服务实例"""
    return SolutionService()


def get_current_user_id() -> int:
    """获取当前用户ID（简化版本）"""
    return 1


@router.post("/solutions", response_model=DataResponse[dict])
async def create_solution(
    solution_data: SolutionCreate,
    service: SolutionService = Depends(get_solution_service),
    current_user: int = Depends(get_current_user_id)
):
    """创建解决方案"""
    try:
        solution = await service.create_solution(current_user, solution_data)
        
        response = {
            "id": solution.id,
            "title": solution.title,
            "category": solution.category,
            "version": solution.version,
            "created_at": solution.created_at
        }
        
        return data_response(response, "解决方案创建成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/solutions/categories/{category}", response_model=ListResponse[dict])
async def get_solutions_by_category(
    category: str,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    service: SolutionService = Depends(get_solution_service)
):
    """根据分类获取解决方案"""
    try:
        solutions = await service.get_solutions_by_category(category, limit, offset)
        
        response = [
            {
                "id": solution.id,
                "title": solution.title,
                "description": solution.description,
                "category": solution.category,
                "tags": solution.tags,
                "usage_count": solution.usage_count,
                "success_rate": solution.success_rate,
                "estimated_time_minutes": solution.estimated_time_minutes,
                "is_approved": solution.is_approved
            }
            for solution in solutions
        ]
        
        return list_response(response, len(response), "获取成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/solutions/search", response_model=ListResponse[dict])
async def search_solutions(
    q: str = Query(..., description="搜索关键词"),
    categories: Optional[List[str]] = Query(None),
    tags: Optional[List[str]] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    service: SolutionService = Depends(get_solution_service)
):
    """搜索解决方案"""
    try:
        solutions = await service.search_solutions(q, categories, tags, limit, offset)
        
        response = [
            {
                "id": solution.id,
                "title": solution.title,
                "description": solution.description,
                "category": solution.category,
                "tags": solution.tags,
                "usage_count": solution.usage_count,
                "success_rate": solution.success_rate,
                "estimated_time_minutes": solution.estimated_time_minutes,
                "is_approved": solution.is_approved
            }
            for solution in solutions
        ]
        
        return list_response(response, len(response), "搜索成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/solutions/recommendations", response_model=ListResponse[dict])
async def get_recommended_solutions(
    alarm_severity: str,
    alarm_source: str,
    alarm_category: Optional[str] = None,
    limit: int = Query(10, le=20),
    service: SolutionService = Depends(get_solution_service)
):
    """获取推荐的解决方案"""
    try:
        solutions = await service.get_recommended_solutions(
            alarm_severity, alarm_source, alarm_category, limit
        )
        
        response = [
            {
                "id": solution.id,
                "title": solution.title,
                "description": solution.description,
                "category": solution.category,
                "solution_steps": solution.solution_steps,
                "required_tools": solution.required_tools,
                "estimated_time_minutes": solution.estimated_time_minutes,
                "usage_count": solution.usage_count,
                "success_rate": solution.success_rate
            }
            for solution in solutions
        ]
        
        return list_response(response, len(response), "推荐获取成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/solutions/{solution_id}", response_model=DataResponse[dict])
async def get_solution_detail(
    solution_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """获取解决方案详情"""
    try:
        from sqlalchemy import select
        from src.models.alarm_processing import ProcessingSolution
        
        result = await db.execute(
            select(ProcessingSolution).where(ProcessingSolution.id == solution_id)
        )
        solution = result.scalar_one_or_none()
        
        if not solution:
            raise HTTPException(status_code=404, detail="解决方案未找到")
        
        response = {
            "id": solution.id,
            "title": solution.title,
            "description": solution.description,
            "category": solution.category,
            "tags": solution.tags,
            "solution_steps": solution.solution_steps,
            "required_tools": solution.required_tools,
            "required_permissions": solution.required_permissions,
            "estimated_time_minutes": solution.estimated_time_minutes,
            "applicable_conditions": solution.applicable_conditions,
            "severity_filter": solution.severity_filter,
            "source_filter": solution.source_filter,
            "usage_count": solution.usage_count,
            "success_rate": solution.success_rate,
            "avg_resolution_time": solution.avg_resolution_time,
            "version": solution.version,
            "is_approved": solution.is_approved,
            "approved_at": solution.approved_at,
            "created_at": solution.created_at,
            "updated_at": solution.updated_at
        }
        
        return data_response(response, "获取成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取解决方案详情失败: {str(e)}")


@router.post("/solutions/{solution_id}/apply", response_model=DataResponse[dict])
async def apply_solution(
    solution_id: int,
    processing_id: int,
    success: bool = True,
    actual_time_minutes: Optional[int] = None,
    notes: Optional[str] = None,
    service: SolutionService = Depends(get_solution_service),
    current_user: int = Depends(get_current_user_id)
):
    """应用解决方案"""
    try:
        await service.apply_solution(
            solution_id, processing_id, current_user, success, actual_time_minutes, notes
        )
        
        return data_response(
            {"solution_id": solution_id, "processing_id": processing_id},
            "解决方案应用成功"
        )
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.post("/solutions/{solution_id}/approve", response_model=DataResponse[dict])
async def approve_solution(
    solution_id: int,
    service: SolutionService = Depends(get_solution_service),
    current_user: int = Depends(get_current_user_id)
):
    """审批解决方案"""
    try:
        solution = await service.approve_solution(solution_id, current_user)
        
        response = {
            "id": solution.id,
            "title": solution.title,
            "is_approved": solution.is_approved,
            "approved_at": solution.approved_at
        }
        
        return data_response(response, "解决方案审批成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/solutions/statistics/overview", response_model=DataResponse[dict])
async def get_solution_statistics(
    days: int = Query(30, ge=1, le=365),
    service: SolutionService = Depends(get_solution_service)
):
    """获取解决方案统计信息"""
    try:
        stats = await service.get_solution_statistics(days)
        return data_response(stats, "统计信息获取成功")
        
    except AlarmSystemException as e:
        raise to_http_exception(e)


@router.get("/solutions/categories", response_model=DataResponse[List[str]])
async def get_solution_categories(
    db: AsyncSession = Depends(get_db_session)
):
    """获取解决方案分类列表"""
    try:
        from sqlalchemy import select, distinct
        from src.models.alarm_processing import ProcessingSolution
        
        result = await db.execute(
            select(distinct(ProcessingSolution.category)).where(
                ProcessingSolution.enabled == True
            )
        )
        categories = [row[0] for row in result.fetchall()]
        
        return data_response(categories, "获取成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分类失败: {str(e)}")


@router.get("/solutions/tags", response_model=DataResponse[List[str]])
async def get_solution_tags(
    db: AsyncSession = Depends(get_db_session)
):
    """获取解决方案标签列表"""
    try:
        from sqlalchemy import select
        from src.models.alarm_processing import ProcessingSolution
        
        # 简化版本：从数据库中提取所有标签
        result = await db.execute(
            select(ProcessingSolution.tags).where(
                and_(
                    ProcessingSolution.enabled == True,
                    ProcessingSolution.tags.is_not(None)
                )
            )
        )
        
        all_tags = set()
        for row in result.fetchall():
            if row[0]:  # tags 不为空
                all_tags.update(row[0])
        
        return data_response(list(all_tags), "获取成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取标签失败: {str(e)}")