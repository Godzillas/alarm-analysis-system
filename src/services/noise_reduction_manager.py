"""
降噪规则管理服务
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, delete, update
from sqlalchemy.orm import selectinload

from src.core.database import async_session_maker
from src.core.logging import get_logger
from src.core.exceptions import DatabaseException, ValidationException, ResourceNotFoundException
from src.models.noise_reduction import (
    NoiseReductionRule, NoiseRuleExecutionLog, NoiseReductionStats,
    NoiseReductionRuleCreate, NoiseReductionRuleUpdate,
    NoiseRuleTestRequest, NoiseRuleTestResult,
    RULE_TEMPLATES
)
from src.services.noise_reduction_service import noise_reduction_engine

logger = get_logger(__name__)


class NoiseReductionManager:
    """降噪规则管理器"""
    
    def __init__(self):
        self.logger = logger
        self.engine = noise_reduction_engine
    
    # 规则管理
    
    async def create_rule(
        self,
        rule_data: NoiseReductionRuleCreate,
        creator_id: int
    ) -> NoiseReductionRule:
        """创建降噪规则"""
        async with async_session_maker() as session:
            try:
                # 检查规则名称是否重复
                existing = await session.execute(
                    select(NoiseReductionRule).where(
                        NoiseReductionRule.name == rule_data.name
                    )
                )
                if existing.scalar_one_or_none():
                    raise ValidationException(
                        "Rule with this name already exists",
                        field="name"
                    )
                
                # 验证规则配置
                self._validate_rule_config(rule_data)
                
                rule = NoiseReductionRule(
                    name=rule_data.name,
                    description=rule_data.description,
                    rule_type=rule_data.rule_type,
                    action=rule_data.action,
                    conditions=rule_data.conditions,
                    parameters=rule_data.parameters,
                    priority=rule_data.priority,
                    effective_start=rule_data.effective_start,
                    effective_end=rule_data.effective_end,
                    created_by=creator_id
                )
                
                session.add(rule)
                await session.commit()
                await session.refresh(rule)
                
                # 清除缓存
                self.engine.clear_cache()
                
                self.logger.info(
                    f"Created noise reduction rule: {rule.name}",
                    extra={"rule_id": rule.id, "creator_id": creator_id}
                )
                
                return rule
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, ValidationException):
                    raise
                raise DatabaseException(f"Failed to create rule: {str(e)}")
    
    async def get_rules(
        self,
        enabled_only: bool = False,
        rule_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[NoiseReductionRule]:
        """获取降噪规则列表"""
        async with async_session_maker() as session:
            try:
                query = select(NoiseReductionRule).options(
                    selectinload(NoiseReductionRule.creator)
                )
                
                conditions = []
                if enabled_only:
                    conditions.append(NoiseReductionRule.enabled == True)
                if rule_type:
                    conditions.append(NoiseReductionRule.rule_type == rule_type)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                query = query.order_by(
                    NoiseReductionRule.priority,
                    NoiseReductionRule.created_at.desc()
                )
                query = query.limit(limit).offset(offset)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                raise DatabaseException(f"Failed to get rules: {str(e)}")
    
    async def get_rule(self, rule_id: int) -> NoiseReductionRule:
        """获取单个规则详情"""
        async with async_session_maker() as session:
            try:
                rule = await session.get(NoiseReductionRule, rule_id)
                if not rule:
                    raise ResourceNotFoundException("NoiseReductionRule", rule_id)
                return rule
            except ResourceNotFoundException:
                raise
            except Exception as e:
                raise DatabaseException(f"Failed to get rule: {str(e)}")
    
    async def update_rule(
        self,
        rule_id: int,
        rule_data: NoiseReductionRuleUpdate,
        updater_id: int
    ) -> NoiseReductionRule:
        """更新降噪规则"""
        async with async_session_maker() as session:
            try:
                rule = await session.get(NoiseReductionRule, rule_id)
                if not rule:
                    raise ResourceNotFoundException("NoiseReductionRule", rule_id)
                
                # 更新字段
                update_data = rule_data.dict(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(rule, field, value)
                
                rule.updated_at = datetime.utcnow()
                
                # 验证更新后的配置
                if "conditions" in update_data or "rule_type" in update_data:
                    self._validate_rule_config(rule)
                
                await session.commit()
                
                # 清除缓存
                self.engine.clear_cache()
                
                self.logger.info(
                    f"Updated noise reduction rule: {rule.name}",
                    extra={"rule_id": rule_id, "updater_id": updater_id}
                )
                
                return rule
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, (ValidationException, ResourceNotFoundException)):
                    raise
                raise DatabaseException(f"Failed to update rule: {str(e)}")
    
    async def delete_rule(self, rule_id: int, deleter_id: int) -> bool:
        """删除降噪规则"""
        async with async_session_maker() as session:
            try:
                rule = await session.get(NoiseReductionRule, rule_id)
                if not rule:
                    raise ResourceNotFoundException("NoiseReductionRule", rule_id)
                
                # 删除相关的执行日志
                await session.execute(
                    delete(NoiseRuleExecutionLog).where(
                        NoiseRuleExecutionLog.rule_id == rule_id
                    )
                )
                
                # 删除规则
                await session.delete(rule)
                await session.commit()
                
                # 清除缓存
                self.engine.clear_cache()
                
                self.logger.info(
                    f"Deleted noise reduction rule: {rule.name}",
                    extra={"rule_id": rule_id, "deleter_id": deleter_id}
                )
                
                return True
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, ResourceNotFoundException):
                    raise
                raise DatabaseException(f"Failed to delete rule: {str(e)}")
    
    async def toggle_rule(self, rule_id: int, enabled: bool, updater_id: int) -> NoiseReductionRule:
        """启用/禁用规则"""
        async with async_session_maker() as session:
            try:
                rule = await session.get(NoiseReductionRule, rule_id)
                if not rule:
                    raise ResourceNotFoundException("NoiseReductionRule", rule_id)
                
                rule.enabled = enabled
                rule.updated_at = datetime.utcnow()
                
                await session.commit()
                
                # 清除缓存
                self.engine.clear_cache()
                
                action = "enabled" if enabled else "disabled"
                self.logger.info(
                    f"Rule {action}: {rule.name}",
                    extra={"rule_id": rule_id, "updater_id": updater_id}
                )
                
                return rule
                
            except Exception as e:
                await session.rollback()
                if isinstance(e, ResourceNotFoundException):
                    raise
                raise DatabaseException(f"Failed to toggle rule: {str(e)}")
    
    # 规则测试
    
    async def test_rule(self, test_request: NoiseRuleTestRequest) -> NoiseRuleTestResult:
        """测试降噪规则"""
        try:
            start_time = datetime.utcnow()
            
            # 创建临时规则对象
            temp_rule = NoiseReductionRule(
                id=-1,  # 临时ID
                name=test_request.rule_config.name,
                rule_type=test_request.rule_config.rule_type,
                action=test_request.rule_config.action,
                conditions=test_request.rule_config.conditions,
                parameters=test_request.rule_config.parameters,
                priority=test_request.rule_config.priority,
                enabled=True,
                effective_start=test_request.rule_config.effective_start,
                effective_end=test_request.rule_config.effective_end
            )
            
            # 测试每个告警
            results = []
            matched_count = 0
            
            for alarm_data in test_request.test_alarms:
                matched, match_details = await self.engine._check_rule_match(temp_rule, alarm_data)
                
                if matched:
                    matched_count += 1
                    action_result = await self.engine._execute_rule_action(temp_rule, alarm_data)
                else:
                    action_result = {"action": "no_match"}
                
                results.append({
                    "alarm": alarm_data,
                    "matched": matched,
                    "match_details": match_details,
                    "action_result": action_result
                })
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            match_rate = matched_count / len(test_request.test_alarms) if test_request.test_alarms else 0
            
            return NoiseRuleTestResult(
                total_alarms=len(test_request.test_alarms),
                matched_alarms=matched_count,
                match_rate=match_rate,
                execution_time_ms=execution_time,
                results=results
            )
            
        except Exception as e:
            self.logger.error(f"Error testing rule: {str(e)}")
            raise DatabaseException(f"Rule test failed: {str(e)}")
    
    # 统计和监控
    
    async def get_rule_stats(
        self,
        rule_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取规则执行统计"""
        async with async_session_maker() as session:
            try:
                # 构建查询条件
                conditions = []
                if rule_id:
                    conditions.append(NoiseRuleExecutionLog.rule_id == rule_id)
                if start_date:
                    conditions.append(NoiseRuleExecutionLog.executed_at >= start_date)
                if end_date:
                    conditions.append(NoiseRuleExecutionLog.executed_at <= end_date)
                
                base_filter = and_(*conditions) if conditions else True
                
                # 基础统计
                basic_stats = await session.execute(
                    select(
                        func.count(NoiseRuleExecutionLog.id).label('total_executions'),
                        func.sum(func.cast(NoiseRuleExecutionLog.matched, int)).label('total_matches'),
                        func.avg(NoiseRuleExecutionLog.execution_time_ms).label('avg_execution_time')
                    ).where(base_filter)
                )
                basic_result = basic_stats.first()
                
                # 按动作分组统计
                action_stats = await session.execute(
                    select(
                        NoiseRuleExecutionLog.action_taken,
                        func.count(NoiseRuleExecutionLog.id).label('count')
                    )
                    .where(and_(base_filter, NoiseRuleExecutionLog.matched == True))
                    .group_by(NoiseRuleExecutionLog.action_taken)
                )
                
                # 按时间分组统计（最近7天）
                seven_days_ago = datetime.utcnow() - timedelta(days=7)
                time_stats = await session.execute(
                    select(
                        func.date(NoiseRuleExecutionLog.executed_at).label('date'),
                        func.count(NoiseRuleExecutionLog.id).label('executions'),
                        func.sum(func.cast(NoiseRuleExecutionLog.matched, int)).label('matches')
                    )
                    .where(and_(base_filter, NoiseRuleExecutionLog.executed_at >= seven_days_ago))
                    .group_by(func.date(NoiseRuleExecutionLog.executed_at))
                    .order_by(func.date(NoiseRuleExecutionLog.executed_at))
                )
                
                return {
                    "basic_stats": {
                        "total_executions": basic_result.total_executions or 0,
                        "total_matches": basic_result.total_matches or 0,
                        "match_rate": (basic_result.total_matches or 0) / (basic_result.total_executions or 1),
                        "avg_execution_time_ms": basic_result.avg_execution_time or 0
                    },
                    "action_distribution": {
                        row.action_taken: row.count for row in action_stats
                    },
                    "daily_stats": [
                        {
                            "date": row.date,
                            "executions": row.executions,
                            "matches": row.matches,
                            "match_rate": row.matches / row.executions if row.executions > 0 else 0
                        }
                        for row in time_stats
                    ]
                }
                
            except Exception as e:
                raise DatabaseException(f"Failed to get rule stats: {str(e)}")
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """获取系统级降噪统计"""
        async with async_session_maker() as session:
            try:
                # 规则统计
                rule_stats = await session.execute(
                    select(
                        func.count(NoiseReductionRule.id).label('total_rules'),
                        func.sum(func.cast(NoiseReductionRule.enabled, int)).label('active_rules'),
                        func.avg(NoiseReductionRule.hit_count).label('avg_hit_count')
                    )
                )
                rule_result = rule_stats.first()
                
                # 最近24小时执行统计
                last_24h = datetime.utcnow() - timedelta(hours=24)
                execution_stats = await session.execute(
                    select(
                        func.count(NoiseRuleExecutionLog.id).label('executions_24h'),
                        func.sum(func.cast(NoiseRuleExecutionLog.matched, int)).label('matches_24h'),
                        func.avg(NoiseRuleExecutionLog.execution_time_ms).label('avg_execution_time')
                    ).where(NoiseRuleExecutionLog.executed_at >= last_24h)
                )
                exec_result = execution_stats.first()
                
                # 获取引擎统计
                engine_stats = self.engine.get_stats()
                
                # 最活跃的规则
                top_rules = await session.execute(
                    select(NoiseReductionRule.id, NoiseReductionRule.name, NoiseReductionRule.hit_count)
                    .where(NoiseReductionRule.enabled == True)
                    .order_by(NoiseReductionRule.hit_count.desc())
                    .limit(5)
                )
                
                return {
                    "rule_summary": {
                        "total_rules": rule_result.total_rules or 0,
                        "active_rules": rule_result.active_rules or 0,
                        "avg_hit_count": rule_result.avg_hit_count or 0
                    },
                    "performance": {
                        "executions_24h": exec_result.executions_24h or 0,
                        "matches_24h": exec_result.matches_24h or 0,
                        "match_rate_24h": (exec_result.matches_24h or 0) / (exec_result.executions_24h or 1),
                        "avg_execution_time_ms": exec_result.avg_execution_time or 0
                    },
                    "engine_stats": engine_stats,
                    "top_rules": [
                        {
                            "id": row.id,
                            "name": row.name,
                            "hit_count": row.hit_count
                        }
                        for row in top_rules
                    ]
                }
                
            except Exception as e:
                raise DatabaseException(f"Failed to get system stats: {str(e)}")
    
    # 工具方法
    
    def _validate_rule_config(self, rule_data: Union[NoiseReductionRuleCreate, NoiseReductionRuleUpdate, NoiseReductionRule]) -> None:
        """验证规则配置"""
        rule_type = rule_data.rule_type
        conditions_data = rule_data.conditions
        parameters_data = rule_data.parameters

        if not conditions_data:
            raise ValidationException("Rule conditions cannot be empty")

        try:
            if rule_type == NoiseRuleType.FREQUENCY_LIMIT:
                FrequencyLimitConditions(**conditions_data)
                if parameters_data:
                    FrequencyLimitParameters(**parameters_data)
            elif rule_type == NoiseRuleType.THRESHOLD_FILTER:
                ThresholdFilterConditions(**conditions_data)
                if parameters_data:
                    ThresholdFilterParameters(**parameters_data)
            elif rule_type == NoiseRuleType.SILENCE_WINDOW:
                SilenceWindowConditions(**conditions_data)
                if parameters_data:
                    SilenceWindowParameters(**parameters_data)
            elif rule_type == NoiseRuleType.DEPENDENCY_FILTER:
                DependencyFilterConditions(**conditions_data)
                if parameters_data:
                    DependencyFilterParameters(**parameters_data)
            elif rule_type == NoiseRuleType.DUPLICATE_SUPPRESS:
                DuplicateSuppressConditions(**conditions_data)
            elif rule_type == NoiseRuleType.TIME_BASED:
                TimeBasedConditions(**conditions_data)
            elif rule_type == NoiseRuleType.CUSTOM_RULE:
                CustomRuleConditions(**conditions_data)
        except Exception as e:
            raise ValidationException(f"Invalid rule configuration for {rule_type}: {str(e)}")

        # 验证时间有效性
        if (rule_data.effective_start and rule_data.effective_end and 
            rule_data.effective_start >= rule_data.effective_end):
            raise ValidationException("effective_start must be before effective_end")
    
    async def get_rule_templates(self) -> Dict[str, Any]:
        """获取规则模板"""
        return RULE_TEMPLATES
    
    async def create_rule_from_template(
        self,
        template_name: str,
        custom_name: str,
        custom_params: Dict[str, Any],
        creator_id: int
    ) -> NoiseReductionRule:
        """从模板创建规则"""
        if template_name not in RULE_TEMPLATES:
            raise ValidationException(f"Unknown template: {template_name}")
        
        template = RULE_TEMPLATES[template_name].copy()
        
        # 应用自定义参数
        if custom_params:
            template["conditions"].update(custom_params.get("conditions", {}))
            template.setdefault("parameters", {}).update(custom_params.get("parameters", {}))
        
        # 创建规则数据
        rule_data = NoiseReductionRuleCreate(
            name=custom_name,
            description=template["description"],
            rule_type=template_name,
            action="suppress",  # 默认动作
            conditions=template["conditions"],
            parameters=template.get("parameters")
        )
        
        return await self.create_rule(rule_data, creator_id)