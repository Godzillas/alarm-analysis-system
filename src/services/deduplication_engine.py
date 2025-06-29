"""
告警去重引擎
基于指纹和相似度算法实现智能告警去重
"""

import hashlib
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging
import re
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from sqlalchemy import select, update, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.core.database import async_session_maker
from src.core.config import settings
from src.models.alarm import AlarmTable
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FingerprintStrategy(Enum):
    """指纹生成策略"""
    STRICT = "strict"          # 严格模式：所有关键字段完全匹配
    NORMAL = "normal"          # 普通模式：核心字段匹配 + 模糊匹配
    LOOSE = "loose"            # 宽松模式：主要字段匹配，忽略细节差异


@dataclass
class DeduplicationConfig:
    """去重配置"""
    strategy: FingerprintStrategy = FingerprintStrategy.NORMAL
    time_window_minutes: int = 60           # 时间窗口（分钟）
    similarity_threshold: float = 0.85      # 相似度阈值
    enabled: bool = True
    custom_fields: List[str] = None         # 自定义指纹字段
    exclude_fields: List[str] = None        # 排除字段


class AlarmFingerprint:
    """告警指纹生成器"""
    
    def __init__(self, strategy: FingerprintStrategy = FingerprintStrategy.NORMAL):
        self.strategy = strategy
        
        # 不同策略的关键字段配置
        self.field_configs = {
            FingerprintStrategy.STRICT: {
                'required': ['title', 'host', 'service', 'severity'],
                'optional': ['environment', 'category'],
                'normalize': False
            },
            FingerprintStrategy.NORMAL: {
                'required': ['title', 'host', 'service'],
                'optional': ['environment'],
                'normalize': True
            },
            FingerprintStrategy.LOOSE: {
                'required': ['title', 'service'],
                'optional': ['host'],
                'normalize': True
            }
        }
    
    def generate_fingerprint(self, alarm_data: Dict[str, Any], 
                           custom_fields: Optional[List[str]] = None) -> str:
        """生成告警指纹"""
        try:
            config = self.field_configs[self.strategy]
            
            # 使用自定义字段或默认字段
            if custom_fields:
                fields_to_use = custom_fields
            else:
                fields_to_use = config['required'] + config['optional']
            
            # 提取指纹数据
            fingerprint_data = {}
            
            for field in fields_to_use:
                value = alarm_data.get(field, '')
                if value:
                    if config.get('normalize', False):
                        value = self._normalize_value(field, value)
                    fingerprint_data[field] = value
            
            # 处理标签数据
            tags = alarm_data.get('tags', {})
            if tags and isinstance(tags, dict):
                # 只包含重要的标签
                important_tags = self._extract_important_tags(tags)
                if important_tags:
                    fingerprint_data['tags'] = important_tags
            
            # 生成哈希
            fingerprint_str = json.dumps(fingerprint_data, sort_keys=True, ensure_ascii=False)
            return hashlib.sha256(fingerprint_str.encode('utf-8')).hexdigest()[:16]
            
        except Exception as e:
            logger.error(f"生成指纹失败: {e}")
            # 回退到基础指纹
            fallback_data = f"{alarm_data.get('title', '')}-{alarm_data.get('service', '')}"
            return hashlib.md5(fallback_data.encode('utf-8')).hexdigest()[:16]
    
    def _normalize_value(self, field: str, value: str) -> str:
        """标准化字段值"""
        if not isinstance(value, str):
            value = str(value)
        
        # 基础清理
        value = value.strip().lower()
        
        # 字段特定的标准化
        if field == 'title':
            # 移除时间戳、数字等变化信息
            value = re.sub(r'\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}', '<timestamp>', value)
            value = re.sub(r'\d+\.?\d*%', '<percentage>', value)
            value = re.sub(r'\d+\.?\d*\s?(mb|gb|kb|bytes?)', '<size>', value)
            value = re.sub(r'\d+\.?\d*\s?(ms|sec|min|hour)s?', '<duration>', value)
        
        elif field == 'host':
            # 标准化主机名
            value = re.sub(r'\.local$', '', value)
            value = re.sub(r':\d+$', '', value)  # 移除端口号
        
        elif field == 'service':
            # 标准化服务名
            value = re.sub(r'[-_][a-zA-Z0-9.]+', '', value)  # 移除版本号或后缀
        
        return value
    
    def _extract_important_tags(self, tags: Dict) -> Dict:
        """提取重要标签"""
        important_keys = {
            'alertname', 'job', 'instance', 'cluster', 'namespace',
            'pod', 'container', 'node', 'deployment', 'service_name'
        }
        
        return {k: v for k, v in tags.items() 
                if k.lower() in important_keys and v}


