"""
告警规则引擎
"""

import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_maker
from src.models.alarm import (
    RuleGroup, DistributionRule, AlarmDistribution, 
    AlarmTable, User, UserSubscription
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RuleEngine:
    def __init__(self):
        self.active_rules: Dict[int, Dict] = {}
        self.rule_groups: Dict[int, Dict] = {}
        
    async def create_rule_group(self, group_data: Dict[str, Any]) -> Optional[RuleGroup]:
        """创建规则组"""
        try:
            async with async_session_maker() as session:
                group = RuleGroup(**group_data)
                session.add(group)
                await session.commit()
                await session.refresh(group)
                
                if group.enabled:
                    await self._load_rule_group(group)
                    
                logger.info(f"Created rule group: {group.name}")
                return group
                
        except Exception as e:
            logger.error(f"Failed to create rule group: {str(e)}")
            return None
            
    async def create_distribution_rule(self, rule_data: Dict[str, Any]) -> Optional[DistributionRule]:
        """创建分发规则"""
        try:
            async with async_session_maker() as session:
                rule = DistributionRule(**rule_data)
                session.add(rule)
                await session.commit()
                await session.refresh(rule)
                
                if rule.enabled:
                    await self._load_distribution_rule(rule)
                    
                logger.info(f"Created distribution rule: {rule.name}")
                return rule
                
        except Exception as e:
            logger.error(f"Failed to create distribution rule: {str(e)}")
            return None
            
    async def update_rule_group(self, group_id: int, update_data: Dict[str, Any]) -> Optional[RuleGroup]:
        """更新规则组"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(RuleGroup).where(RuleGroup.id == group_id)
                )
                group = result.scalars().first()
                
                if not group:
                    return None
                    
                was_enabled = group.enabled
                
                for key, value in update_data.items():
                    if hasattr(group, key):
                        setattr(group, key, value)
                        
                group.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(group)
                
                if was_enabled and not group.enabled:
                    await self._unload_rule_group(group_id)
                elif not was_enabled and group.enabled:
                    await self._load_rule_group(group)
                elif group.enabled:
                    await self._reload_rule_group(group)
                    
                return group
                
        except Exception as e:
            logger.error(f"Failed to update rule group {group_id}: {str(e)}")
            return None
            
    async def update_distribution_rule(self, rule_id: int, update_data: Dict[str, Any]) -> Optional[DistributionRule]:
        """更新分发规则"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(DistributionRule).where(DistributionRule.id == rule_id)
                )
                rule = result.scalars().first()
                
                if not rule:
                    return None
                    
                was_enabled = rule.enabled
                
                for key, value in update_data.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                        
                rule.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(rule)
                
                if was_enabled and not rule.enabled:
                    await self._unload_distribution_rule(rule_id)
                elif not was_enabled and rule.enabled:
                    await self._load_distribution_rule(rule)
                elif rule.enabled:
                    await self._reload_distribution_rule(rule)
                    
                return rule
                
        except Exception as e:
            logger.error(f"Failed to update distribution rule {rule_id}: {str(e)}")
            return None
            
    async def process_alarm(self, alarm: AlarmTable) -> List[Dict[str, Any]]:
        """处理告警，应用分发规则"""
        try:
            distributions = []
            
            # 按优先级排序的规则组
            sorted_groups = sorted(
                self.rule_groups.values(),
                key=lambda x: x.get("priority", 0),
                reverse=True
            )
            
            for group_info in sorted_groups:
                group_rules = group_info.get("rules", [])
                
                # 按优先级排序的规则
                sorted_rules = sorted(
                    group_rules,
                    key=lambda x: x.get("priority", 0),
                    reverse=True
                )
                
                for rule_info in sorted_rules:
                    if await self._evaluate_rule_conditions(alarm, rule_info["conditions"]):
                        actions = rule_info["actions"]
                        rule_distributions = await self._execute_rule_actions(alarm, rule_info["id"], actions)
                        distributions.extend(rule_distributions)
                        
                        # 如果规则配置了停止继续处理，则跳出
                        if actions.get("stop_processing", False):
                            break
                            
            return distributions
            
        except Exception as e:
            logger.error(f"Failed to process alarm {alarm.id}: {str(e)}")
            return []
            
    async def _load_rule_group(self, group: RuleGroup):
        """加载规则组"""
        try:
            async with async_session_maker() as session:
                # 加载规则组的所有规则
                result = await session.execute(
                    select(DistributionRule).where(
                        and_(
                            DistributionRule.rule_group_id == group.id,
                            DistributionRule.enabled == True
                        )
                    )
                )
                rules = result.scalars().all()
                
                rules_info = []
                for rule in rules:
                    rules_info.append({
                        "id": rule.id,
                        "name": rule.name,
                        "conditions": rule.conditions,
                        "actions": rule.actions,
                        "priority": rule.priority
                    })
                    
                self.rule_groups[group.id] = {
                    "id": group.id,
                    "name": group.name,
                    "priority": group.priority,
                    "rules": rules_info
                }
                
                logger.info(f"Loaded rule group: {group.name} with {len(rules_info)} rules")
                
        except Exception as e:
            logger.error(f"Failed to load rule group {group.id}: {str(e)}")
            
    async def _load_distribution_rule(self, rule: DistributionRule):
        """加载分发规则"""
        try:
            self.active_rules[rule.id] = {
                "id": rule.id,
                "name": rule.name,
                "group_id": rule.rule_group_id,
                "conditions": rule.conditions,
                "actions": rule.actions,
                "priority": rule.priority
            }
            
            logger.info(f"Loaded distribution rule: {rule.name}")
            
        except Exception as e:
            logger.error(f"Failed to load distribution rule {rule.id}: {str(e)}")
            
    async def _unload_rule_group(self, group_id: int):
        """卸载规则组"""
        if group_id in self.rule_groups:
            del self.rule_groups[group_id]
            logger.info(f"Unloaded rule group: {group_id}")
            
    async def _unload_distribution_rule(self, rule_id: int):
        """卸载分发规则"""
        if rule_id in self.active_rules:
            del self.active_rules[rule_id]
            logger.info(f"Unloaded distribution rule: {rule_id}")
            
    async def _reload_rule_group(self, group: RuleGroup):
        """重新加载规则组"""
        await self._unload_rule_group(group.id)
        await self._load_rule_group(group)
        
    async def _reload_distribution_rule(self, rule: DistributionRule):
        """重新加载分发规则"""
        await self._unload_distribution_rule(rule.id)
        await self._load_distribution_rule(rule)
        
    async def _evaluate_rule_conditions(self, alarm: AlarmTable, conditions: Dict[str, Any]) -> bool:
        """评估规则条件"""
        try:
            if not conditions:
                return True
                
            # 逻辑操作符
            if "and" in conditions:
                return all(
                    await self._evaluate_condition(alarm, cond) 
                    for cond in conditions["and"]
                )
                
            if "or" in conditions:
                return any(
                    await self._evaluate_condition(alarm, cond) 
                    for cond in conditions["or"]
                )
                
            if "not" in conditions:
                return not await self._evaluate_condition(alarm, conditions["not"])
                
            # 直接条件
            return await self._evaluate_condition(alarm, conditions)
            
        except Exception as e:
            logger.error(f"Failed to evaluate rule conditions: {str(e)}")
            return False
            
    async def _evaluate_condition(self, alarm: AlarmTable, condition: Dict[str, Any]) -> bool:
        """评估单个条件"""
        try:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")
            
            if not all([field, operator]):
                return False
                
            alarm_value = getattr(alarm, field, None)
            
            if operator == "equals":
                return alarm_value == value
            elif operator == "not_equals":
                return alarm_value != value
            elif operator == "contains":
                return value in str(alarm_value) if alarm_value else False
            elif operator == "not_contains":
                return value not in str(alarm_value) if alarm_value else True
            elif operator == "starts_with":
                return str(alarm_value).startswith(value) if alarm_value else False
            elif operator == "ends_with":
                return str(alarm_value).endswith(value) if alarm_value else False
            elif operator == "regex":
                return bool(re.search(value, str(alarm_value))) if alarm_value else False
            elif operator == "in":
                return alarm_value in value if isinstance(value, list) else False
            elif operator == "not_in":
                return alarm_value not in value if isinstance(value, list) else True
            elif operator == "greater_than":
                return float(alarm_value) > float(value) if alarm_value else False
            elif operator == "less_than":
                return float(alarm_value) < float(value) if alarm_value else False
            elif operator == "greater_equal":
                return float(alarm_value) >= float(value) if alarm_value else False
            elif operator == "less_equal":
                return float(alarm_value) <= float(value) if alarm_value else False
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to evaluate condition: {str(e)}")
            return False
            
    async def _execute_rule_actions(self, alarm: AlarmTable, rule_id: int, actions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行规则动作"""
        try:
            distributions = []
            
            # 分发给用户
            if "notify_users" in actions:
                user_ids = actions["notify_users"]
                for user_id in user_ids:
                    distribution = await self._create_alarm_distribution(alarm.id, rule_id, user_id)
                    if distribution:
                        distributions.append(distribution)
                        
            # 分发给用户组
            if "notify_groups" in actions:
                group_ids = actions["notify_groups"]
                for group_id in group_ids:
                    user_ids = await self._get_users_in_group(group_id)
                    for user_id in user_ids:
                        distribution = await self._create_alarm_distribution(alarm.id, rule_id, user_id)
                        if distribution:
                            distributions.append(distribution)
                            
            # 根据订阅分发
            if "notify_subscribers" in actions:
                subscribers = await self._get_alarm_subscribers(alarm)
                for user_id in subscribers:
                    distribution = await self._create_alarm_distribution(alarm.id, rule_id, user_id)
                    if distribution:
                        distributions.append(distribution)
                        
            # 更新告警状态
            if "update_status" in actions:
                new_status = actions["update_status"]
                await self._update_alarm_status(alarm.id, new_status)
                
            # 添加标签
            if "add_tags" in actions:
                tags = actions["add_tags"]
                await self._add_alarm_tags(alarm.id, tags)
                
            return distributions
            
        except Exception as e:
            logger.error(f"Failed to execute rule actions: {str(e)}")
            return []
            
    async def _create_alarm_distribution(self, alarm_id: int, rule_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """创建告警分发记录"""
        try:
            async with async_session_maker() as session:
                distribution = AlarmDistribution(
                    alarm_id=alarm_id,
                    rule_id=rule_id,
                    user_id=user_id,
                    status="pending"
                )
                
                session.add(distribution)
                await session.commit()
                await session.refresh(distribution)
                
                return {
                    "id": distribution.id,
                    "alarm_id": alarm_id,
                    "rule_id": rule_id,
                    "user_id": user_id,
                    "status": distribution.status
                }
                
        except Exception as e:
            logger.error(f"Failed to create alarm distribution: {str(e)}")
            return None
            
    async def _get_users_in_group(self, group_id: int) -> List[int]:
        """获取用户组中的用户"""
        # 这里需要根据实际的用户组实现来获取用户列表
        # 暂时返回空列表
        return []
        
    async def _get_alarm_subscribers(self, alarm: AlarmTable) -> List[int]:
        """获取告警订阅者"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(UserSubscription).where(
                        UserSubscription.enabled == True
                    )
                )
                subscriptions = result.scalars().all()
                
                subscribers = []
                for subscription in subscriptions:
                    if await self._matches_subscription_filters(alarm, subscription.filters):
                        subscribers.append(subscription.user_id)
                        
                return subscribers
                
        except Exception as e:
            logger.error(f"Failed to get alarm subscribers: {str(e)}")
            return []
            
    async def _matches_subscription_filters(self, alarm: AlarmTable, filters: Dict[str, Any]) -> bool:
        """检查告警是否匹配订阅过滤条件"""
        return await self._evaluate_rule_conditions(alarm, filters)
        
    async def _update_alarm_status(self, alarm_id: int, new_status: str):
        """更新告警状态"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(AlarmTable).where(AlarmTable.id == alarm_id)
                )
                alarm = result.scalars().first()
                
                if alarm:
                    alarm.status = new_status
                    alarm.updated_at = datetime.utcnow()
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"Failed to update alarm status: {str(e)}")
            
    async def _add_alarm_tags(self, alarm_id: int, tags: Dict[str, Any]):
        """添加告警标签"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(AlarmTable).where(AlarmTable.id == alarm_id)
                )
                alarm = result.scalars().first()
                
                if alarm:
                    existing_tags = alarm.tags or {}
                    existing_tags.update(tags)
                    alarm.tags = existing_tags
                    alarm.updated_at = datetime.utcnow()
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"Failed to add alarm tags: {str(e)}")
            
    async def load_all_rules(self):
        """加载所有启用的规则"""
        try:
            async with async_session_maker() as session:
                # 加载规则组
                result = await session.execute(
                    select(RuleGroup).where(RuleGroup.enabled == True)
                )
                groups = result.scalars().all()
                
                for group in groups:
                    await self._load_rule_group(group)
                    
                logger.info(f"Loaded {len(groups)} rule groups")
                
        except Exception as e:
            logger.error(f"Failed to load rules: {str(e)}")
            
    async def get_rule_stats(self) -> Dict[str, Any]:
        """获取规则统计信息"""
        try:
            return {
                "active_groups": len(self.rule_groups),
                "active_rules": sum(len(group["rules"]) for group in self.rule_groups.values()),
                "groups": list(self.rule_groups.keys()),
            }
            
        except Exception as e:
            logger.error(f"Failed to get rule stats: {str(e)}")
            return {"active_groups": 0, "active_rules": 0, "groups": []}