"""
告警生命周期管理API接口
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.core.responses import DataResponse, ListResponse, data_response, list_response
from src.core.exceptions import AlarmSystemException, to_http_exception
from src.services.alarm_lifecycle_manager import (
    lifecycle_manager, LifecycleEventType, LifecycleRule, EscalationLevel
)

router = APIRouter()


class LifecycleRuleResponse(BaseModel):
    """生命周期规则响应"""
    name: str
    condition: Dict[str, Any]
    action: Dict[str, Any]
    priority: int
    enabled: bool


class EscalationLevelResponse(BaseModel):
    """升级级别响应"""
    level: int
    delay_minutes: int
    targets: List[int]
    notification_channels: List[str]
    auto_assign: bool


class EscalationPolicyResponse(BaseModel):
    """升级策略响应"""
    policy_name: str
    levels: List[EscalationLevelResponse]


class LifecycleEventRequest(BaseModel):
    """生命周期事件请求"""
    event_type: str
    context: Optional[Dict[str, Any]] = None


class LifecycleRuleRequest(BaseModel):
    """生命周期规则请求"""
    name: str
    condition: Dict[str, Any]
    action: Dict[str, Any]
    priority: int = 100
    enabled: bool = True


class EscalationLevelRequest(BaseModel):
    """升级级别请求"""
    level: int
    delay_minutes: int
    targets: List[int]
    notification_channels: List[str]
    auto_assign: bool = False


class EscalationPolicyRequest(BaseModel):
    """升级策略请求"""
    policy_name: str
    levels: List[EscalationLevelRequest]


def get_current_user_id() -> int:
    """获取当前用户ID"""
    # TODO: 实现真正的用户认证
    return 1


@router.post("/alarms/{alarm_id}/lifecycle/trigger", response_model=DataResponse[dict])
async def trigger_lifecycle_event(
    alarm_id: int,
    event_request: LifecycleEventRequest,
    current_user: int = Depends(get_current_user_id)
):
    """触发告警生命周期事件"""
    try:
        # 验证事件类型
        try:
            event_type = LifecycleEventType(event_request.event_type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的事件类型: {event_request.event_type}"
            )
        
        # 触发事件
        await lifecycle_manager.trigger_lifecycle_event(
            alarm_id, 
            event_type, 
            event_request.context or {}
        )
        
        return data_response(
            {"alarm_id": alarm_id, "event_type": event_request.event_type},
            "生命周期事件触发成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发生命周期事件失败: {str(e)}")


@router.get("/lifecycle/rules", response_model=ListResponse[LifecycleRuleResponse])
async def get_lifecycle_rules():
    """获取生命周期规则列表"""
    try:
        rules = []
        for rule in lifecycle_manager.rules:
            rules.append(LifecycleRuleResponse(
                name=rule.name,
                condition=rule.condition,
                action=rule.action,
                priority=rule.priority,
                enabled=rule.enabled
            ))
        
        return list_response(rules, len(rules), "获取规则列表成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取规则列表失败: {str(e)}")


@router.post("/lifecycle/rules", response_model=DataResponse[LifecycleRuleResponse])
async def create_lifecycle_rule(
    rule_request: LifecycleRuleRequest,
    current_user: int = Depends(get_current_user_id)
):
    """创建生命周期规则"""
    try:
        # 检查规则名称是否已存在
        existing_names = [rule.name for rule in lifecycle_manager.rules]
        if rule_request.name in existing_names:
            raise HTTPException(status_code=400, detail="规则名称已存在")
        
        # 创建新规则
        new_rule = LifecycleRule(
            name=rule_request.name,
            condition=rule_request.condition,
            action=rule_request.action,
            priority=rule_request.priority,
            enabled=rule_request.enabled
        )
        
        # 添加到规则列表并按优先级排序
        lifecycle_manager.rules.append(new_rule)
        lifecycle_manager.rules.sort(key=lambda r: r.priority)
        
        response = LifecycleRuleResponse(
            name=new_rule.name,
            condition=new_rule.condition,
            action=new_rule.action,
            priority=new_rule.priority,
            enabled=new_rule.enabled
        )
        
        return data_response(response, "规则创建成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建规则失败: {str(e)}")


@router.put("/lifecycle/rules/{rule_name}", response_model=DataResponse[LifecycleRuleResponse])
async def update_lifecycle_rule(
    rule_name: str,
    rule_request: LifecycleRuleRequest,
    current_user: int = Depends(get_current_user_id)
):
    """更新生命周期规则"""
    try:
        # 查找规则
        rule_index = None
        for i, rule in enumerate(lifecycle_manager.rules):
            if rule.name == rule_name:
                rule_index = i
                break
        
        if rule_index is None:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        # 更新规则
        updated_rule = LifecycleRule(
            name=rule_request.name,
            condition=rule_request.condition,
            action=rule_request.action,
            priority=rule_request.priority,
            enabled=rule_request.enabled
        )
        
        lifecycle_manager.rules[rule_index] = updated_rule
        lifecycle_manager.rules.sort(key=lambda r: r.priority)
        
        response = LifecycleRuleResponse(
            name=updated_rule.name,
            condition=updated_rule.condition,
            action=updated_rule.action,
            priority=updated_rule.priority,
            enabled=updated_rule.enabled
        )
        
        return data_response(response, "规则更新成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新规则失败: {str(e)}")


@router.delete("/lifecycle/rules/{rule_name}", response_model=DataResponse[dict])
async def delete_lifecycle_rule(
    rule_name: str,
    current_user: int = Depends(get_current_user_id)
):
    """删除生命周期规则"""
    try:
        # 查找并删除规则
        original_count = len(lifecycle_manager.rules)
        lifecycle_manager.rules = [rule for rule in lifecycle_manager.rules if rule.name != rule_name]
        
        if len(lifecycle_manager.rules) == original_count:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        return data_response({"rule_name": rule_name}, "规则删除成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除规则失败: {str(e)}")


@router.get("/lifecycle/escalation-policies", response_model=ListResponse[EscalationPolicyResponse])
async def get_escalation_policies():
    """获取升级策略列表"""
    try:
        policies = []
        for policy_name, levels in lifecycle_manager.escalation_policies.items():
            level_responses = []
            for level in levels:
                level_responses.append(EscalationLevelResponse(
                    level=level.level,
                    delay_minutes=level.delay_minutes,
                    targets=level.targets,
                    notification_channels=level.notification_channels,
                    auto_assign=level.auto_assign
                ))
            
            policies.append(EscalationPolicyResponse(
                policy_name=policy_name,
                levels=level_responses
            ))
        
        return list_response(policies, len(policies), "获取升级策略成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取升级策略失败: {str(e)}")


@router.post("/lifecycle/escalation-policies", response_model=DataResponse[EscalationPolicyResponse])
async def create_escalation_policy(
    policy_request: EscalationPolicyRequest,
    current_user: int = Depends(get_current_user_id)
):
    """创建升级策略"""
    try:
        # 检查策略名称是否已存在
        if policy_request.policy_name in lifecycle_manager.escalation_policies:
            raise HTTPException(status_code=400, detail="升级策略名称已存在")
        
        # 创建升级级别
        levels = []
        for level_req in policy_request.levels:
            levels.append(EscalationLevel(
                level=level_req.level,
                delay_minutes=level_req.delay_minutes,
                targets=level_req.targets,
                notification_channels=level_req.notification_channels,
                auto_assign=level_req.auto_assign
            ))
        
        # 按级别排序
        levels.sort(key=lambda l: l.level)
        
        # 添加到策略字典
        lifecycle_manager.escalation_policies[policy_request.policy_name] = levels
        
        # 构建响应
        level_responses = []
        for level in levels:
            level_responses.append(EscalationLevelResponse(
                level=level.level,
                delay_minutes=level.delay_minutes,
                targets=level.targets,
                notification_channels=level.notification_channels,
                auto_assign=level.auto_assign
            ))
        
        response = EscalationPolicyResponse(
            policy_name=policy_request.policy_name,
            levels=level_responses
        )
        
        return data_response(response, "升级策略创建成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建升级策略失败: {str(e)}")


@router.put("/lifecycle/escalation-policies/{policy_name}", response_model=DataResponse[EscalationPolicyResponse])
async def update_escalation_policy(
    policy_name: str,
    policy_request: EscalationPolicyRequest,
    current_user: int = Depends(get_current_user_id)
):
    """更新升级策略"""
    try:
        # 检查策略是否存在
        if policy_name not in lifecycle_manager.escalation_policies:
            raise HTTPException(status_code=404, detail="升级策略不存在")
        
        # 创建升级级别
        levels = []
        for level_req in policy_request.levels:
            levels.append(EscalationLevel(
                level=level_req.level,
                delay_minutes=level_req.delay_minutes,
                targets=level_req.targets,
                notification_channels=level_req.notification_channels,
                auto_assign=level_req.auto_assign
            ))
        
        # 按级别排序
        levels.sort(key=lambda l: l.level)
        
        # 更新策略
        lifecycle_manager.escalation_policies[policy_name] = levels
        
        # 构建响应
        level_responses = []
        for level in levels:
            level_responses.append(EscalationLevelResponse(
                level=level.level,
                delay_minutes=level.delay_minutes,
                targets=level.targets,
                notification_channels=level.notification_channels,
                auto_assign=level.auto_assign
            ))
        
        response = EscalationPolicyResponse(
            policy_name=policy_name,
            levels=level_responses
        )
        
        return data_response(response, "升级策略更新成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新升级策略失败: {str(e)}")


@router.delete("/lifecycle/escalation-policies/{policy_name}", response_model=DataResponse[dict])
async def delete_escalation_policy(
    policy_name: str,
    current_user: int = Depends(get_current_user_id)
):
    """删除升级策略"""
    try:
        # 检查策略是否存在
        if policy_name not in lifecycle_manager.escalation_policies:
            raise HTTPException(status_code=404, detail="升级策略不存在")
        
        # 删除策略
        del lifecycle_manager.escalation_policies[policy_name]
        
        return data_response({"policy_name": policy_name}, "升级策略删除成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除升级策略失败: {str(e)}")


@router.get("/lifecycle/statistics", response_model=DataResponse[Dict[str, Any]])
async def get_lifecycle_statistics(
    days: int = Query(30, ge=1, le=365)
):
    """获取生命周期统计信息"""
    try:
        stats = await lifecycle_manager.get_lifecycle_statistics(days)
        return data_response(stats, "统计信息获取成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/lifecycle/process", response_model=DataResponse[dict])
async def process_lifecycle_events(
    current_user: int = Depends(get_current_user_id)
):
    """手动触发生命周期事件处理"""
    try:
        await lifecycle_manager.process_lifecycle_events()
        return data_response({"processed": True}, "生命周期事件处理完成")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理生命周期事件失败: {str(e)}")


@router.get("/lifecycle/event-types", response_model=DataResponse[List[dict]])
async def get_lifecycle_event_types():
    """获取生命周期事件类型列表"""
    try:
        event_types = [
            {"value": event_type.value, "label": event_type.value}
            for event_type in LifecycleEventType
        ]
        return data_response(event_types, "获取事件类型成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取事件类型失败: {str(e)}")


@router.get("/lifecycle/rule-templates", response_model=DataResponse[List[dict]])
async def get_rule_templates():
    """获取规则模板"""
    try:
        templates = [
            {
                "name": "自动确认低优先级告警",
                "description": "自动确认低优先级和信息类告警",
                "condition": {
                    "severity": ["low", "info"],
                    "age_minutes": 5,
                    "status": ["active"]
                },
                "action": {
                    "type": "acknowledge",
                    "message": "低优先级告警自动确认"
                },
                "priority": 200
            },
            {
                "name": "SLA预警通知",
                "description": "SLA剩余时间不足20%时发送预警",
                "condition": {
                    "sla_remaining_percent": 20,
                    "status": ["pending", "acknowledged", "in_progress"]
                },
                "action": {
                    "type": "sla_warning",
                    "notify": ["assigned_user", "manager"]
                },
                "priority": 50
            },
            {
                "name": "自动升级关键告警",
                "description": "关键告警30分钟未处理自动升级",
                "condition": {
                    "severity": ["critical"],
                    "age_minutes": 30,
                    "status": ["pending"]
                },
                "action": {
                    "type": "escalate",
                    "escalation_policy": "critical_alerts"
                },
                "priority": 10
            },
            {
                "name": "自动关闭已解决告警",
                "description": "已解决告警24小时后自动关闭",
                "condition": {
                    "status": ["resolved"],
                    "age_hours": 24,
                    "no_activity_hours": 2
                },
                "action": {
                    "type": "close",
                    "message": "已解决告警自动关闭"
                },
                "priority": 300
            }
        ]
        
        return data_response(templates, "获取规则模板成功")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取规则模板失败: {str(e)}")