"""
告警降噪服务
"""

import re
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.orm import selectinload

from src.core.database import async_session_maker
from src.core.logging import get_logger
from src.core.exceptions import DatabaseException, ValidationException, ResourceNotFoundException
from src.models.noise_reduction import (
    NoiseReductionRule, NoiseRuleExecutionLog, NoiseReductionStats,
    NoiseReductionRuleCreate, NoiseReductionRuleUpdate,
    NoiseRuleType, NoiseRuleAction, RuleCondition, RuleConditionGroup
)
from src.models.alarm import AlarmTable

logger = get_logger(__name__)


class NoiseReductionEngine:
    """告警降噪引擎"""
    
    def __init__(self):
        self.logger = logger
        self._rule_cache = {}
        self._cache_ttl = 300  # 5分钟缓存
        self._stats = {
            "total_processed": 0,
            "total_suppressed": 0,
            "total_delayed": 0,
            "total_aggregated": 0,
            "total_downgraded": 0,
            "total_discarded": 0
        }
    
    async def process_alarm(self, alarm_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        处理单个告警的降噪
        
        Returns:
            Tuple[是否通过, 执行的动作, 处理结果]
        """
        start_time = datetime.utcnow()
        
        try:
            # 获取活跃的降噪规则
            rules = await self._get_active_rules()
            
            # 按优先级排序规则
            rules = sorted(rules, key=lambda r: r.priority)
            
            for rule in rules:
                try:
                    # 检查规则是否匹配
                    matched, match_details = await self._check_rule_match(rule, alarm_data)
                    
                    if matched:
                        # 执行降噪动作
                        action_result = await self._execute_rule_action(rule, alarm_data)
                        
                        # 记录执行日志
                        await self._log_rule_execution(
                            rule, alarm_data, matched, match_details, action_result, start_time
                        )
                        
                        # 更新规则统计
                        await self._update_rule_stats(rule)
                        
                        # 更新全局统计
                        self._update_global_stats(rule.action)
                        
                        # 如果动作是丢弃或抑制，则停止处理
                        if rule.action in [NoiseRuleAction.DISCARD, NoiseRuleAction.SUPPRESS]:
                            return False, rule.action, action_result
                        
                        # 如果动作是修改告警，则应用修改后继续处理
                        if rule.action in [NoiseRuleAction.DOWNGRADE, NoiseRuleAction.DELAY]:
                            alarm_data.update(action_result.get("modified_alarm", {}))
                
                except Exception as e:
                    self.logger.error(f"Error processing rule {rule.id}: {str(e)}")
                    await self._log_rule_execution(
                        rule, alarm_data, False, {}, {"error": str(e)}, start_time
                    )
            
            # 所有规则都没有阻止告警，允许通过
            return True, "forward", {"processed": True}
            
        except Exception as e:
            self.logger.error(f"Error in noise reduction processing: {str(e)}")
            return True, "error", {"error": str(e)}
    
    async def batch_process_alarms(self, alarms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量处理告警降噪"""
        processed_alarms = []
        
        for alarm in alarms:
            passed, action, result = await self.process_alarm(alarm)
            
            if passed:
                # 应用可能的修改
                if "modified_alarm" in result:
                    alarm.update(result["modified_alarm"])
                processed_alarms.append(alarm)
            else:
                # 记录被抑制的告警
                self.logger.info(
                    f"Alarm suppressed by noise reduction: {action}",
                    extra={"alarm_id": alarm.get("id"), "action": action}
                )
        
        return processed_alarms
    
    # 规则匹配逻辑
    
    async def _check_rule_match(self, rule: NoiseReductionRule, alarm_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """检查规则是否匹配告警"""
        try:
            conditions = rule.conditions
            match_details = {"rule_type": rule.rule_type, "conditions_checked": []}
            
            # 检查时间有效性
            now = datetime.utcnow()
            if rule.effective_start and now < rule.effective_start:
                return False, {"reason": "before_effective_start"}
            if rule.effective_end and now > rule.effective_end:
                return False, {"reason": "after_effective_end"}
            
            # 根据规则类型执行不同的匹配逻辑
            if rule.rule_type == NoiseRuleType.FREQUENCY_LIMIT:
                return await self._check_frequency_limit(rule, alarm_data, match_details)
            elif rule.rule_type == NoiseRuleType.THRESHOLD_FILTER:
                return await self._check_threshold_filter(rule, alarm_data, match_details)
            elif rule.rule_type == NoiseRuleType.SILENCE_WINDOW:
                return await self._check_silence_window(rule, alarm_data, match_details)
            elif rule.rule_type == NoiseRuleType.DEPENDENCY_FILTER:
                return await self._check_dependency_filter(rule, alarm_data, match_details)
            elif rule.rule_type == NoiseRuleType.DUPLICATE_SUPPRESS:
                return await self._check_duplicate_suppress(rule, alarm_data, match_details)
            elif rule.rule_type == NoiseRuleType.TIME_BASED:
                return await self._check_time_based(rule, alarm_data, match_details)
            elif rule.rule_type == NoiseRuleType.CUSTOM_RULE:
                return await self._check_custom_rule(rule, alarm_data, match_details)
            else:
                return False, {"reason": "unknown_rule_type"}
                
        except Exception as e:
            self.logger.error(f"Error checking rule match: {str(e)}")
            return False, {"error": str(e)}
    
    async def _check_frequency_limit(self, rule: NoiseReductionRule, alarm_data: Dict[str, Any], match_details: Dict) -> Tuple[bool, Dict]:
        """检查频率限制规则"""
        conditions = rule.conditions
        time_window = conditions.get("time_window_minutes", 10)
        max_count = conditions.get("max_count", 3)
        group_by = conditions.get("group_by", ["host", "service"])
        
        # 构建分组键
        group_key = self._build_group_key(alarm_data, group_by)
        
        # 查询时间窗口内的相似告警数量
        time_threshold = datetime.utcnow() - timedelta(minutes=time_window)
        
        async with async_session_maker() as session:
            # 构建查询条件
            filters = [AlarmTable.created_at >= time_threshold]
            
            for field in group_by:
                if field in alarm_data and alarm_data[field]:
                    filters.append(getattr(AlarmTable, field) == alarm_data[field])
            
            count_result = await session.execute(
                select(func.count(AlarmTable.id)).where(and_(*filters))
            )
            current_count = count_result.scalar()
        
        match_details["frequency_check"] = {
            "group_key": group_key,
            "time_window_minutes": time_window,
            "current_count": current_count,
            "max_count": max_count
        }
        
        return current_count >= max_count, match_details
    
    async def _check_threshold_filter(self, rule: NoiseReductionRule, alarm_data: Dict[str, Any], match_details: Dict) -> Tuple[bool, Dict]:
        """检查阈值过滤规则"""
        conditions = rule.conditions
        time_window_hours = conditions.get("time_window_hours", 1)
        min_occurrences = conditions.get("min_occurrences", 5)
        severity_filter = conditions.get("severity", [])
        
        # 检查严重程度是否在过滤范围内
        alarm_severity = alarm_data.get("severity", "").lower()
        if severity_filter and alarm_severity not in [s.lower() for s in severity_filter]:
            return False, match_details
        
        # 查询时间窗口内的告警数量
        time_threshold = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        async with async_session_maker() as session:
            filters = [
                AlarmTable.created_at >= time_threshold,
                AlarmTable.title == alarm_data.get("title"),
                AlarmTable.host == alarm_data.get("host"),
                AlarmTable.service == alarm_data.get("service")
            ]
            
            count_result = await session.execute(
                select(func.count(AlarmTable.id)).where(and_(*filters))
            )
            occurrence_count = count_result.scalar()
        
        match_details["threshold_check"] = {
            "time_window_hours": time_window_hours,
            "occurrence_count": occurrence_count,
            "min_occurrences": min_occurrences,
            "severity_filter": severity_filter
        }
        
        return occurrence_count < min_occurrences, match_details
    
    async def _check_silence_window(self, rule: NoiseReductionRule, alarm_data: Dict[str, Any], match_details: Dict) -> Tuple[bool, Dict]:
        """检查静默窗口规则"""
        conditions = rule.conditions
        time_ranges = conditions.get("time_ranges", [])
        affected_systems = conditions.get("affected_systems", [])
        
        now = datetime.utcnow()
        current_time = now.strftime("%H:%M")
        
        # 检查是否在静默时间窗口内
        in_silence_window = False
        for time_range in time_ranges:
            start_time = time_range.get("start")
            end_time = time_range.get("end")
            
            if self._time_in_range(current_time, start_time, end_time):
                in_silence_window = True
                break
        
        # 检查是否是受影响的系统
        system_affected = True
        if affected_systems:
            alarm_system = alarm_data.get("system_id") or alarm_data.get("source")
            system_affected = alarm_system in affected_systems
        
        match_details["silence_check"] = {
            "current_time": current_time,
            "in_silence_window": in_silence_window,
            "system_affected": system_affected,
            "time_ranges": time_ranges
        }
        
        return in_silence_window and system_affected, match_details
    
    async def _check_dependency_filter(self, rule: NoiseReductionRule, alarm_data: Dict[str, Any], match_details: Dict) -> Tuple[bool, Dict]:
        """检查依赖过滤规则"""
        conditions = rule.conditions
        dependency_map = conditions.get("dependency_map", {})
        cascade_timeout = conditions.get("cascade_timeout_minutes", 5)
        
        # 检查是否有父服务告警
        alarm_service = alarm_data.get("service")
        parent_services = dependency_map.get(alarm_service, [])
        
        if not parent_services:
            return False, match_details
        
        # 查询父服务是否有活跃告警
        time_threshold = datetime.utcnow() - timedelta(minutes=cascade_timeout)
        
        async with async_session_maker() as session:
            parent_alarm_result = await session.execute(
                select(AlarmTable).where(
                    and_(
                        AlarmTable.service.in_(parent_services),
                        AlarmTable.status.in_(["active", "critical"]),
                        AlarmTable.created_at >= time_threshold
                    )
                )
            )
            parent_alarms = parent_alarm_result.scalars().all()
        
        has_parent_alarm = len(parent_alarms) > 0
        
        match_details["dependency_check"] = {
            "alarm_service": alarm_service,
            "parent_services": parent_services,
            "parent_alarms_found": len(parent_alarms),
            "cascade_timeout_minutes": cascade_timeout
        }
        
        return has_parent_alarm, match_details
    
    async def _check_duplicate_suppress(self, rule: NoiseReductionRule, alarm_data: Dict[str, Any], match_details: Dict) -> Tuple[bool, Dict]:
        """检查重复抑制规则"""
        conditions = rule.conditions
        similarity_threshold = conditions.get("similarity_threshold", 0.9)
        time_window_minutes = conditions.get("time_window_minutes", 30)
        
        # 查询时间窗口内的相似告警
        time_threshold = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        async with async_session_maker() as session:
            similar_alarms = await session.execute(
                select(AlarmTable).where(
                    and_(
                        AlarmTable.created_at >= time_threshold,
                        AlarmTable.title.ilike(f"%{alarm_data.get('title', '')}%"),
                        AlarmTable.host == alarm_data.get("host"),
                        AlarmTable.service == alarm_data.get("service")
                    )
                )
            )
            similar_alarm_list = similar_alarms.scalars().all()
        
        # 计算相似度
        max_similarity = 0
        for similar_alarm in similar_alarm_list:
            similarity = self._calculate_alarm_similarity(alarm_data, {
                "title": similar_alarm.title,
                "description": similar_alarm.description,
                "host": similar_alarm.host,
                "service": similar_alarm.service
            })
            max_similarity = max(max_similarity, similarity)
        
        is_duplicate = max_similarity >= similarity_threshold
        
        match_details["duplicate_check"] = {
            "similarity_threshold": similarity_threshold,
            "max_similarity": max_similarity,
            "similar_alarms_count": len(similar_alarm_list),
            "is_duplicate": is_duplicate
        }
        
        return is_duplicate, match_details
    
    async def _check_time_based(self, rule: NoiseReductionRule, alarm_data: Dict[str, Any], match_details: Dict) -> Tuple[bool, Dict]:
        """检查基于时间的规则"""
        conditions = rule.conditions
        allowed_hours = conditions.get("allowed_hours", [])  # 24小时制，如 [9, 10, 11, 12, 13, 14, 15, 16, 17]
        blocked_weekdays = conditions.get("blocked_weekdays", [])  # 0=周一, 6=周日
        
        now = datetime.utcnow()
        current_hour = now.hour
        current_weekday = now.weekday()
        
        # 检查是否在允许的小时内
        hour_blocked = allowed_hours and current_hour not in allowed_hours
        
        # 检查是否在禁止的工作日
        weekday_blocked = current_weekday in blocked_weekdays
        
        should_block = hour_blocked or weekday_blocked
        
        match_details["time_check"] = {
            "current_hour": current_hour,
            "current_weekday": current_weekday,
            "allowed_hours": allowed_hours,
            "blocked_weekdays": blocked_weekdays,
            "hour_blocked": hour_blocked,
            "weekday_blocked": weekday_blocked
        }
        
        return should_block, match_details
    
    async def _check_custom_rule(self, rule: NoiseReductionRule, alarm_data: Dict[str, Any], match_details: Dict) -> Tuple[bool, Dict]:
        """检查自定义规则"""
        conditions = rule.conditions
        rule_expression = conditions.get("expression", "")
        condition_groups = conditions.get("condition_groups", [])
        
        # 处理条件组
        if condition_groups:
            return await self._evaluate_condition_groups(condition_groups, alarm_data, match_details)
        
        # 处理表达式（简单实现）
        if rule_expression:
            return await self._evaluate_expression(rule_expression, alarm_data, match_details)
        
        return False, match_details
    
    # 规则动作执行
    
    async def _execute_rule_action(self, rule: NoiseReductionRule, alarm_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行规则动作"""
        action = rule.action
        parameters = rule.parameters or {}
        
        if action == NoiseRuleAction.SUPPRESS:
            return {"action": "suppressed", "reason": "noise_reduction_rule"}
        
        elif action == NoiseRuleAction.DISCARD:
            return {"action": "discarded", "reason": "noise_reduction_rule"}
        
        elif action == NoiseRuleAction.DELAY:
            delay_minutes = parameters.get("delay_minutes", 5)
            return {
                "action": "delayed",
                "delay_minutes": delay_minutes,
                "delayed_until": datetime.utcnow() + timedelta(minutes=delay_minutes)
            }
        
        elif action == NoiseRuleAction.DOWNGRADE:
            new_severity = parameters.get("new_severity", "low")
            return {
                "action": "downgraded",
                "original_severity": alarm_data.get("severity"),
                "new_severity": new_severity,
                "modified_alarm": {"severity": new_severity}
            }
        
        elif action == NoiseRuleAction.AGGREGATE:
            group_key = parameters.get("group_key", "default")
            return {
                "action": "aggregated",
                "group_key": group_key,
                "aggregate_window": parameters.get("aggregate_window_minutes", 10)
            }
        
        elif action == NoiseRuleAction.FORWARD:
            return {"action": "forwarded", "reason": "passed_all_checks"}
        
        else:
            return {"action": "unknown", "error": f"Unknown action: {action}"}
    
    # 工具方法
    
    def _build_group_key(self, alarm_data: Dict[str, Any], group_by: List[str]) -> str:
        """构建分组键"""
        key_parts = []
        for field in group_by:
            value = alarm_data.get(field, "unknown")
            key_parts.append(f"{field}:{value}")
        return "|".join(key_parts)
    
    def _time_in_range(self, current_time: str, start_time: str, end_time: str) -> bool:
        """检查时间是否在范围内"""
        try:
            current = datetime.strptime(current_time, "%H:%M").time()
            start = datetime.strptime(start_time, "%H:%M").time()
            end = datetime.strptime(end_time, "%H:%M").time()
            
            if start <= end:
                return start <= current <= end
            else:  # 跨天的情况
                return current >= start or current <= end
        except:
            return False
    
    def _calculate_alarm_similarity(self, alarm1: Dict[str, Any], alarm2: Dict[str, Any]) -> float:
        """计算告警相似度"""
        # 简单的相似度计算（可以使用更复杂的算法）
        title_similarity = self._text_similarity(
            alarm1.get("title", ""), alarm2.get("title", "")
        )
        
        host_match = 1.0 if alarm1.get("host") == alarm2.get("host") else 0.0
        service_match = 1.0 if alarm1.get("service") == alarm2.get("service") else 0.0
        
        # 加权平均
        similarity = (title_similarity * 0.5 + host_match * 0.3 + service_match * 0.2)
        return similarity
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 简单的Jaccard相似度
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    async def _evaluate_condition_groups(self, condition_groups: List[Dict], alarm_data: Dict[str, Any], match_details: Dict) -> Tuple[bool, Dict]:
        """评估条件组"""
        # 实现条件组的评估逻辑
        for group in condition_groups:
            logic = group.get("logic", "AND")
            conditions = group.get("conditions", [])
            
            results = []
            for condition in conditions:
                field = condition.get("field")
                operator = condition.get("operator")
                value = condition.get("value")
                
                result = self._evaluate_condition(alarm_data, field, operator, value)
                results.append(result)
            
            if logic == "AND" and all(results):
                return True, match_details
            elif logic == "OR" and any(results):
                return True, match_details
        
        return False, match_details
    
    def _evaluate_condition(self, alarm_data: Dict[str, Any], field: str, operator: str, value: Any) -> bool:
        """评估单个条件"""
        alarm_value = alarm_data.get(field)
        
        if operator == "eq":
            return alarm_value == value
        elif operator == "ne":
            return alarm_value != value
        elif operator == "in":
            return alarm_value in value if isinstance(value, list) else False
        elif operator == "not_in":
            return alarm_value not in value if isinstance(value, list) else False
        elif operator == "contains":
            return str(value).lower() in str(alarm_value).lower() if alarm_value else False
        elif operator == "regex":
            return bool(re.search(str(value), str(alarm_value))) if alarm_value else False
        elif operator == "gt":
            try:
                return float(alarm_value) > float(value)
            except:
                return False
        elif operator == "lt":
            try:
                return float(alarm_value) < float(value)
            except:
                return False
        elif operator == "gte":
            try:
                return float(alarm_value) >= float(value)
            except:
                return False
        elif operator == "lte":
            try:
                return float(alarm_value) <= float(value)
            except:
                return False
        
        return False
    
    async def _evaluate_expression(self, expression: str, alarm_data: Dict[str, Any], match_details: Dict) -> Tuple[bool, Dict]:
        """评估表达式（简单实现）"""
        # 这里可以实现更复杂的表达式评估逻辑
        # 为了安全起见，这里只是一个简单的示例
        try:
            # 替换变量
            safe_expression = expression
            for key, value in alarm_data.items():
                if isinstance(value, str):
                    safe_expression = safe_expression.replace(f"${key}", f"'{value}'")
                else:
                    safe_expression = safe_expression.replace(f"${key}", str(value))
            
            # 简单的安全检查
            if any(dangerous in safe_expression for dangerous in ["import", "exec", "eval", "__"]):
                return False, {"error": "unsafe_expression"}
            
            # 评估表达式
            result = eval(safe_expression)
            return bool(result), {"expression": safe_expression, "result": result}
        except Exception as e:
            return False, {"error": str(e)}
    
    # 数据访问和缓存
    
    async def _get_active_rules(self) -> List[NoiseReductionRule]:
        """获取活跃的降噪规则"""
        cache_key = "active_noise_rules"
        cached = self._rule_cache.get(cache_key)
        
        if cached and cached["expires"] > datetime.utcnow():
            return cached["rules"]
        
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(NoiseReductionRule)
                    .where(NoiseReductionRule.enabled == True)
                    .order_by(NoiseReductionRule.priority)
                )
                rules = result.scalars().all()
                
                # 缓存结果
                self._rule_cache[cache_key] = {
                    "rules": rules,
                    "expires": datetime.utcnow() + timedelta(seconds=self._cache_ttl)
                }
                
                return rules
            except Exception as e:
                self.logger.error(f"Error getting active rules: {str(e)}")
                return []
    
    async def _log_rule_execution(self, rule: NoiseReductionRule, alarm_data: Dict[str, Any], 
                                 matched: bool, match_details: Dict, action_result: Dict, start_time: datetime):
        """记录规则执行日志"""
        try:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            async with async_session_maker() as session:
                log = NoiseRuleExecutionLog(
                    rule_id=rule.id,
                    alarm_id=alarm_data.get("id"),
                    matched=matched,
                    action_taken=action_result.get("action"),
                    result="success" if "error" not in action_result else "error",
                    match_details=match_details,
                    execution_time_ms=execution_time,
                    error_message=action_result.get("error")
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            self.logger.error(f"Error logging rule execution: {str(e)}")
    
    async def _update_rule_stats(self, rule: NoiseReductionRule):
        """更新规则统计"""
        try:
            async with async_session_maker() as session:
                await session.execute(
                    update(NoiseReductionRule)
                    .where(NoiseReductionRule.id == rule.id)
                    .values(
                        hit_count=NoiseReductionRule.hit_count + 1,
                        last_hit=datetime.utcnow()
                    )
                )
                await session.commit()
        except Exception as e:
            self.logger.error(f"Error updating rule stats: {str(e)}")
    
    def _update_global_stats(self, action: str):
        """更新全局统计"""
        self._stats["total_processed"] += 1
        
        if action == NoiseRuleAction.SUPPRESS:
            self._stats["total_suppressed"] += 1
        elif action == NoiseRuleAction.DELAY:
            self._stats["total_delayed"] += 1
        elif action == NoiseRuleAction.AGGREGATE:
            self._stats["total_aggregated"] += 1
        elif action == NoiseRuleAction.DOWNGRADE:
            self._stats["total_downgraded"] += 1
        elif action == NoiseRuleAction.DISCARD:
            self._stats["total_discarded"] += 1
    
    def clear_cache(self):
        """清除缓存"""
        self._rule_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()


# 全局降噪引擎实例
noise_reduction_engine = NoiseReductionEngine()