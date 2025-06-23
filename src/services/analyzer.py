"""
告警分析引擎
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select, update, func, and_, case

from src.core.config import settings
from src.core.database import async_session_maker
from src.models.alarm import AlarmTable, AlarmStatus, AlarmSeverity

logger = logging.getLogger(__name__)


class AlarmAnalyzer:
    def __init__(self):
        self.is_running = False
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.analysis_interval = 60
        
    async def start(self):
        if not settings.ANALYZER_ENABLED:
            logger.info("告警分析器已禁用")
            return
            
        self.is_running = True
        asyncio.create_task(self._analysis_worker())
        logger.info("告警分析器启动成功")
        
    async def stop(self):
        self.is_running = False
        logger.info("告警分析器已停止")
        
    async def _analysis_worker(self):
        while self.is_running:
            try:
                await self._analyze_duplicates()
                await self._analyze_correlations()
                await self._analyze_patterns()
                await self._auto_resolve()
                
                await asyncio.sleep(self.analysis_interval)
            except Exception as e:
                logger.error(f"分析工作器错误: {e}")
                await asyncio.sleep(10)
                
    async def _analyze_duplicates(self):
        """分析重复告警"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(AlarmTable).where(
                        AlarmTable.status == AlarmStatus.ACTIVE,
                        AlarmTable.is_duplicate == False
                    ).order_by(AlarmTable.created_at.desc()).limit(100)
                )
                alarms = result.scalars().all()
                
                if len(alarms) < 2:
                    return
                    
                texts = [f"{alarm.title} {alarm.description or ''}" for alarm in alarms]
                
                try:
                    tfidf_matrix = self.vectorizer.fit_transform(texts)
                    similarity_matrix = cosine_similarity(tfidf_matrix)
                    
                    for i, alarm1 in enumerate(alarms):
                        for j, alarm2 in enumerate(alarms[i+1:], i+1):
                            similarity = similarity_matrix[i][j]
                            
                            if similarity > settings.DUPLICATE_THRESHOLD:
                                if alarm1.created_at < alarm2.created_at:
                                    duplicate_alarm = alarm2
                                    original_alarm = alarm1
                                else:
                                    duplicate_alarm = alarm1
                                    original_alarm = alarm2
                                    
                                duplicate_alarm.is_duplicate = True
                                duplicate_alarm.similarity_score = similarity
                                duplicate_alarm.parent_alarm_id = original_alarm.id
                                duplicate_alarm.status = AlarmStatus.SUPPRESSED
                                
                                original_alarm.count += duplicate_alarm.count
                                
                    await session.commit()
                    logger.info("重复告警分析完成")
                    
                except Exception as e:
                    logger.error(f"文本向量化失败: {e}")
                    
            except Exception as e:
                await session.rollback()
                logger.error(f"重复告警分析失败: {e}")
                
    async def _analyze_correlations(self):
        """分析告警关联"""
        async with async_session_maker() as session:
            try:
                time_window = datetime.utcnow() - timedelta(seconds=settings.CORRELATION_WINDOW)
                
                result = await session.execute(
                    select(AlarmTable).where(
                        AlarmTable.status == AlarmStatus.ACTIVE,
                        AlarmTable.created_at >= time_window
                    ).order_by(AlarmTable.created_at.desc())
                )
                alarms = result.scalars().all()
                
                correlations = self._find_correlations(alarms)
                
                for correlation_id, alarm_ids in correlations.items():
                    for alarm_id in alarm_ids:
                        alarm = next((a for a in alarms if a.id == alarm_id), None)
                        if alarm:
                            alarm.correlation_id = correlation_id
                            
                await session.commit()
                logger.info(f"发现 {len(correlations)} 个告警关联")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"告警关联分析失败: {e}")
                
    def _find_correlations(self, alarms: List[AlarmTable]) -> Dict[str, List[int]]:
        """查找告警关联"""
        correlations = defaultdict(list)
        
        host_groups = defaultdict(list)
        service_groups = defaultdict(list)
        
        for alarm in alarms:
            if alarm.host:
                host_groups[alarm.host].append(alarm.id)
            if alarm.service:
                service_groups[alarm.service].append(alarm.id)
                
        correlation_id = 1
        for host, alarm_ids in host_groups.items():
            if len(alarm_ids) > 1:
                correlations[f"host_{correlation_id}"] = alarm_ids
                correlation_id += 1
                
        for service, alarm_ids in service_groups.items():
            if len(alarm_ids) > 1:
                correlations[f"service_{correlation_id}"] = alarm_ids
                correlation_id += 1
                
        return dict(correlations)
        
    async def _analyze_patterns(self):
        """分析告警模式"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(
                        AlarmTable.source,
                        AlarmTable.severity,
                        func.count(AlarmTable.id).label('count'),
                        func.avg(AlarmTable.count).label('avg_count')
                    ).where(
                        AlarmTable.created_at >= datetime.utcnow() - timedelta(hours=24)
                    ).group_by(AlarmTable.source, AlarmTable.severity)
                )
                
                patterns = result.all()
                
                for pattern in patterns:
                    if pattern.count > 10 and pattern.avg_count > 5:
                        logger.warning(
                            f"检测到告警模式: {pattern.source} - {pattern.severity}, "
                            f"数量: {pattern.count}, 平均重复: {pattern.avg_count}"
                        )
                        
            except Exception as e:
                logger.error(f"模式分析失败: {e}")
                
    async def _auto_resolve(self):
        """自动解决告警"""
        async with async_session_maker() as session:
            try:
                auto_resolve_time = datetime.utcnow() - timedelta(hours=24)
                
                result = await session.execute(
                    select(AlarmTable).where(
                        AlarmTable.status == AlarmStatus.ACTIVE,
                        AlarmTable.severity.in_([AlarmSeverity.LOW, AlarmSeverity.INFO]),
                        AlarmTable.last_occurrence < auto_resolve_time
                    )
                )
                
                alarms = result.scalars().all()
                
                for alarm in alarms:
                    alarm.status = AlarmStatus.RESOLVED
                    alarm.resolved_at = datetime.utcnow()
                    
                await session.commit()
                
                if alarms:
                    logger.info(f"自动解决了 {len(alarms)} 个告警")
                    
            except Exception as e:
                await session.rollback()
                logger.error(f"自动解决告警失败: {e}")
                
    async def get_analysis_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(
                        func.count(AlarmTable.id).label('total'),
                        func.sum(case([(AlarmTable.is_duplicate == True, 1)], else_=0)).label('duplicates'),
                        func.count(func.distinct(AlarmTable.correlation_id)).label('correlations')
                    ).where(
                        AlarmTable.created_at >= datetime.utcnow() - timedelta(hours=24)
                    )
                )
                
                stats = result.first()
                
                return {
                    "total_analyzed": stats.total or 0,
                    "duplicates_found": stats.duplicates or 0,
                    "correlations_found": stats.correlations or 0,
                    "is_running": self.is_running
                }
                
            except Exception as e:
                logger.error(f"获取分析摘要失败: {e}")
                return {
                    "total_analyzed": 0,
                    "duplicates_found": 0,
                    "correlations_found": 0,
                    "is_running": self.is_running
                }