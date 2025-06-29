"""
通知管理API
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from src.core.database import get_db_session
from src.api.auth import get_current_user
from src.models.alarm import (
    User, NotificationTemplate, ContactPoint, UserSubscription, NotificationLog,
    NotificationTemplateCreate, NotificationTemplateUpdate, NotificationTemplateResponse,
    ContactPointCreateNew, ContactPointUpdateNew, ContactPointResponseNew,
    UserSubscriptionCreateNew, UserSubscriptionUpdateNew, UserSubscriptionResponseNew,
    NotificationLogResponse
)
from src.services.notification_service import notification_service
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# 通知模板管理
@router.post("/templates", response_model=NotificationTemplateResponse)
async def create_notification_template(
    template_data: NotificationTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """创建通知模板"""
    try:
        template = NotificationTemplate(
            name=template_data.name,
            description=template_data.description,
            template_type=template_data.template_type,
            content_type=template_data.content_type,
            title_template=template_data.title_template,
            content_template=template_data.content_template,
            footer_template=template_data.footer_template,
            variables=template_data.variables,
            style_config=template_data.style_config,
            created_by=current_user.id
        )
        
        db.add(template)
        await db.commit()
        await db.refresh(template)
        
        logger.info(f"创建通知模板: {template.name} (ID: {template.id})")
        return template
        
    except Exception as e:
        await db.rollback()
        logger.error(f"创建通知模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建模板失败: {str(e)}")


@router.get("/templates", response_model=List[NotificationTemplateResponse])
async def list_notification_templates(
    content_type: Optional[str] = Query(None, description="按内容类型过滤"),
    enabled_only: bool = Query(True, description="只返回启用的模板"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """获取通知模板列表"""
    try:
        query = select(NotificationTemplate)
        
        if content_type:
            query = query.where(NotificationTemplate.content_type == content_type)
        
        if enabled_only:
            query = query.where(NotificationTemplate.enabled == True)
        
        query = query.order_by(desc(NotificationTemplate.created_at))
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        templates = result.scalars().all()
        
        return templates
        
    except Exception as e:
        logger.error(f"获取通知模板列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模板列表失败: {str(e)}")


@router.get("/templates/{template_id}", response_model=NotificationTemplateResponse)
async def get_notification_template(
    template_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """获取单个通知模板"""
    template = await db.get(NotificationTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    return template


@router.put("/templates/{template_id}", response_model=NotificationTemplateResponse)
async def update_notification_template(
    template_id: int,
    template_data: NotificationTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """更新通知模板"""
    try:
        template = await db.get(NotificationTemplate, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        # 检查权限（只有创建者或管理员可以修改）
        if template.created_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="没有权限修改此模板")
        
        # 更新字段
        update_data = template_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(template, field, value)
        
        await db.commit()
        await db.refresh(template)
        
        logger.info(f"更新通知模板: {template.name} (ID: {template.id})")
        return template
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新通知模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新模板失败: {str(e)}")


@router.delete("/templates/{template_id}")
async def delete_notification_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """删除通知模板"""
    try:
        template = await db.get(NotificationTemplate, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        # 检查权限
        if template.created_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="没有权限删除此模板")
        
        # 检查是否为系统模板
        if template.is_system_template:
            raise HTTPException(status_code=400, detail="不能删除系统模板")
        
        await db.delete(template)
        await db.commit()
        
        logger.info(f"删除通知模板: {template.name} (ID: {template.id})")
        return {"message": "模板删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除通知模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除模板失败: {str(e)}")


# 联系点管理
@router.post("/contact-points", response_model=ContactPointResponseNew)
async def create_contact_point(
    contact_point_data: ContactPointCreateNew,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """创建联系点"""
    try:
        contact_point = ContactPoint(
            name=contact_point_data.name,
            description=contact_point_data.description,
            contact_type=contact_point_data.contact_type,
            config=contact_point_data.config,
            template_id=contact_point_data.template_id,
            created_by=current_user.id
        )
        
        db.add(contact_point)
        await db.commit()
        await db.refresh(contact_point)
        
        logger.info(f"创建联系点: {contact_point.name} (ID: {contact_point.id})")
        return contact_point
        
    except Exception as e:
        await db.rollback()
        logger.error(f"创建联系点失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建联系点失败: {str(e)}")


@router.get("/contact-points", response_model=List[ContactPointResponseNew])
async def list_contact_points(
    contact_type: Optional[str] = Query(None, description="按类型过滤"),
    enabled_only: bool = Query(True, description="只返回启用的联系点"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """获取联系点列表"""
    try:
        query = select(ContactPoint)
        
        if contact_type:
            query = query.where(ContactPoint.contact_type == contact_type)
        
        if enabled_only:
            query = query.where(ContactPoint.enabled == True)
        
        query = query.order_by(desc(ContactPoint.created_at))
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        contact_points = result.scalars().all()
        
        return contact_points
        
    except Exception as e:
        logger.error(f"获取联系点列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取联系点列表失败: {str(e)}")


@router.get("/contact-points/{contact_point_id}", response_model=ContactPointResponseNew)
async def get_contact_point(
    contact_point_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """获取单个联系点"""
    contact_point = await db.get(ContactPoint, contact_point_id)
    if not contact_point:
        raise HTTPException(status_code=404, detail="联系点不存在")
    
    return contact_point


@router.put("/contact-points/{contact_point_id}", response_model=ContactPointResponseNew)
async def update_contact_point(
    contact_point_id: int,
    contact_point_data: ContactPointUpdateNew,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """更新联系点"""
    try:
        contact_point = await db.get(ContactPoint, contact_point_id)
        if not contact_point:
            raise HTTPException(status_code=404, detail="联系点不存在")
        
        # 检查权限
        if contact_point.created_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="没有权限修改此联系点")
        
        # 更新字段
        update_data = contact_point_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(contact_point, field, value)
        
        await db.commit()
        await db.refresh(contact_point)
        
        logger.info(f"更新联系点: {contact_point.name} (ID: {contact_point.id})")
        return contact_point
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新联系点失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新联系点失败: {str(e)}")


@router.delete("/contact-points/{contact_point_id}")
async def delete_contact_point(
    contact_point_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """删除联系点"""
    try:
        contact_point = await db.get(ContactPoint, contact_point_id)
        if not contact_point:
            raise HTTPException(status_code=404, detail="联系点不存在")
        
        # 检查权限
        if contact_point.created_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="没有权限删除此联系点")
        
        # 检查是否被订阅使用
        subscription_query = select(UserSubscription).where(
            UserSubscription.contact_points.contains([contact_point_id])
        )
        result = await db.execute(subscription_query)
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="联系点正在被订阅使用，无法删除")
        
        await db.delete(contact_point)
        await db.commit()
        
        logger.info(f"删除联系点: {contact_point.name} (ID: {contact_point.id})")
        return {"message": "联系点删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除联系点失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除联系点失败: {str(e)}")


@router.post("/contact-points/{contact_point_id}/test")
async def test_contact_point(
    contact_point_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """测试联系点"""
    try:
        contact_point = await db.get(ContactPoint, contact_point_id)
        if not contact_point:
            raise HTTPException(status_code=404, detail="联系点不存在")
        
        # 执行测试
        result = await notification_service.test_contact_point(contact_point_id)
        
        logger.info(f"测试联系点: {contact_point.name} (ID: {contact_point.id}), 结果: {result['success']}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试联系点失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"测试联系点失败: {str(e)}")


# 订阅管理
@router.post("/subscriptions", response_model=UserSubscriptionResponseNew)
async def create_subscription(
    subscription_data: UserSubscriptionCreateNew,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """创建告警订阅"""
    try:
        # 验证联系点是否存在
        for contact_point_id in subscription_data.contact_points:
            contact_point = await db.get(ContactPoint, contact_point_id)
            if not contact_point:
                raise HTTPException(status_code=400, detail=f"联系点 {contact_point_id} 不存在")
            if not contact_point.enabled:
                raise HTTPException(status_code=400, detail=f"联系点 {contact_point.name} 已禁用")
        
        subscription = UserSubscription(
            user_id=current_user.id,
            name=subscription_data.name,
            description=subscription_data.description,
            subscription_type=subscription_data.subscription_type,
            filters=subscription_data.filters,
            contact_points=subscription_data.contact_points,
            notification_schedule=subscription_data.notification_schedule,
            cooldown_minutes=subscription_data.cooldown_minutes,
            max_notifications_per_hour=subscription_data.max_notifications_per_hour,
            escalation_rules=subscription_data.escalation_rules
        )
        
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
        
        logger.info(f"创建订阅: {subscription.name} (ID: {subscription.id})")
        return subscription
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"创建订阅失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建订阅失败: {str(e)}")


@router.get("/subscriptions", response_model=List[UserSubscriptionResponseNew])
async def list_user_subscriptions(
    enabled_only: bool = Query(True, description="只返回启用的订阅"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """获取当前用户的订阅列表"""
    try:
        query = select(UserSubscription).where(
            UserSubscription.user_id == current_user.id
        )
        
        if enabled_only:
            query = query.where(UserSubscription.enabled == True)
        
        query = query.order_by(desc(UserSubscription.created_at))
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        subscriptions = result.scalars().all()
        
        return subscriptions
        
    except Exception as e:
        logger.error(f"获取订阅列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取订阅列表失败: {str(e)}")


@router.get("/subscriptions/{subscription_id}", response_model=UserSubscriptionResponseNew)
async def get_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """获取单个订阅"""
    subscription = await db.get(UserSubscription, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")
    
    # 检查权限
    if subscription.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="没有权限查看此订阅")
    
    return subscription


@router.put("/subscriptions/{subscription_id}", response_model=UserSubscriptionResponseNew)
async def update_subscription(
    subscription_id: int,
    subscription_data: UserSubscriptionUpdateNew,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """更新订阅"""
    try:
        subscription = await db.get(UserSubscription, subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="订阅不存在")
        
        # 检查权限
        if subscription.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="没有权限修改此订阅")
        
        # 验证联系点（如果有更新）
        if subscription_data.contact_points is not None:
            for contact_point_id in subscription_data.contact_points:
                contact_point = await db.get(ContactPoint, contact_point_id)
                if not contact_point:
                    raise HTTPException(status_code=400, detail=f"联系点 {contact_point_id} 不存在")
        
        # 更新字段
        update_data = subscription_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(subscription, field, value)
        
        await db.commit()
        await db.refresh(subscription)
        
        logger.info(f"更新订阅: {subscription.name} (ID: {subscription.id})")
        return subscription
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新订阅失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新订阅失败: {str(e)}")


@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """删除订阅"""
    try:
        subscription = await db.get(UserSubscription, subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="订阅不存在")
        
        # 检查权限
        if subscription.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="没有权限删除此订阅")
        
        await db.delete(subscription)
        await db.commit()
        
        logger.info(f"删除订阅: {subscription.name} (ID: {subscription.id})")
        return {"message": "订阅删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除订阅失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除订阅失败: {str(e)}")


# 通知日志
@router.get("/logs", response_model=List[NotificationLogResponse])
async def get_notification_logs(
    subscription_id: Optional[int] = Query(None, description="按订阅ID过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    days: int = Query(7, description="查询天数"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """获取通知日志"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 构建查询 - 只能查看自己的通知日志
        if current_user.is_admin:
            # 管理员可以查看所有日志
            query = select(NotificationLog)
        else:
            # 普通用户只能查看自己订阅的通知日志
            query = select(NotificationLog).join(UserSubscription).where(
                UserSubscription.user_id == current_user.id
            )
        
        query = query.where(NotificationLog.created_at >= start_date)
        
        if subscription_id:
            query = query.where(NotificationLog.subscription_id == subscription_id)
        
        if status:
            query = query.where(NotificationLog.status == status)
        
        query = query.order_by(desc(NotificationLog.created_at))
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        logs = result.scalars().all()
        
        return logs
        
    except Exception as e:
        logger.error(f"获取通知日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取通知日志失败: {str(e)}")


@router.post("/test-filters")
async def test_subscription_filters(
    filters: Dict[str, Any] = Body(..., description="过滤条件"),
    alarm_data: Dict[str, Any] = Body(..., description="告警数据样例")
):
    """测试订阅过滤条件"""
    try:
        from src.services.subscription_service import subscription_service
        
        result = await subscription_service.test_subscription_filters(filters, alarm_data)
        
        return {
            "match": result,
            "filters": filters,
            "alarm_data": alarm_data
        }
        
    except Exception as e:
        logger.error(f"测试过滤条件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")