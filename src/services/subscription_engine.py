"""
规则订阅引擎
支持灵活的告警订阅规则匹配和通知分发
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import re
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from src.models.alarm import AlarmTable, UserSubscription
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OperatorType(Enum):
    """操作符类型"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "gt"
    GREATER_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_EQUAL = "lte"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class ConditionLogic(Enum):
    """条件逻辑"""
    AND = "and"
    OR = "or"


class RuleCondition:
    """规则条件"""
    
    def __init__(
        self,
        field: str,
        operator: OperatorType,
        value: Any = None,
        values: List[Any] = None
    ):
        self.field = field
        self.operator = operator
        self.value = value
        self.values = values or []
    
    def evaluate(self, alarm_data: Dict[str, Any]) -> bool:
        """评估条件是否满足"""
        try:
            field_value = self._get_field_value(alarm_data, self.field)
            
            if self.operator == OperatorType.EQUALS:
                return self._equals(field_value, self.value)
            elif self.operator == OperatorType.NOT_EQUALS:
                return not self._equals(field_value, self.value)
            elif self.operator == OperatorType.CONTAINS:
                return self._contains(field_value, self.value)
            elif self.operator == OperatorType.NOT_CONTAINS:
                return not self._contains(field_value, self.value)
            elif self.operator == OperatorType.STARTS_WITH:
                return str(field_value).startswith(str(self.value))
            elif self.operator == OperatorType.ENDS_WITH:
                return str(field_value).endswith(str(self.value))
            elif self.operator == OperatorType.REGEX:
                return bool(re.search(str(self.value), str(field_value)))
            elif self.operator == OperatorType.IN:
                return field_value in self.values
            elif self.operator == OperatorType.NOT_IN:
                return field_value not in self.values
            elif self.operator == OperatorType.GREATER_THAN:
                return self._numeric_compare(field_value, self.value, lambda x, y: x > y)
            elif self.operator == OperatorType.GREATER_EQUAL:
                return self._numeric_compare(field_value, self.value, lambda x, y: x >= y)
            elif self.operator == OperatorType.LESS_THAN:
                return self._numeric_compare(field_value, self.value, lambda x, y: x < y)
            elif self.operator == OperatorType.LESS_EQUAL:
                return self._numeric_compare(field_value, self.value, lambda x, y: x <= y)
            elif self.operator == OperatorType.BETWEEN:
                if len(self.values) >= 2:
                    return self._between(field_value, self.values[0], self.values[1])
                return False
            elif self.operator == OperatorType.IS_NULL:
                return field_value is None or field_value == ""
            elif self.operator == OperatorType.IS_NOT_NULL:
                return field_value is not None and field_value != ""
            
            return False
            
        except Exception as e:
            logger.warning(f"Error evaluating condition {self.field} {self.operator}: {e}")
            return False
    
    def _get_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """获取嵌套字段值，支持点号路径"""
        try:
            value = data
            for part in field_path.split('.'):
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value
        except Exception:
            return None
    
    def _equals(self, value1: Any, value2: Any) -> bool:
        """相等比较，支持类型转换"""
        if value1 is None or value2 is None:
            return value1 is value2
        
        # 字符串比较忽略大小写
        if isinstance(value1, str) and isinstance(value2, str):
            return value1.lower() == value2.lower()
        
        return value1 == value2
    
    def _contains(self, container: Any, item: Any) -> bool:
        """包含比较"""
        if container is None or item is None:
            return False
        
        container_str = str(container).lower()
        item_str = str(item).lower()
        
        return item_str in container_str
    
    def _numeric_compare(self, value1: Any, value2: Any, comparator) -> bool:
        """数值比较"""
        try:
            num1 = float(value1) if value1 is not None else None
            num2 = float(value2) if value2 is not None else None
            
            if num1 is None or num2 is None:
                return False
            
            return comparator(num1, num2)
        except (ValueError, TypeError):
            return False
    
    def _between(self, value: Any, min_val: Any, max_val: Any) -> bool:
        """范围比较"""
        try:
            num_value = float(value) if value is not None else None
            num_min = float(min_val) if min_val is not None else None
            num_max = float(max_val) if max_val is not None else None
            
            if num_value is None or num_min is None or num_max is None:
                return False
            
            return num_min <= num_value <= num_max
        except (ValueError, TypeError):
            return False