class SimilarityCalculator:
    """相似度计算器"""
    
    def calculate_similarity(self, alarm1: Dict, alarm2: Dict) -> float:
        """计算两个告警的相似度 (0-1)"""
        try:
            # 文本相似度权重
            weights = {
                'title': 0.4,
                'description': 0.2, 
                'host': 0.15,
                'service': 0.15,
                'tags': 0.1
            }
            
            total_score = 0.0
            total_weight = 0.0
            
            for field, weight in weights.items():
                if field in alarm1 and field in alarm2:
                    if field == 'tags':
                        score = self._calculate_tags_similarity(
                            alarm1.get(field, {}), 
                            alarm2.get(field, {})
                        )
                    else:
                        score = self._calculate_text_similarity(
                            str(alarm1.get(field, '')),
                            str(alarm2.get(field, ''))
                        )
                    
                    total_score += score * weight
                    total_weight += weight
            
            return total_score / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"计算相似度失败: {e}")
            return 0.0
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度 (TF-IDF + 余弦相似度)"""
        if not text1 or not text2:
            return 0.0
        
        if text1 == text2:
            return 1.0
        
        # 创建TF-IDF向量化器
        # 这里每次都重新创建，是为了简化，实际生产环境可能需要预训练或缓存
        vectorizer = TfidfVectorizer().fit([text1, text2])
        
        # 转换文本为TF-IDF向量
        tfidf_text1 = vectorizer.transform([text1])
        tfidf_text2 = vectorizer.transform([text2])
        
        # 计算余弦相似度
        # cosine_similarity返回一个矩阵，取[0][0]即为两个向量的相似度
        similarity = cosine_similarity(tfidf_text1, tfidf_text2)[0][0]
        
        return float(similarity)
    
    def _calculate_tags_similarity(self, tags1: Dict, tags2: Dict) -> float:
        """计算标签相似度"""
        if not tags1 and not tags2:
            return 1.0
        
        if not tags1 or not tags2:
            return 0.0
        
        # 计算共同标签的比例
        keys1 = set(tags1.keys())
        keys2 = set(tags2.keys())
        
        common_keys = keys1.intersection(keys2)
        if not common_keys:
            return 0.0
        
        # 计算共同标签中值相同的比例
        matching_values = sum(1 for key in common_keys 
                            if tags1[key] == tags2[key])
        
        return matching_values / len(common_keys)


class DeduplicationEngine:
    """告警去重引擎"""
    
    def __init__(self):
        self.config = DeduplicationConfig()
        self.fingerprint_generator = AlarmFingerprint(self.config.strategy)
        self.similarity_calculator = SimilarityCalculator()
        self.redis_client: Optional[redis.Redis] = None
        
    async def start(self):
        """启动去重引擎"""
        try:
            # 连接Redis
            if settings.REDIS_URL:
                self.redis_client = redis.from_url(settings.REDIS_URL)
                await self.redis_client.ping()
                logger.info("去重引擎Redis连接成功")
        except Exception as e:
            logger.warning(f"Redis连接失败，将使用数据库缓存: {e}")
            self.redis_client = None
    
    async def process_alarm(self, alarm_data: Dict[str, Any]) -> Tuple[bool, Optional[int]]:
        """处理告警去重
        返回: (是否为重复告警, 原始告警ID)
        """
        if not self.config.enabled:
            return False, None
        
        try:
            # 生成指纹
            fingerprint = self.fingerprint_generator.generate_fingerprint(alarm_data)
            
            # 查找相似告警
            similar_alarm = await self._find_similar_alarm(fingerprint, alarm_data)
            
            if similar_alarm:
                # 更新原始告警的计数和时间
                await self._update_original_alarm(similar_alarm['id'])
                
                # 缓存去重结果
                await self._cache_deduplication_result(fingerprint, similar_alarm['id'])
                
                logger.info(f"检测到重复告警，指纹: {fingerprint}, 原始ID: {similar_alarm['id']}")
                return True, similar_alarm['id']
            
            else:
                # 缓存新的指纹
                await self._cache_fingerprint(fingerprint, alarm_data)
                return False, None
                
        except Exception as e:
            logger.error(f"去重处理失败: {e}")
            return False, None
    
    async def _find_similar_alarm(self, fingerprint: str, 
                                alarm_data: Dict) -> Optional[Dict]:
        """查找相似告警"""
        # 首先检查精确指纹匹配
        cached_alarm = await self._get_cached_fingerprint(fingerprint)
        if cached_alarm:
            return cached_alarm
        
        # 数据库查询相似告警
        time_threshold = datetime.utcnow() - timedelta(
            minutes=self.config.time_window_minutes
        )
        
        async with async_session_maker() as session:
            # 查询时间窗口内的活跃告警
            query = select(AlarmTable).where(
                and_(
                    AlarmTable.created_at >= time_threshold,
                    AlarmTable.status == 'active',
                    AlarmTable.correlation_id.is_(None)  # 非重复告警
                )
            ).order_by(desc(AlarmTable.created_at)).limit(100)
            
            result = await session.execute(query)
            recent_alarms = result.scalars().all()
            
            # 计算相似度
            for alarm in recent_alarms:
                alarm_dict = {
                    'title': alarm.title,
                    'description': alarm.description,
                    'host': alarm.host,
                    'service': alarm.service,
                    'tags': alarm.tags or {}
                }
                
                similarity = self.similarity_calculator.calculate_similarity(
                    alarm_data, alarm_dict
                )
                
                if similarity >= self.config.similarity_threshold:
                    return {
                        'id': alarm.id,
                        'similarity': similarity,
                        'fingerprint': fingerprint
                    }
        
        return None
    
    async def _update_original_alarm(self, alarm_id: int):
        """更新原始告警的计数和时间"""
        async with async_session_maker() as session:
            query = update(AlarmTable).where(
                AlarmTable.id == alarm_id
            ).values(
                count=AlarmTable.count + 1,
                last_occurrence=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await session.execute(query)
            await session.commit()
    
    async def _cache_fingerprint(self, fingerprint: str, alarm_data: Dict):
        """缓存指纹信息"""
        if self.redis_client:
            try:
                cache_data = {
                    'fingerprint': fingerprint,
                    'created_at': datetime.utcnow().isoformat(),
                    'title': alarm_data.get('title', ''),
                    'service': alarm_data.get('service', '')
                }
                
                await self.redis_client.setex(
                    f"fingerprint:{fingerprint}",
                    self.config.time_window_minutes * 60,
                    json.dumps(cache_data)
                )
            except Exception as e:
                logger.warning(f"缓存指纹失败: {e}")
    
    async def _get_cached_fingerprint(self, fingerprint: str) -> Optional[Dict]:
        """获取缓存的指纹信息"""
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(f"fingerprint:{fingerprint}")
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"获取缓存指纹失败: {e}")
        return None
    
    async def _cache_deduplication_result(self, fingerprint: str, original_id: int):
        """缓存去重结果"""
        if self.redis_client:
            try:
                result_data = {
                    'original_id': original_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                await self.redis_client.setex(
                    f"dedup_result:{fingerprint}",
                    self.config.time_window_minutes * 60,
                    json.dumps(result_data)
                )
            except Exception as e:
                logger.warning(f"缓存去重结果失败: {e}")
    
    async def get_deduplication_stats(self) -> Dict[str, Any]:
        """获取去重统计信息"""
        try:
            async with async_session_maker() as session:
                # 获取最近24小时的统计
                time_threshold = datetime.utcnow() - timedelta(hours=24)
                
                # 总告警数
                total_query = select(func.count(AlarmTable.id)).where(
                    AlarmTable.created_at >= time_threshold
                )
                total_result = await session.execute(total_query)
                total_alarms = total_result.scalar() or 0
                
                # 重复告警数
                duplicate_query = select(func.count(AlarmTable.id)).where(
                    and_(
                        AlarmTable.created_at >= time_threshold,
                        AlarmTable.is_duplicate == True
                    )
                )
                duplicate_result = await session.execute(duplicate_query)
                duplicate_alarms = duplicate_result.scalar() or 0
                
                # 计算去重率
                dedup_rate = (duplicate_alarms / total_alarms * 100) if total_alarms > 0 else 0
                
                return {
                    'total_alarms': total_alarms,
                    'duplicate_alarms': duplicate_alarms,
                    'unique_alarms': total_alarms - duplicate_alarms,
                    'deduplication_rate': round(dedup_rate, 2),
                    'time_window': '24h',
                    'config': {
                        'strategy': self.config.strategy.value,
                        'similarity_threshold': self.config.similarity_threshold,
                        'time_window_minutes': self.config.time_window_minutes
                    }
                }
                
        except Exception as e:
            logger.error(f"获取去重统计失败: {e}")
            return {}
    
    async def update_config(self, new_config: DeduplicationConfig):
        """更新去重配置"""
        self.config = new_config
        self.fingerprint_generator = AlarmFingerprint(new_config.strategy)
        logger.info(f"去重配置已更新: {new_config}")


# 全局去重引擎实例
deduplication_engine = DeduplicationEngine()


async def initialize_deduplication_engine():
    """初始化去重引擎"""
    await deduplication_engine.start()
    logger.info("告警去重引擎初始化完成")


# 便捷函数
async def process_alarm_deduplication(alarm_data: Dict[str, Any]) -> Tuple[bool, Optional[int]]:
    """处理告警去重的便捷函数"""
    return await deduplication_engine.process_alarm(alarm_data)