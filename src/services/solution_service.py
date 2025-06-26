"""
解决方案管理服务
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, desc, func

from src.core.database import async_session_maker
from src.core.logging import get_logger
from src.core.exceptions import (
    DatabaseException, ValidationException,
    ResourceNotFoundException, AuthorizationException
)
from src.models.alarm_processing import (
    ProcessingSolution, SolutionCreate,
    AlarmProcessing, ResolutionMethod
)

logger = get_logger(__name__)


class SolutionService:
    """解决方案管理服务"""
    
    def __init__(self):
        self.logger = logger
    
    async def create_solution(
        self, 
        user_id: int,
        solution_data: SolutionCreate
    ) -> ProcessingSolution:
        """创建解决方案"""
        async with async_session_maker() as session:
            try:
                # 检查标题是否重复
                existing = await session.execute(
                    select(ProcessingSolution).where(
                        ProcessingSolution.title == solution_data.title
                    )
                )
                if existing.scalar_one_or_none():
                    raise ValidationException(
                        "Solution with this title already exists",
                        field="title"
                    )
                
                # 创建解决方案
                solution = ProcessingSolution(
                    title=solution_data.title,
                    description=solution_data.description,
                    category=solution_data.category,
                    solution_steps=solution_data.solution_steps,
                    tags=solution_data.tags,
                    required_tools=solution_data.required_tools,
                    estimated_time_minutes=solution_data.estimated_time_minutes,
                    created_by=user_id,
                    version="1.0"
                )
                
                session.add(solution)
                await session.commit()
                
                self.logger.info(
                    f"Created solution: {solution.title}",
                    extra={
                        "solution_id": solution.id,
                        "user_id": user_id,
                        "category": solution.category
                    }
                )
                
                return solution
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, ValidationException):
                    raise
                raise DatabaseException(f"Failed to create solution: {str(e)}")
    
    async def get_solutions_by_category(
        self, 
        category: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProcessingSolution]:
        """根据分类获取解决方案"""
        async with async_session_maker() as session:
            try:
                query = select(ProcessingSolution).where(
                    and_(
                        ProcessingSolution.category == category,
                        ProcessingSolution.enabled == True
                    )
                ).order_by(desc(ProcessingSolution.usage_count))
                
                result = await session.execute(query.limit(limit).offset(offset))
                return result.scalars().all()
                
            except Exception as e:
                raise DatabaseException(f"Failed to get solutions: {str(e)}")
    
    async def search_solutions(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProcessingSolution]:
        """搜索解决方案"""
        async with async_session_maker() as session:
            try:
                # 构建搜索条件
                conditions = [ProcessingSolution.enabled == True]
                
                if query:
                    conditions.append(
                        or_(
                            ProcessingSolution.title.contains(query),
                            ProcessingSolution.description.contains(query)
                        )
                    )
                
                if categories:
                    conditions.append(ProcessingSolution.category.in_(categories))
                
                # TODO: 实现标签搜索（需要JSON查询）
                
                search_query = select(ProcessingSolution).where(
                    and_(*conditions)
                ).order_by(desc(ProcessingSolution.usage_count))
                
                result = await session.execute(search_query.limit(limit).offset(offset))
                return result.scalars().all()
                
            except Exception as e:
                raise DatabaseException(f"Failed to search solutions: {str(e)}")
    
    async def get_recommended_solutions(
        self,
        alarm_severity: str,
        alarm_source: str,
        alarm_category: Optional[str] = None,
        limit: int = 10
    ) -> List[ProcessingSolution]:
        """获取推荐的解决方案"""
        async with async_session_maker() as session:
            try:
                # 简化的推荐逻辑：根据条件和使用频率推荐
                conditions = [
                    ProcessingSolution.enabled == True,
                    ProcessingSolution.is_approved == True
                ]
                
                # 可以根据告警特征添加更复杂的推荐逻辑
                if alarm_category:
                    conditions.append(ProcessingSolution.category == alarm_category)
                
                query = select(ProcessingSolution).where(
                    and_(*conditions)
                ).order_by(
                    desc(ProcessingSolution.success_rate),
                    desc(ProcessingSolution.usage_count)
                )
                
                result = await session.execute(query.limit(limit))
                return result.scalars().all()
                
            except Exception as e:
                raise DatabaseException(f"Failed to get recommendations: {str(e)}")
    
    async def apply_solution(
        self,
        solution_id: int,
        processing_id: int,
        user_id: int,
        success: bool = True,
        actual_time_minutes: Optional[int] = None,
        notes: Optional[str] = None
    ):
        """应用解决方案并记录结果"""
        async with async_session_maker() as session:
            try:
                # 获取解决方案
                solution = await session.get(ProcessingSolution, solution_id)
                if not solution:
                    raise ResourceNotFoundException("ProcessingSolution", solution_id)
                
                # 获取处理记录
                processing = await session.get(AlarmProcessing, processing_id)
                if not processing:
                    raise ResourceNotFoundException("AlarmProcessing", processing_id)
                
                # 更新解决方案统计
                solution.usage_count += 1
                
                if success:
                    # 简化的成功率计算
                    total_applications = solution.usage_count
                    if solution.success_rate is None:
                        solution.success_rate = 100
                    else:
                        # 计算新的成功率
                        success_count = int(total_applications * solution.success_rate / 100)
                        success_count += 1
                        solution.success_rate = int(success_count * 100 / total_applications)
                    
                    # 更新平均解决时间
                    if actual_time_minutes and solution.avg_resolution_time:
                        solution.avg_resolution_time = int(
                            (solution.avg_resolution_time + actual_time_minutes) / 2
                        )
                    elif actual_time_minutes:
                        solution.avg_resolution_time = actual_time_minutes
                
                # 在处理记录中添加解决方案信息
                if not processing.processing_metadata:
                    processing.processing_metadata = {}
                
                processing.processing_metadata.update({
                    "applied_solution": {
                        "solution_id": solution_id,
                        "solution_title": solution.title,
                        "applied_by": user_id,
                        "applied_at": datetime.utcnow().isoformat(),
                        "success": success,
                        "actual_time_minutes": actual_time_minutes,
                        "notes": notes
                    }
                })
                
                await session.commit()
                
                self.logger.info(
                    f"Applied solution {solution_id} to processing {processing_id}",
                    extra={
                        "solution_id": solution_id,
                        "processing_id": processing_id,
                        "user_id": user_id,
                        "success": success
                    }
                )
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, ResourceNotFoundException):
                    raise
                raise DatabaseException(f"Failed to apply solution: {str(e)}")
    
    async def approve_solution(
        self,
        solution_id: int,
        approver_id: int
    ) -> ProcessingSolution:
        """审批解决方案"""
        async with async_session_maker() as session:
            try:
                solution = await session.get(ProcessingSolution, solution_id)
                if not solution:
                    raise ResourceNotFoundException("ProcessingSolution", solution_id)
                
                solution.is_approved = True
                solution.approved_by = approver_id
                solution.approved_at = datetime.utcnow()
                
                await session.commit()
                
                self.logger.info(
                    f"Approved solution {solution_id}",
                    extra={
                        "solution_id": solution_id,
                        "approver_id": approver_id
                    }
                )
                
                return solution
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, ResourceNotFoundException):
                    raise
                raise DatabaseException(f"Failed to approve solution: {str(e)}")
    
    async def get_solution_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取解决方案统计信息"""
        async with async_session_maker() as session:
            try:
                from datetime import datetime, timedelta
                start_date = datetime.utcnow() - timedelta(days=days)
                
                # 总体统计
                total_solutions = await session.execute(
                    select(func.count(ProcessingSolution.id))
                )
                
                approved_solutions = await session.execute(
                    select(func.count(ProcessingSolution.id)).where(
                        ProcessingSolution.is_approved == True
                    )
                )
                
                # 按分类统计
                category_stats = await session.execute(
                    select(
                        ProcessingSolution.category,
                        func.count(ProcessingSolution.id).label('count'),
                        func.avg(ProcessingSolution.success_rate).label('avg_success_rate')
                    ).group_by(ProcessingSolution.category)
                )
                
                # 最常用的解决方案
                popular_solutions = await session.execute(
                    select(ProcessingSolution).where(
                        ProcessingSolution.enabled == True
                    ).order_by(desc(ProcessingSolution.usage_count)).limit(10)
                )
                
                stats = {
                    "total_solutions": total_solutions.scalar(),
                    "approved_solutions": approved_solutions.scalar(),
                    "by_category": [
                        {
                            "category": row.category,
                            "count": row.count,
                            "avg_success_rate": row.avg_success_rate
                        }
                        for row in category_stats
                    ],
                    "popular_solutions": [
                        {
                            "id": solution.id,
                            "title": solution.title,
                            "usage_count": solution.usage_count,
                            "success_rate": solution.success_rate
                        }
                        for solution in popular_solutions.scalars().all()
                    ]
                }
                
                return stats
                
            except Exception as e:
                raise DatabaseException(f"Failed to get statistics: {str(e)}")