class SubscriptionRule:
    """订阅规则"""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        conditions: List[RuleCondition],
        logic: ConditionLogic = ConditionLogic.AND,
        enabled: bool = True,
        priority: int = 1,
        time_restrictions: Optional[Dict[str, Any]] = None
    ):
        self.rule_id = rule_id
        self.name = name
        self.conditions = conditions
        self.logic = logic
        self.enabled = enabled
        self.priority = priority
        self.time_restrictions = time_restrictions or {}
    
    def matches(self, alarm_data: Dict[str, Any]) -> bool:
        """检查告警是否匹配规则"""
        if not self.enabled:
            return False
        
        # 检查时间限制
        if not self._check_time_restrictions():
            return False
        
        if not self.conditions:
            return True
        
        # 评估所有条件
        results = [condition.evaluate(alarm_data) for condition in self.conditions]
        
        if self.logic == ConditionLogic.AND:
            return all(results)
        else:  # OR
            return any(results)
    
    def _check_time_restrictions(self) -> bool:
        """检查时间限制"""
        if not self.time_restrictions:
            return True
        
        now = datetime.now()
        
        # 检查工作日限制
        weekdays = self.time_restrictions.get("weekdays")
        if weekdays is not None:
            current_weekday = now.weekday()  # 0=Monday, 6=Sunday
            if current_weekday not in weekdays:
                return False
        
        # 检查时间范围限制
        time_range = self.time_restrictions.get("time_range")
        if time_range:
            start_time = time_range.get("start", "00:00")
            end_time = time_range.get("end", "23:59")
            
            current_time = now.strftime("%H:%M")
            
            if start_time <= end_time:
                # 同一天内的时间范围
                if not (start_time <= current_time <= end_time):
                    return False
            else:
                # 跨天的时间范围
                if not (current_time >= start_time or current_time <= end_time):
                    return False
        
        return True


