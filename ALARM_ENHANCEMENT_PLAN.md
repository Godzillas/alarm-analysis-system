# 告警去重、降噪、订阅功能开发计划

## 📋 项目概述

基于当前告警接入功能，开发告警去重、降噪和订阅功能，提升告警系统的智能化水平和用户体验。

## 🎯 核心目标

1. **告警去重** - 消除重复告警，减少告警风暴
2. **告警降噪** - 智能过滤和聚合，提升告警质量  
3. **订阅管理** - 精准告警推送，个性化通知

## 📊 现状分析

### ✅ 已有功能
- 告警数据模型完整（支持去重字段：correlation_id, is_duplicate, similarity_score）
- 基础聚合服务（aggregator.py）
- 订阅引擎框架（subscription_engine.py）
- 关联分析引擎（correlation_engine.py）
- 通知管理服务

### ⚠️ 待开发功能
- 告警指纹生成算法
- 实时去重处理
- 智能降噪规则
- 时间窗口聚合
- 订阅规则匹配
- 用户订阅管理界面

## 🚀 开发计划

### 阶段一：告警去重功能 (优先级：高)

#### 1.1 告警指纹生成机制
```python
# 文件：src/services/deduplication_engine.py
class AlarmFingerprint:
    def generate_fingerprint(self, alarm_data: Dict) -> str:
        """生成告警指纹，用于去重识别"""
        # 基于 title + host + service + severity 生成指纹
        # 使用 SHA256 哈希确保唯一性
```

**开发任务：**
- [ ] 设计指纹生成算法（基于关键字段组合）
- [ ] 实现多种指纹策略（严格、宽松、自定义）
- [ ] 添加指纹缓存机制，提升性能

#### 1.2 实时去重处理
```python
# 文件：src/services/deduplication_engine.py  
class DeduplicationEngine:
    async def process_alarm(self, alarm_data: Dict) -> Tuple[bool, Optional[int]]:
        """处理告警去重，返回(是否重复, 原始告警ID)"""
```

**开发任务：**
- [ ] 集成到告警收集流程（collector.py）
- [ ] 实现重复告警计数更新
- [ ] 添加去重时间窗口配置
- [ ] 支持去重策略配置（时间范围、相似度阈值）

#### 1.3 相似度计算
```python
class SimilarityCalculator:
    def calculate_similarity(self, alarm1: Dict, alarm2: Dict) -> float:
        """计算告警相似度 (0-1)"""
        # 文本相似度：标题、描述
        # 标签相似度：tags, host, service
        # 时间相关性：发生时间窗口
```

**开发任务：**
- [ ] 文本相似度算法（编辑距离、余弦相似度）
- [ ] 标签匹配算法
- [ ] 综合相似度评分机制

### 阶段二：告警降噪功能 (优先级：中)

#### 2.1 降噪规则引擎
```python
# 文件：src/services/noise_reduction_engine.py
class NoiseReductionEngine:
    async def apply_noise_rules(self, alarms: List[Dict]) -> List[Dict]:
        """应用降噪规则过滤告警"""
```

**降噪策略：**
- **频率限制**：同类告警在时间窗口内限制数量
- **抑制规则**：高优先级告警抑制低优先级
- **静默时间**：维护时间段自动静默
- **阈值过滤**：基于告警频次自动过滤

**开发任务：**
- [ ] 设计降噪规则数据模型
- [ ] 实现规则匹配引擎
- [ ] 添加规则管理界面
- [ ] 支持规则优先级和冲突处理

#### 2.2 时间窗口聚合
```python
# 文件：src/services/aggregation_engine.py
class AlarmAggregation:
    async def aggregate_by_window(self, 
                                window_size: timedelta,
                                group_by: List[str]) -> List[Dict]:
        """按时间窗口聚合告警"""
```

**聚合维度：**
- 按主机聚合
- 按服务聚合  
- 按告警类型聚合
- 自定义标签聚合

**开发任务：**
- [ ] 滑动时间窗口实现
- [ ] 多维度聚合算法
- [ ] 聚合结果存储和查询
- [ ] 聚合规则配置管理

#### 2.3 告警抑制机制
```python
class SuppressionEngine:
    async def check_suppression(self, alarm: Dict) -> bool:
        """检查告警是否应被抑制"""
        # 依赖关系抑制：父服务故障时抑制子服务告警
        # 维护窗口抑制：计划维护时间自动抑制
        # 手动抑制：用户手动设置抑制规则
```

**开发任务：**
- [ ] 依赖关系建模和配置
- [ ] 维护窗口管理
- [ ] 抑制规则配置界面
- [ ] 抑制历史记录和审计

### 阶段三：订阅管理功能 (优先级：中)

#### 3.1 用户订阅数据模型扩展
```sql
-- 扩展现有 UserSubscription 表
ALTER TABLE user_subscriptions ADD COLUMN notification_channels JSON;
ALTER TABLE user_subscriptions ADD COLUMN frequency_limit INT DEFAULT 0;
ALTER TABLE user_subscriptions ADD COLUMN quiet_hours JSON;
```

**字段说明：**
- `notification_channels`: 通知渠道配置（邮件、短信、钉钉等）
- `frequency_limit`: 频率限制（每小时最大通知数）
- `quiet_hours`: 免打扰时间段

#### 3.2 订阅规则匹配引擎增强
```python
# 增强现有 subscription_engine.py
class SubscriptionMatcher:
    async def match_subscribers(self, alarm: Dict) -> List[UserSubscription]:
        """匹配告警的订阅用户"""
        # 支持复杂条件匹配：
        # - 多字段组合条件
        # - 正则表达式匹配
        # - 标签键值对匹配
        # - 时间范围限制
```

