#!/usr/bin/env python3
"""
告警降噪系统初始化脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from src.services.noise_reduction_manager import NoiseReductionManager
from src.models.noise_reduction import NoiseReductionRuleCreate, NoiseRuleType, NoiseRuleAction
from src.core.logging import get_logger

logger = get_logger(__name__)


async def create_default_rules():
    """创建默认的降噪规则"""
    print("开始创建默认降噪规则...")
    
    manager = NoiseReductionManager()
    
    # 默认规则配置
    default_rules = [
        {
            "name": "高频告警抑制",
            "description": "抑制10分钟内相同主机和服务超过5次的告警",
            "rule_type": NoiseRuleType.FREQUENCY_LIMIT,
            "action": NoiseRuleAction.SUPPRESS,
            "conditions": {
                "time_window_minutes": 10,
                "max_count": 5,
                "group_by": ["host", "service", "title"]
            },
            "parameters": {
                "action_after_limit": "suppress",
                "reset_window": True
            },
            "priority": 10
        },
        {
            "name": "低级别告警过滤",
            "description": "过滤1小时内出现次数少于3次的低级别告警",
            "rule_type": NoiseRuleType.THRESHOLD_FILTER,
            "action": NoiseRuleAction.DISCARD,
            "conditions": {
                "time_window_hours": 1,
                "min_occurrences": 3,
                "severity": ["low", "info"]
            },
            "parameters": {
                "discard_below_threshold": True
            },
            "priority": 20
        },
        {
            "name": "夜间维护静默",
            "description": "在夜间维护时间窗口内抑制非紧急告警",
            "rule_type": NoiseRuleType.SILENCE_WINDOW,
            "action": NoiseRuleAction.SUPPRESS,
            "conditions": {
                "time_ranges": [
                    {"start": "02:00", "end": "06:00", "timezone": "UTC"}
                ],
                "affected_systems": [],
                "severity_filter": ["low", "medium", "info"]
            },
            "parameters": {
                "maintenance_mode": True,
                "notify_before_window": 15
            },
            "priority": 30
        },
        {
            "name": "重复告警抑制",
            "description": "抑制30分钟内90%相似的重复告警",
            "rule_type": NoiseRuleType.DUPLICATE_SUPPRESS,
            "action": NoiseRuleAction.SUPPRESS,
            "conditions": {
                "similarity_threshold": 0.9,
                "time_window_minutes": 30
            },
            "parameters": {
                "keep_first_occurrence": True,
                "aggregate_count": True
            },
            "priority": 40
        },
        {
            "name": "工作时间外降级",
            "description": "在非工作时间将中等级别告警降级为低级别",
            "rule_type": NoiseRuleType.TIME_BASED,
            "action": NoiseRuleAction.DOWNGRADE,
            "conditions": {
                "allowed_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17],  # 9:00-17:59
                "blocked_weekdays": [5, 6],  # 周六、周日
                "severity_filter": ["medium"]
            },
            "parameters": {
                "new_severity": "low",
                "add_note": "Downgraded due to non-business hours"
            },
            "priority": 50
        }
    ]
    
    created_rules = []
    
    try:
        for rule_config in default_rules:
            try:
                rule_data = NoiseReductionRuleCreate(**rule_config)
                rule = await manager.create_rule(rule_data, creator_id=1)  # 系统用户
                created_rules.append(rule)
                print(f"   ✅ 创建规则: {rule.name}")
            except Exception as e:
                print(f"   ❌ 创建规则失败 '{rule_config['name']}': {str(e)}")
        
        print(f"\n📊 降噪规则创建完成:")
        print(f"   成功创建: {len(created_rules)} 个规则")
        print(f"   失败: {len(default_rules) - len(created_rules)} 个规则")
        
        return created_rules
        
    except Exception as e:
        print(f"❌ 创建默认规则失败: {str(e)}")
        raise


async def create_template_rules():
    """从模板创建规则"""
    print("\n🔧 从模板创建规则...")
    
    manager = NoiseReductionManager()
    
    template_rules = [
        {
            "template_name": "frequency_limit",
            "rule_name": "数据库连接告警频率限制",
            "custom_params": {
                "conditions": {
                    "time_window_minutes": 5,
                    "max_count": 3,
                    "group_by": ["host", "service"],
                    "service_filter": ["database", "mysql", "postgresql"]
                }
            }
        },
        {
            "template_name": "threshold_filter",
            "rule_name": "网络延迟告警阈值过滤",
            "custom_params": {
                "conditions": {
                    "time_window_hours": 2,
                    "min_occurrences": 10,
                    "severity": ["info"],
                    "category_filter": ["network", "latency"]
                }
            }
        }
    ]
    
    created_count = 0
    
    try:
        for template_config in template_rules:
            try:
                rule = await manager.create_rule_from_template(
                    template_config["template_name"],
                    template_config["rule_name"],
                    template_config["custom_params"],
                    creator_id=1
                )
                created_count += 1
                print(f"   ✅ 从模板创建规则: {rule.name}")
            except Exception as e:
                print(f"   ❌ 从模板创建规则失败 '{template_config['rule_name']}': {str(e)}")
        
        print(f"   模板规则创建: {created_count} 个")
        
    except Exception as e:
        print(f"❌ 模板规则创建失败: {str(e)}")


async def test_noise_reduction():
    """测试降噪功能"""
    print("\n🧪 测试降噪功能...")
    
    from src.services.noise_reduction_service import noise_reduction_engine
    
    # 测试告警数据
    test_alarms = [
        {
            "id": 1,
            "title": "Database connection timeout",
            "description": "Connection to database failed",
            "severity": "high",
            "host": "db-server-01",
            "service": "database",
            "source": "monitoring",
            "category": "database"
        },
        {
            "id": 2,
            "title": "High CPU usage",
            "description": "CPU usage is above 90%",
            "severity": "medium",
            "host": "web-server-01",
            "service": "web",
            "source": "monitoring",
            "category": "performance"
        },
        {
            "id": 3,
            "title": "Low disk space",
            "description": "Disk usage is above 95%",
            "severity": "low",
            "host": "app-server-01",
            "service": "application",
            "source": "monitoring",
            "category": "storage"
        }
    ]
    
    try:
        # 批量处理测试
        processed_alarms = await noise_reduction_engine.batch_process_alarms(test_alarms)
        
        print(f"   原始告警数: {len(test_alarms)}")
        print(f"   处理后告警数: {len(processed_alarms)}")
        print(f"   降噪率: {((len(test_alarms) - len(processed_alarms)) / len(test_alarms) * 100):.1f}%")
        
        # 获取引擎统计
        stats = noise_reduction_engine.get_stats()
        print(f"   引擎统计: {stats}")
        
    except Exception as e:
        print(f"   ❌ 测试失败: {str(e)}")


async def show_system_status():
    """显示系统状态"""
    print("\n📊 降噪系统状态:")
    
    try:
        manager = NoiseReductionManager()
        
        # 获取规则统计
        all_rules = await manager.get_rules(limit=1000)
        active_rules = await manager.get_rules(enabled_only=True, limit=1000)
        
        print(f"   总规则数: {len(all_rules)}")
        print(f"   活跃规则数: {len(active_rules)}")
        
        # 按类型分组统计
        rule_types = {}
        for rule in all_rules:
            rule_type = rule.rule_type
            if rule_type not in rule_types:
                rule_types[rule_type] = {"total": 0, "active": 0}
            rule_types[rule_type]["total"] += 1
            if rule.enabled:
                rule_types[rule_type]["active"] += 1
        
        print(f"\n   规则类型分布:")
        for rule_type, counts in rule_types.items():
            print(f"     - {rule_type}: {counts['active']}/{counts['total']} (活跃/总数)")
        
        # 获取系统统计
        system_stats = await manager.get_system_stats()
        print(f"\n   系统性能:")
        performance = system_stats.get("performance", {})
        print(f"     - 24小时执行次数: {performance.get('executions_24h', 0)}")
        print(f"     - 24小时匹配次数: {performance.get('matches_24h', 0)}")
        print(f"     - 平均执行时间: {performance.get('avg_execution_time_ms', 0):.2f}ms")
        
        # 获取模板信息
        templates = await manager.get_rule_templates()
        print(f"\n   可用模板: {len(templates)} 个")
        for template_name in templates.keys():
            print(f"     - {template_name}")
            
    except Exception as e:
        print(f"   ❌ 获取状态失败: {str(e)}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="告警降噪系统管理工具")
    parser.add_argument("--init", action="store_true", help="初始化降噪系统")
    parser.add_argument("--create-defaults", action="store_true", help="创建默认规则")
    parser.add_argument("--create-templates", action="store_true", help="从模板创建规则")
    parser.add_argument("--test", action="store_true", help="测试降噪功能")
    parser.add_argument("--status", action="store_true", help="显示系统状态")
    parser.add_argument("--all", action="store_true", help="执行所有操作")
    
    args = parser.parse_args()
    
    if not any([args.init, args.create_defaults, args.create_templates, args.test, args.status, args.all]):
        parser.print_help()
        return
    
    async def run_tasks():
        print("🚀 告警降噪系统初始化")
        print("=" * 50)
        
        if args.all or args.init or args.create_defaults:
            await create_default_rules()
        
        if args.all or args.create_templates:
            await create_template_rules()
        
        if args.all or args.test:
            await test_noise_reduction()
        
        if args.all or args.status:
            await show_system_status()
        
        print("\n" + "=" * 50)
        print("🎉 降噪系统初始化完成")
        print("\n💡 使用建议:")
        print("   1. 通过API接口 /api/v1/noise-reduction/rules 管理规则")
        print("   2. 使用 /api/v1/noise-reduction/test-alarm 测试单个告警")
        print("   3. 查看 /api/v1/noise-reduction/stats/overview 监控降噪效果")
        print("   4. 根据实际需求调整规则的优先级和参数")
    
    try:
        asyncio.run(run_tasks())
    except Exception as e:
        print(f"\n❌ 操作失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()