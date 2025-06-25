"""
智能告警关联分析引擎
基于图神经网络和机器学习的多维关联分析
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict, Counter
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from src.models.alarm import AlarmTable, AlarmSeverity, AlarmStatus
from src.core.database import async_session_maker
from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CorrelationRule:
    """关联规则定义"""
    name: str
    conditions: Dict[str, Any]
    weight: float
    time_window: int  # 秒
    max_distance: int = 1  # 图中最大距离


@dataclass
class AlarmNode:
    """告警节点"""
    alarm_id: int
    timestamp: datetime
    host: str
    service: str
    severity: str
    title: str
    description: str
    tags: Dict[str, Any]
    features: np.ndarray = None


@dataclass
class CorrelationResult:
    """关联分析结果"""
    primary_alarm_id: int
    related_alarms: List[int]
    correlation_type: str
    correlation_score: float
    root_cause_probability: float
    recommended_actions: List[str]


class SmartCorrelationEngine:
    """智能关联分析引擎"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # 文本向量化器
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        # 关联规则
        self.correlation_rules = self._load_correlation_rules()
        
        # 图神经网络 (简化版本)
        self.alarm_graph = nx.DiGraph()
        
        # 缓存
        self.feature_cache = {}
        self.correlation_cache = {}
        
    def _load_correlation_rules(self) -> List[CorrelationRule]:
        """加载关联规则"""
        return [
            # 主机级别关联
            CorrelationRule(
                name="host_cascade",
                conditions={"same_host": True},
                weight=0.8,
                time_window=300  # 5分钟
            ),
            
            # 服务级别关联
            CorrelationRule(
                name="service_dependency",
                conditions={"related_services": True},
                weight=0.7,
                time_window=600  # 10分钟
            ),
            
            # 网络级别关联
            CorrelationRule(
                name="network_segment",
                conditions={"same_network": True},
                weight=0.6,
                time_window=180  # 3分钟
            ),
            
            # 时间模式关联
            CorrelationRule(
                name="temporal_pattern",
                conditions={"time_proximity": True},
                weight=0.5,
                time_window=120  # 2分钟
            ),
            
            # 文本相似性关联
            CorrelationRule(
                name="content_similarity",
                conditions={"text_similarity": 0.7},
                weight=0.6,
                time_window=900  # 15分钟
            )
        ]
    
    async def analyze_correlations(
        self, 
        time_window: int = 3600,
        min_correlation_score: float = 0.5
    ) -> List[CorrelationResult]:
        """执行关联分析"""
        try:
            # 获取时间窗口内的活跃告警
            alarms = await self._get_active_alarms(time_window)
            
            if len(alarms) < 2:
                return []
            
            self.logger.info(f"开始分析 {len(alarms)} 个告警的关联关系")
            
            # 构建告警节点
            alarm_nodes = await self._build_alarm_nodes(alarms)
            
            # 构建关联图
            correlation_graph = await self._build_correlation_graph(alarm_nodes)
            
            # 识别关联模式
            correlations = await self._identify_correlations(
                correlation_graph, 
                min_correlation_score
            )
            
            # 根因分析
            enhanced_correlations = await self._perform_root_cause_analysis(correlations)
            
            # 生成推荐动作
            final_results = await self._generate_recommendations(enhanced_correlations)
            
            self.logger.info(f"发现 {len(final_results)} 个关联模式")
            return final_results
            
        except Exception as e:
            self.logger.error(f"关联分析失败: {str(e)}")
            return []
    
    async def _get_active_alarms(self, time_window: int) -> List[AlarmTable]:
        """获取活跃告警"""
        start_time = datetime.utcnow() - timedelta(seconds=time_window)
        
        async with async_session_maker() as session:
            result = await session.execute(
                select(AlarmTable).where(
                    and_(
                        AlarmTable.created_at >= start_time,
                        AlarmTable.status.in_([AlarmStatus.ACTIVE, AlarmStatus.ACKNOWLEDGED])
                    )
                ).order_by(AlarmTable.created_at.desc())
            )
            return result.scalars().all()
    
    async def _build_alarm_nodes(self, alarms: List[AlarmTable]) -> List[AlarmNode]:
        """构建告警节点"""
        nodes = []
        
        # 准备文本数据用于向量化
        texts = [f"{alarm.title} {alarm.description or ''}" for alarm in alarms]
        
        # 生成TF-IDF特征
        try:
            if len(texts) > 1:
                tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
                features = tfidf_matrix.toarray()
            else:
                features = np.zeros((1, 100))  # 默认特征维度
        except Exception as e:
            self.logger.warning(f"TF-IDF向量化失败: {str(e)}")
            features = np.zeros((len(alarms), 100))
        
        # 创建告警节点
        for i, alarm in enumerate(alarms):
            node = AlarmNode(
                alarm_id=alarm.id,
                timestamp=alarm.created_at,
                host=alarm.host or "",
                service=alarm.service or "",
                severity=alarm.severity,
                title=alarm.title,
                description=alarm.description or "",
                tags=alarm.tags or {},
                features=features[i] if i < len(features) else np.zeros(100)
            )
            nodes.append(node)
        
        return nodes
    
    async def _build_correlation_graph(self, nodes: List[AlarmNode]) -> nx.DiGraph:
        """构建关联图"""
        graph = nx.DiGraph()
        
        # 添加节点
        for node in nodes:
            graph.add_node(
                node.alarm_id,
                timestamp=node.timestamp,
                host=node.host,
                service=node.service,
                severity=node.severity,
                features=node.features
            )
        
        # 添加边 (关联关系)
        for i, node1 in enumerate(nodes):
            for j, node2 in enumerate(nodes):
                if i != j:
                    correlation_score = await self._calculate_correlation_score(node1, node2)
                    
                    if correlation_score > 0.3:  # 阈值
                        graph.add_edge(
                            node1.alarm_id,
                            node2.alarm_id,
                            weight=correlation_score,
                            correlation_type=self._determine_correlation_type(node1, node2)
                        )
        
        return graph
    
    async def _calculate_correlation_score(self, node1: AlarmNode, node2: AlarmNode) -> float:
        """计算两个告警节点的关联得分"""
        total_score = 0.0
        total_weight = 0.0
        
        for rule in self.correlation_rules:
            if self._rule_matches(node1, node2, rule):
                score = self._apply_rule(node1, node2, rule)
                total_score += score * rule.weight
                total_weight += rule.weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _rule_matches(self, node1: AlarmNode, node2: AlarmNode, rule: CorrelationRule) -> bool:
        """检查规则是否匹配"""
        # 时间窗口检查
        time_diff = abs((node1.timestamp - node2.timestamp).total_seconds())
        if time_diff > rule.time_window:
            return False
        
        conditions = rule.conditions
        
        # 同主机检查
        if conditions.get("same_host") and node1.host != node2.host:
            return False
        
        # 相关服务检查
        if conditions.get("related_services"):
            if not self._are_services_related(node1.service, node2.service):
                return False
        
        # 同网络段检查
        if conditions.get("same_network"):
            if not self._same_network_segment(node1.host, node2.host):
                return False
        
        return True
    
    def _apply_rule(self, node1: AlarmNode, node2: AlarmNode, rule: CorrelationRule) -> float:
        """应用规则计算得分"""
        conditions = rule.conditions
        
        if rule.name == "host_cascade":
            return 1.0 if node1.host == node2.host else 0.0
        
        elif rule.name == "service_dependency":
            return self._service_dependency_score(node1.service, node2.service)
        
        elif rule.name == "network_segment":
            return 0.8 if self._same_network_segment(node1.host, node2.host) else 0.0
        
        elif rule.name == "temporal_pattern":
            time_diff = abs((node1.timestamp - node2.timestamp).total_seconds())
            return max(0, 1.0 - time_diff / rule.time_window)
        
        elif rule.name == "content_similarity":
            if node1.features is not None and node2.features is not None:
                similarity = cosine_similarity(
                    node1.features.reshape(1, -1),
                    node2.features.reshape(1, -1)
                )[0][0]
                threshold = conditions.get("text_similarity", 0.7)
                return similarity if similarity >= threshold else 0.0
        
        return 0.0
    
    def _determine_correlation_type(self, node1: AlarmNode, node2: AlarmNode) -> str:
        """确定关联类型"""
        if node1.host == node2.host:
            return "host_level"
        elif self._are_services_related(node1.service, node2.service):
            return "service_level"
        elif self._same_network_segment(node1.host, node2.host):
            return "network_level"
        else:
            return "temporal"
    
    def _are_services_related(self, service1: str, service2: str) -> bool:
        """判断服务是否相关"""
        # 简化的服务依赖关系
        service_dependencies = {
            "web": ["database", "cache", "api"],
            "api": ["database", "cache"],
            "database": ["storage"],
            "cache": ["database"],
            "load-balancer": ["web", "api"]
        }
        
        return (service2 in service_dependencies.get(service1, []) or
                service1 in service_dependencies.get(service2, []))
    
    def _same_network_segment(self, host1: str, host2: str) -> bool:
        """判断是否在同一网络段"""
        # 简化的网络段判断
        if not host1 or not host2:
            return False
        
        # 假设主机名格式为 prefix-subnet-number
        try:
            parts1 = host1.split('-')
            parts2 = host2.split('-')
            
            if len(parts1) >= 2 and len(parts2) >= 2:
                return parts1[0] == parts2[0] and parts1[1] == parts2[1]
        except:
            pass
        
        return False
    
    def _service_dependency_score(self, service1: str, service2: str) -> float:
        """计算服务依赖得分"""
        if self._are_services_related(service1, service2):
            # 基于服务类型的权重
            weights = {
                ("web", "database"): 0.9,
                ("api", "database"): 0.8,
                ("web", "cache"): 0.7,
                ("load-balancer", "web"): 0.9
            }
            
            key = (service1, service2)
            reverse_key = (service2, service1)
            
            return weights.get(key, weights.get(reverse_key, 0.6))
        
        return 0.0
    
    async def _identify_correlations(
        self, 
        graph: nx.DiGraph, 
        min_score: float
    ) -> List[CorrelationResult]:
        """识别关联模式"""
        correlations = []
        
        # 使用社区检测算法识别关联集群
        try:
            # 转换为无向图进行社区检测
            undirected_graph = graph.to_undirected()
            
            # 使用连通分量作为简化的社区检测
            communities = list(nx.connected_components(undirected_graph))
            
            for community in communities:
                if len(community) > 1:
                    # 为每个社区创建关联结果
                    correlation = await self._analyze_community(graph, community)
                    if correlation and correlation.correlation_score >= min_score:
                        correlations.append(correlation)
        
        except Exception as e:
            self.logger.warning(f"社区检测失败: {str(e)}")
        
        return correlations
    
    async def _analyze_community(self, graph: nx.DiGraph, community: Set[int]) -> CorrelationResult:
        """分析社区的关联模式"""
        community_list = list(community)
        
        # 找到最早的告警作为主要告警
        timestamps = []
        for node_id in community_list:
            timestamps.append((node_id, graph.nodes[node_id]['timestamp']))
        
        timestamps.sort(key=lambda x: x[1])
        primary_alarm_id = timestamps[0][0]
        related_alarms = [alarm_id for alarm_id, _ in timestamps[1:]]
        
        # 计算整体关联得分
        total_score = 0.0
        edge_count = 0
        
        for node1 in community_list:
            for node2 in community_list:
                if node1 != node2 and graph.has_edge(node1, node2):
                    total_score += graph[node1][node2]['weight']
                    edge_count += 1
        
        avg_score = total_score / edge_count if edge_count > 0 else 0.0
        
        # 确定关联类型
        correlation_types = []
        for node1 in community_list:
            for node2 in community_list:
                if node1 != node2 and graph.has_edge(node1, node2):
                    correlation_types.append(graph[node1][node2]['correlation_type'])
        
        most_common_type = Counter(correlation_types).most_common(1)[0][0] if correlation_types else "unknown"
        
        return CorrelationResult(
            primary_alarm_id=primary_alarm_id,
            related_alarms=related_alarms,
            correlation_type=most_common_type,
            correlation_score=avg_score,
            root_cause_probability=0.0,  # 将在根因分析中计算
            recommended_actions=[]  # 将在推荐生成中填充
        )
    
    async def _perform_root_cause_analysis(
        self, 
        correlations: List[CorrelationResult]
    ) -> List[CorrelationResult]:
        """执行根因分析"""
        for correlation in correlations:
            # 基于关联类型和严重程度计算根因概率
            async with async_session_maker() as session:
                # 获取主要告警信息
                result = await session.execute(
                    select(AlarmTable).where(AlarmTable.id == correlation.primary_alarm_id)
                )
                primary_alarm = result.scalar_one_or_none()
                
                if primary_alarm:
                    # 基于多个因素计算根因概率
                    probability = 0.5  # 基础概率
                    
                    # 严重程度权重
                    severity_weights = {
                        AlarmSeverity.CRITICAL: 0.3,
                        AlarmSeverity.HIGH: 0.2,
                        AlarmSeverity.MEDIUM: 0.1,
                        AlarmSeverity.LOW: 0.05,
                        AlarmSeverity.INFO: 0.0
                    }
                    probability += severity_weights.get(primary_alarm.severity, 0.0)
                    
                    # 关联类型权重
                    type_weights = {
                        "host_level": 0.2,
                        "service_level": 0.15,
                        "network_level": 0.1,
                        "temporal": 0.05
                    }
                    probability += type_weights.get(correlation.correlation_type, 0.0)
                    
                    # 时间因素 (越早发生概率越高)
                    if len(correlation.related_alarms) > 0:
                        probability += 0.1
                    
                    correlation.root_cause_probability = min(probability, 1.0)
        
        return correlations
    
    async def _generate_recommendations(
        self, 
        correlations: List[CorrelationResult]
    ) -> List[CorrelationResult]:
        """生成推荐动作"""
        for correlation in correlations:
            recommendations = []
            
            if correlation.correlation_type == "host_level":
                recommendations.extend([
                    "检查主机资源使用情况",
                    "验证主机网络连接",
                    "检查主机系统日志",
                    "考虑主机重启或迁移"
                ])
            
            elif correlation.correlation_type == "service_level":
                recommendations.extend([
                    "检查服务依赖关系",
                    "验证服务配置",
                    "重启相关服务",
                    "检查服务间通信"
                ])
            
            elif correlation.correlation_type == "network_level":
                recommendations.extend([
                    "检查网络设备状态",
                    "验证网络配置",
                    "检查防火墙规则",
                    "测试网络连通性"
                ])
            
            else:
                recommendations.extend([
                    "分析告警时间模式",
                    "检查系统负载变化",
                    "查看监控指标趋势",
                    "联系相关运维人员"
                ])
            
            # 基于根因概率添加特定建议
            if correlation.root_cause_probability > 0.7:
                recommendations.insert(0, "高概率根因告警，优先处理")
            elif correlation.root_cause_probability > 0.5:
                recommendations.insert(0, "可能的根因告警，重点关注")
            
            correlation.recommended_actions = recommendations
        
        return correlations


# 全局实例
correlation_engine = SmartCorrelationEngine()