"""
系统管理API路由
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import selectinload

from src.core.database import get_db_session
from src.models.alarm import (
    System, User, SystemCreate, SystemUpdate, SystemResponse, 
    PaginatedResponse, user_system_association
)
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/", response_model=PaginatedResponse[SystemResponse])
async def get_systems(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=1000, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    enabled: Optional[bool] = Query(None, description="启用状态"),
    db: AsyncSession = Depends(get_db_session)
):
    """获取系统列表"""
    try:
        # 构建查询条件
        conditions = []
        if search:
            conditions.append(
                or_(
                    System.name.ilike(f"%{search}%"),
                    System.code.ilike(f"%{search}%"),
                    System.description.ilike(f"%{search}%")
                )
            )
        if enabled is not None:
            conditions.append(System.enabled == enabled)
        
        # 查询数据
        query = select(System)
        if conditions:
            query = query.where(and_(*conditions))
        
        # 总数查询
        count_query = select(func.count(System.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分页查询
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(System.created_at.desc())
        
        result = await db.execute(query)
        systems = result.scalars().all()
        
        # 如果没有系统，创建一个默认的演示系统
        if total == 0 and page == 1:
            try:
                demo_system = System(
                    name="演示系统",
                    code="demo", 
                    description="系统演示用途",
                    enabled=True
                )
                db.add(demo_system)
                await db.commit()
                await db.refresh(demo_system)
                
                systems = [demo_system]
                total = 1
                logger.info("创建了默认演示系统")
            except Exception as create_error:
                logger.warning(f"创建默认系统失败: {str(create_error)}")
                # 如果创建失败，继续返回空结果
                pass
        
        # 计算总页数
        pages = (total + page_size - 1) // page_size if total > 0 else 1
        
        return PaginatedResponse(
            data=[SystemResponse.model_validate(system) for system in systems],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"获取系统列表失败: {str(e)}")
        # 返回空的分页结果而不是抛出异常
        return PaginatedResponse(
            data=[],
            total=0,
            page=page,
            page_size=page_size,
            pages=1
        )


@router.post("/", response_model=SystemResponse)
async def create_system(
    system_data: SystemCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """创建系统"""
    try:
        # 检查系统名称是否已存在
        existing_name = await db.execute(
            select(System).where(System.name == system_data.name)
        )
        if existing_name.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="系统名称已存在")
        
        # 检查系统编码是否已存在
        existing_code = await db.execute(
            select(System).where(System.code == system_data.code)
        )
        if existing_code.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="系统编码已存在")
        
        # 创建系统
        system = System(**system_data.model_dump())
        db.add(system)
        await db.commit()
        await db.refresh(system)
        
        logger.info(f"创建系统成功: {system.name} ({system.code})")
        return SystemResponse.model_validate(system)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"创建系统失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建系统失败")


@router.get("/{system_id}", response_model=SystemResponse)
async def get_system(
    system_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """获取系统详情"""
    try:
        query = select(System).where(System.id == system_id)
        query = query.options(selectinload(System.users))
        
        result = await db.execute(query)
        system = result.scalar_one_or_none()
        
        if not system:
            raise HTTPException(status_code=404, detail="系统不存在")
        
        return SystemResponse.model_validate(system)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取系统详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取系统详情失败")


@router.put("/{system_id}", response_model=SystemResponse)
async def update_system(
    system_id: int,
    system_data: SystemUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """更新系统"""
    try:
        # 查询系统
        result = await db.execute(
            select(System).where(System.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            raise HTTPException(status_code=404, detail="系统不存在")
        
        # 检查名称唯一性
        if system_data.name and system_data.name != system.name:
            existing = await db.execute(
                select(System).where(
                    and_(System.name == system_data.name, System.id != system_id)
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="系统名称已存在")
        
        # 检查编码唯一性
        if system_data.code and system_data.code != system.code:
            existing = await db.execute(
                select(System).where(
                    and_(System.code == system_data.code, System.id != system_id)
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="系统编码已存在")
        
        # 更新字段
        update_data = system_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(system, field, value)
        
        await db.commit()
        await db.refresh(system)
        
        logger.info(f"更新系统成功: {system.name} ({system.code})")
        return SystemResponse.model_validate(system)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新系统失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新系统失败")


@router.delete("/{system_id}")
async def delete_system(
    system_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """删除系统"""
    try:
        # 查询系统
        result = await db.execute(
            select(System).where(System.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            raise HTTPException(status_code=404, detail="系统不存在")
        
        # 检查是否有关联的告警
        from src.models.alarm import AlarmTable
        alarm_result = await db.execute(
            select(func.count(AlarmTable.id)).where(AlarmTable.system_id == system_id)
        )
        alarm_count = alarm_result.scalar()
        
        if alarm_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"无法删除系统，存在 {alarm_count} 个关联告警"
            )
        
        # 检查是否有关联的接入点
        from src.models.alarm import Endpoint
        endpoint_result = await db.execute(
            select(func.count(Endpoint.id)).where(Endpoint.system_id == system_id)
        )
        endpoint_count = endpoint_result.scalar()
        
        if endpoint_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"无法删除系统，存在 {endpoint_count} 个关联接入点"
            )
        
        # 删除用户关联
        await db.execute(
            user_system_association.delete().where(
                user_system_association.c.system_id == system_id
            )
        )
        
        # 删除系统
        await db.delete(system)
        await db.commit()
        
        logger.info(f"删除系统成功: {system.name} ({system.code})")
        return {"message": "删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除系统失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除系统失败")


@router.get("/{system_id}/users", response_model=List[dict])
async def get_system_users(
    system_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """获取系统关联的用户"""
    try:
        # 检查系统是否存在
        system_result = await db.execute(
            select(System).where(System.id == system_id)
        )
        system = system_result.scalar_one_or_none()
        
        if not system:
            raise HTTPException(status_code=404, detail="系统不存在")
        
        # 查询关联用户
        query = select(User).join(
            user_system_association,
            User.id == user_system_association.c.user_id
        ).where(user_system_association.c.system_id == system_id)
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        return [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active
            }
            for user in users
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取系统用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取系统用户失败")


@router.post("/{system_id}/users/{user_id}")
async def add_user_to_system(
    system_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """将用户添加到系统"""
    try:
        # 检查系统是否存在
        system_result = await db.execute(
            select(System).where(System.id == system_id)
        )
        system = system_result.scalar_one_or_none()
        
        if not system:
            raise HTTPException(status_code=404, detail="系统不存在")
        
        # 检查用户是否存在
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 检查关联是否已存在
        existing = await db.execute(
            select(user_system_association).where(
                and_(
                    user_system_association.c.user_id == user_id,
                    user_system_association.c.system_id == system_id
                )
            )
        )
        
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="用户已在该系统中")
        
        # 创建关联
        await db.execute(
            user_system_association.insert().values(
                user_id=user_id,
                system_id=system_id
            )
        )
        await db.commit()
        
        logger.info(f"用户 {user.username} 已添加到系统 {system.name}")
        return {"message": "添加成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"添加用户到系统失败: {str(e)}")
        raise HTTPException(status_code=500, detail="添加用户到系统失败")


@router.delete("/{system_id}/users/{user_id}")
async def remove_user_from_system(
    system_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """从系统中移除用户"""
    try:
        # 检查关联是否存在
        existing = await db.execute(
            select(user_system_association).where(
                and_(
                    user_system_association.c.user_id == user_id,
                    user_system_association.c.system_id == system_id
                )
            )
        )
        
        if not existing.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="用户不在该系统中")
        
        # 删除关联
        await db.execute(
            user_system_association.delete().where(
                and_(
                    user_system_association.c.user_id == user_id,
                    user_system_association.c.system_id == system_id
                )
            )
        )
        await db.commit()
        
        logger.info(f"用户 {user_id} 已从系统 {system_id} 中移除")
        return {"message": "移除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"从系统移除用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail="从系统移除用户失败")


@router.get("/{system_id}/stats")
async def get_system_stats(
    system_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """获取系统统计信息"""
    try:
        # 检查系统是否存在
        system_result = await db.execute(
            select(System).where(System.id == system_id)
        )
        system = system_result.scalar_one_or_none()
        
        if not system:
            raise HTTPException(status_code=404, detail="系统不存在")
        
        # 统计告警数量
        from src.models.alarm import AlarmTable
        alarm_stats = await db.execute(
            select(
                func.count(AlarmTable.id).label('total_alarms'),
                func.sum(case((AlarmTable.status == 'active', 1), else_=0)).label('active_alarms'),
                func.sum(case((AlarmTable.severity == 'critical', 1), else_=0)).label('critical_alarms')
            ).where(AlarmTable.system_id == system_id)
        )
        alarm_result = alarm_stats.first()
        
        # 统计接入点数量
        from src.models.alarm import Endpoint
        endpoint_stats = await db.execute(
            select(
                func.count(Endpoint.id).label('total_endpoints'),
                func.sum(case((Endpoint.enabled == True, 1), else_=0)).label('active_endpoints')
            ).where(Endpoint.system_id == system_id)
        )
        endpoint_result = endpoint_stats.first()
        
        # 统计用户数量
        user_stats = await db.execute(
            select(func.count(user_system_association.c.user_id)).where(
                user_system_association.c.system_id == system_id
            )
        )
        user_count = user_stats.scalar()
        
        return {
            "system_id": system_id,
            "system_name": system.name,
            "total_alarms": alarm_result.total_alarms or 0,
            "active_alarms": alarm_result.active_alarms or 0,
            "critical_alarms": alarm_result.critical_alarms or 0,
            "total_endpoints": endpoint_result.total_endpoints or 0,
            "active_endpoints": endpoint_result.active_endpoints or 0,
            "user_count": user_count or 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取系统统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取系统统计失败")