"""
告警抑制服务
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from sqlalchemy import and_, or_, select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import json
import re

try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False
    croniter = None

from src.core.database import get_db_session
from src.models.suppression import (
    AlarmSuppression, SuppressionLog, MaintenanceWindow, DependencyMap,
    SuppressionType, SuppressionStatus, SUPPRESSION_TEMPLATES,
    AlarmSuppressionCreate, AlarmSuppressionUpdate, AlarmSuppressionResponse
)
from src.models.alarm import AlarmTable, User
from src.models.noise_reduction import NoiseReductionRule
# 可选导入通知服务
try:
    from src.services.notification_service import notification_service
    NOTIFICATION_SERVICE_AVAILABLE = True
except ImportError:
    notification_service = None
    NOTIFICATION_SERVICE_AVAILABLE = False


class SuppressionService:
    """告警抑制服务"""
    
    def __init__(self):
        self.active_suppressions = {}
        self.maintenance_windows = {}
        self.dependency_cache = {}
        
    async def create_suppression(
        self,
        db: AsyncSession,
        suppression_data: AlarmSuppressionCreate,
        creator_id: int
    ) -> AlarmSuppression:
        """创建告警抑制规则"""
        
        # 验证抑制条件 (Pydantic already handles this)
        # await self._validate_suppression_conditions(suppression_data.conditions)
        
        # 创建抑制规则
        suppression = AlarmSuppression(
            name=suppression_data.name,
            description=suppression_data.description,
            suppression_type=suppression_data.suppression_type,
            conditions=suppression_data.conditions.model_dump(),
            start_time=suppression_data.start_time,
            end_time=suppression_data.end_time,
            is_recurring=suppression_data.is_recurring,
            recurrence_pattern=suppression_data.recurrence_pattern,
            priority=suppression_data.priority,
            action_config=suppression_data.action_config.model_dump() if suppression_data.action_config else None,
            created_by=creator_id
        )
        
        db.add(suppression)
        await db.commit()
        await db.refresh(suppression)
        
        # 如果是立即生效的抑制，加载到缓存
        if suppression.start_time <= datetime.utcnow():
            await self._load_suppression_to_cache(suppression)
            
        return suppression
    
    async def update_suppression(
        self,
        db: AsyncSession,
        suppression_id: int,
        update_data: Dict[str, Any]
    ) -> Optional[AlarmSuppression]:
        """更新告警抑制规则"""
        
        suppression = await db.get(AlarmSuppression, suppression_id)
        if not suppression:
            return None
            
        # 更新字段
        for field, value in update_data.items():
            if hasattr(suppression, field):
                setattr(suppression, field, value)
                
        suppression.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(suppression)
        
        # 更新缓存
        await self._update_suppression_cache(suppression)
        
        return suppression
    
    async def delete_suppression(self, db: AsyncSession, suppression_id: int) -> bool:
        """删除告警抑制规则"""
        
        suppression = await db.get(AlarmSuppression, suppression_id)
        if not suppression:
            return False
            
        # 从缓存中移除
        self.active_suppressions.pop(suppression_id, None)
        
        # 删除数据库记录
        await db.delete(suppression)
        await db.commit()
        
        return True
    
    async def get_suppression(
        self,
        db: AsyncSession,
        suppression_id: int
    ) -> Optional[AlarmSuppression]:
        """获取抑制规则详情"""
        
        stmt = select(AlarmSuppression).where(
            AlarmSuppression.id == suppression_id
        ).options(
            selectinload(AlarmSuppression.creator),
            selectinload(AlarmSuppression.suppression_logs)
        )
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_suppressions(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        suppression_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AlarmSuppression]:
        """获取抑制规则列表"""
        
        stmt = select(AlarmSuppression)
        
        if status:
            stmt = stmt.where(AlarmSuppression.status == status)
        if suppression_type:
            stmt = stmt.where(AlarmSuppression.suppression_type == suppression_type)
            
        stmt = stmt.limit(limit).offset(offset).order_by(
            AlarmSuppression.priority.asc(),
            AlarmSuppression.created_at.desc()
        )
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def check_alarm_suppression(
        self,
        alarm_data: Dict[str, Any],
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """检查告警是否应被抑制"""
        
        if current_time is None:
            current_time = datetime.utcnow()
            
        suppression_result = {
            'should_suppress': False,
            'suppression_rules': [],
            'suppression_reason': None,
            'action_taken': None
        }
        
        # 按优先级检查所有活跃的抑制规则
        for rule_id, rule_config in sorted(
            self.active_suppressions.items(),
            key=lambda x: x[1].get('priority', 100)
        ):
            if await self._check_rule_match(alarm_data, rule_config, current_time):
                suppression_result['should_suppress'] = True
                suppression_result['suppression_rules'].append(rule_id)
                suppression_result['suppression_reason'] = rule_config.get('name', 'Unknown')
                suppression_result['action_taken'] = rule_config.get('action_config', {}).get('action', 'suppress')
                
                # 如果是高优先级规则，直接返回
                if rule_config.get('priority', 100) <= 10:
                    break
                    
        return suppression_result
    
    async def apply_suppression(
        self,
        db: AsyncSession,
        alarm_id: int,
        suppression_result: Dict[str, Any]
    ) -> bool:
        """应用抑制规则"""
        
        if not suppression_result['should_suppress']:
            return False
            
        # 记录抑制日志
        for rule_id in suppression_result['suppression_rules']:
            suppression_log = SuppressionLog(
                suppression_id=rule_id,
                alarm_id=alarm_id,
                action=suppression_result['action_taken'],
                reason=suppression_result['suppression_reason'],
                match_details=suppression_result,
                suppressed_at=datetime.utcnow()
            )
            db.add(suppression_log)
            
            # 更新抑制规则统计
            await self._update_suppression_stats(db, rule_id)
        
        await db.commit()
        return True
    
    async def create_maintenance_window(
        self,
        db: AsyncSession,
        window_data: Dict[str, Any],
        creator_id: int
    ) -> MaintenanceWindow:
        """创建维护窗口"""
        
        window = MaintenanceWindow(
            name=window_data['name'],
            description=window_data.get('description'),
            start_time=window_data['start_time'],
            end_time=window_data['end_time'],
            is_recurring=window_data.get('is_recurring', False),
            recurrence_pattern=window_data.get('recurrence_pattern'),
            affected_systems=window_data.get('affected_systems', []),
            affected_services=window_data.get('affected_services', []),
            affected_hosts=window_data.get('affected_hosts', []),
            suppress_all=window_data.get('suppress_all', False),
            severity_filter=window_data.get('severity_filter'),
            notify_before_minutes=window_data.get('notify_before_minutes', 30),
            notification_config=window_data.get('notification_config', {}),
            created_by=creator_id
        )
        
        db.add(window)
        await db.commit()
        await db.refresh(window)
        
        # 自动创建对应的抑制规则
        await self._create_maintenance_suppression(db, window)
        
        # 安排维护通知
        await self._schedule_maintenance_notifications(window)
        
        return window
    
    async def get_maintenance_windows(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        upcoming_hours: Optional[int] = None
    ) -> List[MaintenanceWindow]:
        """获取维护窗口列表"""
        
        stmt = select(MaintenanceWindow)
        
        if status:
            stmt = stmt.where(MaintenanceWindow.status == status)
            
        if upcoming_hours:
            future_time = datetime.utcnow() + timedelta(hours=upcoming_hours)
            stmt = stmt.where(
                and_(
                    MaintenanceWindow.start_time <= future_time,
                    MaintenanceWindow.end_time >= datetime.utcnow()
                )
            )
            
        stmt = stmt.order_by(MaintenanceWindow.start_time.asc())
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def create_dependency_map(
        self,
        db: AsyncSession,
        dependency_data: Dict[str, Any],
        creator_id: int
    ) -> DependencyMap:
        """创建依赖关系映射"""
        
        dependency = DependencyMap(
            name=dependency_data['name'],
            description=dependency_data.get('description'),
            parent_type=dependency_data['parent_type'],
            parent_identifier=dependency_data['parent_identifier'],
            child_type=dependency_data['child_type'],
            child_identifier=dependency_data['child_identifier'],
            dependency_config=dependency_data.get('dependency_config', {}),
            cascade_timeout_minutes=dependency_data.get('cascade_timeout_minutes', 5),
            weight=dependency_data.get('weight', 1.0),
            priority=dependency_data.get('priority', 100),
            created_by=creator_id
        )
        
        db.add(dependency)
        await db.commit()
        await db.refresh(dependency)
        
        # 更新依赖缓存
        await self._update_dependency_cache()
        
        return dependency
    
    async def test_suppression_rule(
        self,
        suppression_config: Dict[str, Any],
        test_alarms: List[Dict[str, Any]],
        test_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """测试抑制规则"""
        
        if test_time is None:
            test_time = datetime.utcnow()
            
        results = {
            'total_alarms': len(test_alarms),
            'suppressed_alarms': 0,
            'suppression_rate': 0.0,
            'test_results': []
        }
        
        for alarm in test_alarms:
            is_suppressed = await self._check_rule_match(alarm, suppression_config, test_time)
            
            result = {
                'alarm_id': alarm.get('id', 'unknown'),
                'alarm_summary': alarm.get('summary', ''),
                'suppressed': is_suppressed,
                'match_details': {}
            }
            
            if is_suppressed:
                results['suppressed_alarms'] += 1
                result['match_details'] = await self._get_match_details(alarm, suppression_config)
                
            results['test_results'].append(result)
        
        results['suppression_rate'] = (
            results['suppressed_alarms'] / results['total_alarms'] * 100
            if results['total_alarms'] > 0 else 0
        )
        
        return results
    
    async def load_active_suppressions(self, db: AsyncSession):
        """加载活跃的抑制规则到缓存"""
        
        current_time = datetime.utcnow()
        
        # 查询当前活跃的抑制规则
        stmt = select(AlarmSuppression).where(
            and_(
                AlarmSuppression.status == SuppressionStatus.ACTIVE,
                AlarmSuppression.start_time <= current_time,
                or_(
                    AlarmSuppression.end_time.is_(None),
                    AlarmSuppression.end_time >= current_time
                )
            )
        )
        
        result = await db.execute(stmt)
        suppressions = result.scalars().all()
        
        # 加载到缓存
        for suppression in suppressions:
            await self._load_suppression_to_cache(suppression)
    
    
    
    async def _load_suppression_to_cache(self, suppression: AlarmSuppression):
        """加载抑制规则到缓存"""
        
        self.active_suppressions[suppression.id] = {
            'id': suppression.id,
            'name': suppression.name,
            'type': suppression.suppression_type,
            'conditions': suppression.conditions,
            'start_time': suppression.start_time,
            'end_time': suppression.end_time,
            'is_recurring': suppression.is_recurring,
            'recurrence_pattern': suppression.recurrence_pattern,
            'priority': suppression.priority,
            'action_config': suppression.action_config
        }
    
    async def _update_suppression_cache(self, suppression: AlarmSuppression):
        """更新缓存中的抑制规则"""
        
        if suppression.status == SuppressionStatus.ACTIVE:
            await self._load_suppression_to_cache(suppression)
        else:
            self.active_suppressions.pop(suppression.id, None)
    
    async def _check_rule_match(
        self,
        alarm_data: Dict[str, Any],
        rule_config: Dict[str, Any],
        current_time: datetime
    ) -> bool:
        """检查规则是否匹配告警"""
        
        conditions = rule_config.get('conditions', {})
        
        # 检查时间范围
        if not await self._check_time_range(rule_config, current_time):
            return False
        
        # 检查基本条件匹配
        match_type = conditions.get('match_type', 'exact')
        
        if match_type == 'exact':
            return await self._check_exact_match(alarm_data, conditions)
        elif match_type == 'regex':
            return await self._check_regex_match(alarm_data, conditions)
        elif match_type == 'wildcard':
            return await self._check_wildcard_match(alarm_data, conditions)
        elif match_type == 'tag_based':
            return await self._check_tag_match(alarm_data, conditions)
        
        return False
    
    async def _check_time_range(self, rule_config: Dict[str, Any], current_time: datetime) -> bool:
        """检查时间范围"""
        
        start_time = rule_config.get('start_time')
        end_time = rule_config.get('end_time')
        
        if start_time and current_time < start_time:
            return False
        if end_time and current_time > end_time:
            return False
            
        # 检查周期性规则
        if rule_config.get('is_recurring') and rule_config.get('recurrence_pattern'):
            return await self._check_recurrence_pattern(
                rule_config['recurrence_pattern'],
                current_time
            )
            
        return True
    
    async def _check_exact_match(self, alarm_data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """检查精确匹配"""
        
        for field, expected_value in conditions.items():
            if field in ['match_type']:
                continue
                
            alarm_value = alarm_data.get(field)
            
            if isinstance(expected_value, list):
                if alarm_value not in expected_value:
                    return False
            elif alarm_value != expected_value:
                return False
                
        return True
    
    async def _check_regex_match(self, alarm_data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """检查正则表达式匹配"""
        
        for field, pattern in conditions.items():
            if field in ['match_type']:
                continue
                
            alarm_value = str(alarm_data.get(field, ''))
            
            try:
                if not re.search(pattern, alarm_value):
                    return False
            except re.error:
                return False
                
        return True
    
    async def _check_wildcard_match(self, alarm_data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """检查通配符匹配"""
        
        for field, pattern in conditions.items():
            if field in ['match_type']:
                continue
                
            alarm_value = str(alarm_data.get(field, ''))
            
            # 将通配符转换为正则表达式
            regex_pattern = pattern.replace('*', '.*').replace('?', '.')
            
            try:
                if not re.search(f"^{regex_pattern}$", alarm_value):
                    return False
            except re.error:
                return False
                
        return True
    
    async def _check_tag_match(self, alarm_data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """检查标签匹配"""
        
        alarm_tags = alarm_data.get('tags', {})
        required_tags = conditions.get('tags', {})
        
        for tag_key, tag_value in required_tags.items():
            if tag_key not in alarm_tags:
                return False
                
            if isinstance(tag_value, list):
                if alarm_tags[tag_key] not in tag_value:
                    return False
            elif alarm_tags[tag_key] != tag_value:
                return False
                
        return True
    
    async def _check_recurrence_pattern(self, pattern: Dict[str, Any], current_time: datetime) -> bool:
        """检查周期性模式"""
        
        pattern_type = pattern.get('type', 'cron')
        
        if pattern_type == 'cron':
            cron_expr = pattern.get('expression')
            if cron_expr and CRONITER_AVAILABLE:
                try:
                    cron = croniter(cron_expr, current_time)
                    # 检查当前时间是否在cron表达式范围内
                    return abs((cron.get_next(datetime) - current_time).total_seconds()) < 60
                except:
                    return False
            elif not CRONITER_AVAILABLE:
                # 如果croniter不可用，跳过cron模式检查
                return False
                    
        elif pattern_type == 'daily':
            time_ranges = pattern.get('time_ranges', [])
            if not time_ranges:
                return False
            
            current_time_only = current_time.time()
            
            for time_range in time_ranges:
                try:
                    start_time_str = time_range['start']
                    end_time_str = time_range['end']
                    
                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                    end_time = datetime.strptime(end_time_str, '%H:%M').time()
                    
                    if start_time <= end_time:
                        if start_time <= current_time_only <= end_time:
                            return True
                    else: # Overnight range, e.g., 22:00 - 06:00
                        if current_time_only >= start_time or current_time_only <= end_time:
                            return True
                except (KeyError, ValueError):
                    self.logger.warning(f"Invalid daily time range format: {time_range}")
                    continue
            return False
                    
        elif pattern_type == 'weekly':
            weekdays = pattern.get('weekdays', []) # 0=Monday, 6=Sunday
            if not weekdays:
                return False
            
            current_weekday = current_time.weekday() # 0=Monday, 6=Sunday
            
            if current_weekday not in weekdays:
                return False
            
            time_ranges = pattern.get('time_ranges', [])
            if not time_ranges: # If no time ranges specified, just check weekday
                return True
            
            current_time_only = current_time.time()
            
            for time_range in time_ranges:
                try:
                    start_time_str = time_range['start']
                    end_time_str = time_range['end']
                    
                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                    end_time = datetime.strptime(end_time_str, '%H:%M').time()
                    
                    if start_time <= end_time:
                        if start_time <= current_time_only <= end_time:
                            return True
                    else: # Overnight range
                        if current_time_only >= start_time or current_time_only <= end_time:
                            return True
                except (KeyError, ValueError):
                    self.logger.warning(f"Invalid weekly time range format: {time_range}")
                    continue
            return False
        
        elif pattern_type == 'monthly':
            days_of_month = pattern.get('days_of_month', []) # 1-31
            if not days_of_month:
                return False
            
            current_day = current_time.day
            if current_day not in days_of_month:
                return False
            
            time_ranges = pattern.get('time_ranges', [])
            if not time_ranges:
                return True
            
            current_time_only = current_time.time()
            
            for time_range in time_ranges:
                try:
                    start_time_str = time_range['start']
                    end_time_str = time_range['end']
                    
                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                    end_time = datetime.strptime(end_time_str, '%H:%M').time()
                    
                    if start_time <= end_time:
                        if start_time <= current_time_only <= end_time:
                            return True
                    else: # Overnight range
                        if current_time_only >= start_time or current_time_only <= end_time:
                            return True
                except (KeyError, ValueError):
                    self.logger.warning(f"Invalid monthly time range format: {time_range}")
                    continue
            return False
        
        elif pattern_type == 'yearly':
            months = pattern.get('months', []) # 1-12
            days_of_month = pattern.get('days_of_month', []) # 1-31
            
            if not months or not days_of_month:
                return False
            
            current_month = current_time.month
            current_day = current_time.day
            
            if current_month not in months or current_day not in days_of_month:
                return False
            
            time_ranges = pattern.get('time_ranges', [])
            if not time_ranges:
                return True
            
            current_time_only = current_time.time()
            
            for time_range in time_ranges:
                try:
                    start_time_str = time_range['start']
                    end_time_str = time_range['end']
                    
                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                    end_time = datetime.strptime(end_time_str, '%H:%M').time()
                    
                    if start_time <= end_time:
                        if start_time <= current_time_only <= end_time:
                            return True
                    else: # Overnight range
                        if current_time_only >= start_time or current_time_only <= end_time:
                            return True
                except (KeyError, ValueError):
                    self.logger.warning(f"Invalid yearly time range format: {time_range}")
                    continue
            return False
        
        return False
    
    async def _update_suppression_stats(self, db: AsyncSession, rule_id: int):
        """更新抑制规则统计"""
        
        await db.execute(
            update(AlarmSuppression)
            .where(AlarmSuppression.id == rule_id)
            .values(
                suppressed_count=AlarmSuppression.suppressed_count + 1,
                last_match=datetime.utcnow()
            )
        )
    
    async def _create_maintenance_suppression(self, db: AsyncSession, window: MaintenanceWindow):
        """为维护窗口创建抑制规则"""
        
        conditions = {
            'match_type': 'tag_based',
            'maintenance_window_id': window.id
        }
        
        # 添加影响范围条件
        if window.affected_systems:
            conditions['systems'] = window.affected_systems
        if window.affected_services:
            conditions['services'] = window.affected_services
        if window.affected_hosts:
            conditions['hosts'] = window.affected_hosts
            
        # 添加严重程度过滤
        if window.severity_filter:
            conditions['severity'] = window.severity_filter
        
        suppression_data = {
            'name': f"Maintenance: {window.name}",
            'description': f"Auto-generated suppression for maintenance window: {window.description}",
            'suppression_type': SuppressionType.MAINTENANCE,
            'conditions': conditions,
            'start_time': window.start_time,
            'end_time': window.end_time,
            'is_recurring': window.is_recurring,
            'recurrence_pattern': window.recurrence_pattern,
            'priority': 1,  # 维护窗口优先级最高
            'action_config': {
                'action': 'suppress',
                'notify_suppressed': not window.suppress_all,
                'maintenance_mode': True
            }
        }
        
        await self.create_suppression(db, suppression_data, window.created_by)
    
    async def _schedule_maintenance_notifications(self, window: MaintenanceWindow):
        """安排维护通知"""
        
        if window.notify_before_minutes > 0:
            notify_time = window.start_time - timedelta(minutes=window.notify_before_minutes)
            
            # 这里可以集成到任务调度系统
            notification_data = {
                'type': 'maintenance_notification',
                'window_id': window.id,
                'message': f"Maintenance window '{window.name}' will start in {window.notify_before_minutes} minutes",
                'scheduled_time': notify_time
            }
            
            # 发送通知 (这里简化处理)
            if NOTIFICATION_SERVICE_AVAILABLE:
                await notification_service.send_maintenance_notification(notification_data)
    
    async def _update_dependency_cache(self):
        """更新依赖关系缓存"""
        
        # 这里可以实现依赖关系的缓存更新逻辑
        # 用于优化依赖检查的性能
        pass
    
    async def _get_match_details(self, alarm_data: Dict[str, Any], rule_config: Dict[str, Any]) -> Dict[str, Any]:
        """获取匹配详情"""
        
        return {
            'rule_id': rule_config.get('id'),
            'rule_name': rule_config.get('name'),
            'match_type': rule_config.get('conditions', {}).get('match_type'),
            'matched_fields': list(rule_config.get('conditions', {}).keys()),
            'alarm_fields': {k: v for k, v in alarm_data.items() if k in rule_config.get('conditions', {})},
            'match_time': datetime.utcnow().isoformat()
        }
    
    def get_suppression_templates(self) -> Dict[str, Any]:
        """获取抑制规则模板"""
        return SUPPRESSION_TEMPLATES


# 全局实例
suppression_service = SuppressionService()