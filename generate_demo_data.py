#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成演示告警数据
"""

import asyncio
import sys
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from src.core.database import init_db
from src.services.collector import AlarmCollector


async def generate_demo_alarms():
    """生成演示告警数据"""
    print("🚀 开始生成演示告警数据...")
    
    # 初始化数据库
    await init_db()
    
    collector = AlarmCollector()
    await collector.start()
    
    # 预定义的告警数据模板
    alarm_templates = [
        {
            "source": "prometheus",
            "title": "CPU使用率过高",
            "description": "服务器CPU使用率超过90%",
            "severity": "high",
            "category": "system",
            "host": "web-server-01",
            "service": "webapp",
            "tags": {"env": "production", "team": "devops"},
            "alarm_metadata": {"threshold": 90, "current": 95.2}
        },
        {
            "source": "grafana",
            "title": "内存使用率告警",
            "description": "内存使用率超过85%",
            "severity": "medium", 
            "category": "system",
            "host": "db-server-01",
            "service": "database",
            "tags": {"env": "production", "team": "dba"},
            "alarm_metadata": {"threshold": 85, "current": 88.5}
        },
        {
            "source": "zabbix",
            "title": "磁盘空间不足",
            "description": "磁盘使用率超过90%",
            "severity": "critical",
            "category": "storage",
            "host": "file-server-01",
            "service": "storage",
            "tags": {"env": "production", "team": "ops"},
            "alarm_metadata": {"threshold": 90, "current": 94.8}
        },
        {
            "source": "elasticsearch",
            "title": "搜索响应时间过长",
            "description": "搜索请求平均响应时间超过2秒",
            "severity": "medium",
            "category": "performance",
            "host": "search-server-01", 
            "service": "search",
            "tags": {"env": "production", "team": "backend"},
            "alarm_metadata": {"threshold": 2000, "current": 2500}
        },
        {
            "source": "nginx",
            "title": "HTTP 5xx错误率过高",
            "description": "过去5分钟HTTP 5xx错误率超过5%",
            "severity": "high",
            "category": "application",
            "host": "lb-01",
            "service": "loadbalancer",
            "tags": {"env": "production", "team": "devops"},
            "alarm_metadata": {"threshold": 5, "current": 8.2}
        },
        {
            "source": "mysql",
            "title": "数据库连接数过多",
            "description": "MySQL活跃连接数超过阈值",
            "severity": "medium",
            "category": "database",
            "host": "db-server-02",
            "service": "mysql",
            "tags": {"env": "production", "team": "dba"},
            "alarm_metadata": {"threshold": 100, "current": 120}
        },
        {
            "source": "redis",
            "title": "缓存命中率下降",
            "description": "Redis缓存命中率低于90%",
            "severity": "low",
            "category": "cache",
            "host": "cache-server-01",
            "service": "redis",
            "tags": {"env": "production", "team": "backend"},
            "alarm_metadata": {"threshold": 90, "current": 85.5}
        },
        {
            "source": "kubernetes",
            "title": "Pod重启频繁",
            "description": "Pod在过去1小时内重启次数超过3次",
            "severity": "medium",
            "category": "container",
            "host": "k8s-node-01",
            "service": "user-service",
            "tags": {"env": "production", "team": "devops", "namespace": "default"},
            "alarm_metadata": {"threshold": 3, "current": 5}
        },
        {
            "source": "jenkins",
            "title": "构建失败",
            "description": "生产环境部署构建失败",
            "severity": "high",
            "category": "ci/cd",
            "host": "jenkins-master",
            "service": "jenkins",
            "tags": {"env": "production", "team": "devops", "pipeline": "prod-deploy"},
            "alarm_metadata": {"build_number": 234, "branch": "main"}
        },
        {
            "source": "mongodb",
            "title": "文档写入延迟",
            "description": "MongoDB写入操作平均延迟超过100ms",
            "severity": "medium",
            "category": "database",
            "host": "mongo-01",
            "service": "mongodb",
            "tags": {"env": "production", "team": "backend"},
            "alarm_metadata": {"threshold": 100, "current": 150}
        }
    ]
    
    # 扩展的主机和服务列表
    hosts = [
        "web-server-01", "web-server-02", "web-server-03",
        "db-server-01", "db-server-02", "db-server-03",
        "cache-server-01", "cache-server-02",
        "api-server-01", "api-server-02", "api-server-03",
        "lb-01", "lb-02", "monitor-01", "file-server-01"
    ]
    
    services = [
        "webapp", "database", "cache", "api", "loadbalancer",
        "monitoring", "logging", "search", "message-queue",
        "auth", "payment", "notification", "analytics"
    ]
    
    severities = ["critical", "high", "medium", "low", "info"]
    statuses = ["active", "active", "active", "resolved", "acknowledged"]  # 更多活跃状态
    
    success_count = 0
    failed_count = 0
    
    # 生成基础告警数据
    for template in alarm_templates:
        # 为每个模板生成1-3个变体
        for i in range(random.randint(1, 3)):
            alarm_data = template.copy()
            
            # 随机化一些字段
            if i > 0:
                alarm_data["host"] = random.choice(hosts)
                alarm_data["service"] = random.choice(services)
                alarm_data["severity"] = random.choice(severities)
                
                # 调整描述
                if alarm_data["severity"] == "critical":
                    alarm_data["description"] = alarm_data["description"].replace("超过", "严重超过")
                elif alarm_data["severity"] == "low":
                    alarm_data["description"] = alarm_data["description"].replace("超过", "接近")
            
            # 随机设置状态
            if random.random() < 0.7:  # 70%概率是活跃状态
                alarm_data["status"] = "active"
            else:
                alarm_data["status"] = random.choice(["resolved", "acknowledged"])
            
            try:
                success = await collector.collect_alarm_dict(alarm_data)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"❌ 告警创建失败: {str(e)}")
                failed_count += 1
    
    # 生成随机告警数据
    print("📊 生成随机告警数据...")
    for i in range(50):  # 额外生成50个随机告警
        alarm_data = {
            "source": random.choice(["prometheus", "grafana", "zabbix", "elasticsearch", "custom", "monitoring"]),
            "title": f"随机告警 #{i+1}",
            "description": f"这是第{i+1}个随机生成的告警",
            "severity": random.choice(severities),
            "category": random.choice(["system", "application", "network", "database", "security"]),
            "host": random.choice(hosts),
            "service": random.choice(services),
            "environment": random.choice(["production", "staging", "development"]),
            "tags": {
                "env": random.choice(["production", "staging", "development"]),
                "team": random.choice(["devops", "backend", "frontend", "dba", "security"]),
                "priority": random.choice(["p1", "p2", "p3"])
            },
            "alarm_metadata": {
                "auto_generated": True,
                "correlation_id": f"corr-{random.randint(1000, 9999)}"
            }
        }
        
        # 随机设置状态
        if random.random() < 0.6:  # 60%概率是活跃状态
            alarm_data["status"] = "active"
        else:
            alarm_data["status"] = random.choice(["resolved", "acknowledged", "suppressed"])
            
        try:
            success = await collector.collect_alarm_dict(alarm_data)
            if success:
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            failed_count += 1
    
    # 生成历史告警数据 (过去7天)
    print("📅 生成历史告警数据...")
    for day in range(7):
        date_offset = timedelta(days=day)
        for hour in range(0, 24, 2):  # 每2小时一个时间点
            hour_offset = timedelta(hours=hour)
            timestamp = datetime.utcnow() - date_offset - hour_offset
            
            # 每个时间点生成2-5个告警
            for _ in range(random.randint(2, 5)):
                template = random.choice(alarm_templates)
                alarm_data = template.copy()
                
                # 随机化数据
                alarm_data["host"] = random.choice(hosts)
                alarm_data["service"] = random.choice(services)
                alarm_data["severity"] = random.choice(severities)
                alarm_data["created_at"] = timestamp.isoformat()
                
                # 历史数据大部分应该已解决
                if random.random() < 0.8:
                    alarm_data["status"] = "resolved"
                    alarm_data["resolved_at"] = (timestamp + timedelta(minutes=random.randint(5, 120))).isoformat()
                else:
                    alarm_data["status"] = random.choice(["active", "acknowledged"])
                
                try:
                    success = await collector.collect_alarm_dict(alarm_data)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
    
    await collector.stop()
    
    print(f"\n✅ 告警数据生成完成!")
    print(f"   📊 成功: {success_count}")
    print(f"   ❌ 失败: {failed_count}")
    print(f"   📈 总计: {success_count + failed_count}")
    print(f"\n🎉 访问管理后台查看数据: http://localhost:8000/admin")


if __name__ == "__main__":
    asyncio.run(generate_demo_alarms())