**开发任务：**
- [ ] 复杂规则表达式解析
- [ ] 规则性能优化（索引、缓存）
- [ ] 规则冲突检测和解决
- [ ] 规则测试和调试工具

#### 3.3 订阅管理前端界面
```vue
<!-- 文件：frontend/src/views/SubscriptionManagement/index.vue -->
<template>
  <div class="subscription-management">
    <!-- 我的订阅列表 -->
    <!-- 订阅规则编辑器 -->
    <!-- 通知渠道配置 -->
    <!-- 订阅测试工具 -->
  </div>
</template>
```

**界面功能：**
- 订阅规则可视化编辑器
- 多通道通知配置
- 订阅效果预览和测试
- 订阅历史和统计

**开发任务：**
- [ ] 规则编辑器组件（支持拖拽、可视化）
- [ ] 通知渠道配置界面
- [ ] 订阅测试功能
- [ ] 订阅统计和分析

## 🛠️ 技术实现细节

### 数据库设计

#### 去重相关表
```sql
-- 告警指纹表
CREATE TABLE alarm_fingerprints (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    fingerprint VARCHAR(64) UNIQUE NOT NULL,
    first_alarm_id BIGINT NOT NULL,
    alarm_count INT DEFAULT 1,
    last_occurrence DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fingerprint (fingerprint),
    INDEX idx_last_occurrence (last_occurrence)
);

-- 去重配置表  
CREATE TABLE deduplication_configs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    fingerprint_fields JSON NOT NULL,
    time_window_minutes INT DEFAULT 60,
    similarity_threshold DECIMAL(3,2) DEFAULT 0.80,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 降噪相关表
```sql
-- 降噪规则表
CREATE TABLE noise_reduction_rules (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    rule_type ENUM('frequency_limit', 'suppression', 'silence') NOT NULL,
    conditions JSON NOT NULL,
    actions JSON NOT NULL,
    priority INT DEFAULT 0,
    enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 告警抑制记录表
CREATE TABLE alarm_suppressions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    alarm_id BIGINT NOT NULL,
    rule_id INT NOT NULL,
    suppressed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    INDEX idx_alarm_id (alarm_id),
    INDEX idx_suppressed_at (suppressed_at)
);
```

### 性能优化策略

#### 1. 缓存策略
```python
# Redis 缓存结构
cache_structure = {
    "alarm_fingerprints": "hash",      # 指纹缓存，TTL: 1小时
    "dedup_results": "hash",           # 去重结果，TTL: 30分钟  
    "suppression_rules": "list",       # 抑制规则，TTL: 10分钟
    "user_subscriptions": "hash",      # 用户订阅，TTL: 5分钟
}
```

#### 2. 异步处理
```python
# 使用消息队列异步处理
async def process_alarm_async(alarm_data: Dict):
    """异步处理告警（去重、降噪、订阅匹配）"""
    # 1. 后台去重处理
    # 2. 异步降噪分析  
    # 3. 订阅匹配和通知
```

#### 3. 批处理优化
```python
# 批量处理提升性能
async def batch_process_alarms(alarms: List[Dict], batch_size: int = 100):
    """批量处理告警，减少数据库连接"""
```

## 📝 开发时间估算

| 阶段 | 功能模块 | 预估时间 | 优先级 |
|------|----------|----------|--------|
| 阶段一 | 告警指纹生成 | 2-3天 | 高 |
| 阶段一 | 实时去重处理 | 3-4天 | 高 |
| 阶段一 | 相似度计算 | 2-3天 | 高 |
| 阶段二 | 降噪规则引擎 | 4-5天 | 中 |
| 阶段二 | 时间窗口聚合 | 3-4天 | 中 |
| 阶段二 | 告警抑制机制 | 3-4天 | 中 |
| 阶段三 | 数据模型扩展 | 1-2天 | 中 |
| 阶段三 | 订阅匹配引擎 | 3-4天 | 中 |
| 阶段三 | 前端订阅界面 | 4-5天 | 低 |
| **总计** | | **25-34天** | |

## 🧪 测试计划

### 单元测试
- 指纹生成算法测试
- 相似度计算测试  
- 规则匹配引擎测试
- 订阅匹配逻辑测试

### 集成测试
- 端到端告警处理流程
- 去重降噪效果验证
- 订阅通知准确性测试

### 性能测试
- 高并发告警处理
- 大量规则匹配性能
- 数据库查询性能

### 压力测试  
- 告警风暴场景测试
- 系统资源占用监控
- 故障恢复能力测试

## 🎯 成功指标

### 功能指标
- 去重准确率 > 95%
- 降噪效果减少告警量 30-50%
- 订阅匹配延迟 < 100ms

### 性能指标
- 单机处理能力 > 1000 告警/秒
- 去重处理延迟 < 50ms
- 内存使用稳定，无明显泄漏

### 用户体验指标
- 误报率 < 5%
- 漏报率 < 1%  
- 用户满意度 > 90%

## 🔄 迭代计划

### Sprint 1 (1周): 告警去重核心功能
- 指纹生成算法
- 基础去重逻辑
- 集成到现有流程

### Sprint 2 (1周): 去重功能完善  
- 相似度计算
- 去重配置管理
- 性能优化

### Sprint 3 (1-2周): 降噪功能开发
- 降噪规则引擎
- 时间窗口聚合
- 抑制机制

### Sprint 4 (1周): 订阅功能增强
- 订阅引擎完善
- 前端界面开发
- 整体测试优化

## 📚 参考资料

- [Prometheus Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [ElasticSearch Watcher](https://www.elastic.co/guide/en/elasticsearch/reference/current/watcher-api.html)
- [PagerDuty Event Intelligence](https://www.pagerduty.com/platform/event-intelligence/)
- [Grafana Alerting](https://grafana.com/docs/grafana/latest/alerting/)