class SubscriptionEngine:
    """订阅引擎"""
    
    def __init__(self):
        self.rules: Dict[str, SubscriptionRule] = {}
        self.user_subscriptions: Dict[str, List[str]] = {}  # user_id -> [rule_ids]
        self.notification_cache: Set[str] = set()  # 通知去重缓存
        self.rate_limiter: Dict[str, List[datetime]] = {}  # 频率限制
    
    def add_rule(self, rule: SubscriptionRule):
        """添加订阅规则"""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added subscription rule: {rule.name}")
    
    def remove_rule(self, rule_id: str):
        """删除订阅规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed subscription rule: {rule_id}")
    
    def subscribe_user(self, user_id: str, rule_ids: List[str]):
        """用户订阅规则"""
        # 验证规则是否存在
        valid_rule_ids = [rule_id for rule_id in rule_ids if rule_id in self.rules]
        
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = []
        
        # 添加新的订阅
        for rule_id in valid_rule_ids:
            if rule_id not in self.user_subscriptions[user_id]:
                self.user_subscriptions[user_id].append(rule_id)
        
        logger.info(f"User {user_id} subscribed to {len(valid_rule_ids)} rules")
    
    def unsubscribe_user(self, user_id: str, rule_ids: List[str]):
        """用户取消订阅规则"""
        if user_id in self.user_subscriptions:
            for rule_id in rule_ids:
                if rule_id in self.user_subscriptions[user_id]:
                    self.user_subscriptions[user_id].remove(rule_id)
        
        logger.info(f"User {user_id} unsubscribed from {len(rule_ids)} rules")
    
    def find_matching_subscriptions(
        self, 
        alarm_data: Dict[str, Any]
    ) -> Dict[str, List[SubscriptionRule]]:
        """查找匹配的订阅"""
        matching_subscriptions = {}
        
        # 遍历所有用户的订阅
        for user_id, rule_ids in self.user_subscriptions.items():
            matching_rules = []
            
            for rule_id in rule_ids:
                rule = self.rules.get(rule_id)
                if rule and rule.matches(alarm_data):
                    matching_rules.append(rule)
            
            if matching_rules:
                # 按优先级排序
                matching_rules.sort(key=lambda r: r.priority, reverse=True)
                matching_subscriptions[user_id] = matching_rules
        
        return matching_subscriptions
    
    def should_notify(
        self, 
        user_id: str, 
        rule_id: str, 
        alarm_fingerprint: str,
        max_notifications_per_hour: int = 10
    ) -> bool:
        """检查是否应该发送通知（去重和频率限制）"""
        
        # 构建通知唯一标识
        notification_key = f"{user_id}:{rule_id}:{alarm_fingerprint}"
        
        # 检查是否已经通知过相同的告警
        if notification_key in self.notification_cache:
            return False
        
        # 检查频率限制
        rate_key = f"{user_id}:{rule_id}"
        now = datetime.now()
        
        if rate_key not in self.rate_limiter:
            self.rate_limiter[rate_key] = []
        
        # 清理过期的通知记录（1小时前）
        cutoff_time = now - timedelta(hours=1)
        self.rate_limiter[rate_key] = [
            ts for ts in self.rate_limiter[rate_key] if ts > cutoff_time
        ]
        
        # 检查是否超过频率限制
        if len(self.rate_limiter[rate_key]) >= max_notifications_per_hour:
            logger.warning(f"Rate limit exceeded for {rate_key}")
            return False
        
        # 记录通知
        self.notification_cache.add(notification_key)
        self.rate_limiter[rate_key].append(now)
        
        # 定期清理缓存（保留最近24小时）
        asyncio.create_task(self._cleanup_cache_later(notification_key))
        
        return True
    
    async def _cleanup_cache_later(self, notification_key: str):
        """延时清理缓存"""
        await asyncio.sleep(24 * 3600)  # 24小时后清理
        self.notification_cache.discard(notification_key)
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """获取规则统计信息"""
        stats = {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for rule in self.rules.values() if rule.enabled),
            "total_subscriptions": sum(len(rules) for rules in self.user_subscriptions.values()),
            "active_users": len(self.user_subscriptions),
            "rule_details": []
        }
        
        for rule in self.rules.values():
            subscribers = sum(
                1 for rule_ids in self.user_subscriptions.values() 
                if rule.rule_id in rule_ids
            )
            
            stats["rule_details"].append({
                "rule_id": rule.rule_id,
                "name": rule.name,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "conditions_count": len(rule.conditions),
                "subscribers": subscribers
            })
        
        return stats


class RuleBuilder:
    """规则构建器"""
    
    @staticmethod
    def build_from_dict(rule_data: Dict[str, Any]) -> SubscriptionRule:
        """从字典构建规则"""
        conditions = []
        
        for condition_data in rule_data.get("conditions", []):
            condition = RuleCondition(
                field=condition_data["field"],
                operator=OperatorType(condition_data["operator"]),
                value=condition_data.get("value"),
                values=condition_data.get("values", [])
            )
            conditions.append(condition)
        
        return SubscriptionRule(
            rule_id=rule_data["rule_id"],
            name=rule_data["name"],
            conditions=conditions,
            logic=ConditionLogic(rule_data.get("logic", "and")),
            enabled=rule_data.get("enabled", True),
            priority=rule_data.get("priority", 1),
            time_restrictions=rule_data.get("time_restrictions")
        )
    
    @staticmethod
    def create_severity_rule(
        rule_id: str,
        name: str,
        severities: List[str],
        priority: int = 1
    ) -> SubscriptionRule:
        """创建基于严重程度的规则"""
        condition = RuleCondition(
            field="severity",
            operator=OperatorType.IN,
            values=severities
        )
        
        return SubscriptionRule(
            rule_id=rule_id,
            name=name,
            conditions=[condition],
            priority=priority
        )
    
    @staticmethod
    def create_system_rule(
        rule_id: str,
        name: str,
        systems: List[str],
        priority: int = 1
    ) -> SubscriptionRule:
        """创建基于系统的规则"""
        condition = RuleCondition(
            field="tags.system",
            operator=OperatorType.IN,
            values=systems
        )
        
        return SubscriptionRule(
            rule_id=rule_id,
            name=name,
            conditions=[condition],
            priority=priority
        )
    
    @staticmethod
    def create_environment_rule(
        rule_id: str,
        name: str,
        environments: List[str],
        priority: int = 1
    ) -> SubscriptionRule:
        """创建基于环境的规则"""
        condition = RuleCondition(
            field="tags.environment",
            operator=OperatorType.IN,
            values=environments
        )
        
        return SubscriptionRule(
            rule_id=rule_id,
            name=name,
            conditions=[condition],
            priority=priority
        )
    
    @staticmethod
    def create_composite_rule(
        rule_id: str,
        name: str,
        severities: List[str],
        systems: List[str],
        environments: List[str] = None,
        logic: ConditionLogic = ConditionLogic.AND,
        priority: int = 1
    ) -> SubscriptionRule:
        """创建复合规则"""
        conditions = []
        
        if severities:
            conditions.append(RuleCondition(
                field="severity",
                operator=OperatorType.IN,
                values=severities
            ))
        
        if systems:
            conditions.append(RuleCondition(
                field="tags.system",
                operator=OperatorType.IN,
                values=systems
            ))
        
        if environments:
            conditions.append(RuleCondition(
                field="tags.environment",
                operator=OperatorType.IN,
                values=environments
            ))
        
        return SubscriptionRule(
            rule_id=rule_id,
            name=name,
            conditions=conditions,
            logic=logic,
            priority=priority
        )