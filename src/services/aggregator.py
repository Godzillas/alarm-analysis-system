"""
告警聚合分析系统
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict, Counter

from src.core.database import async_session_maker, engine
from src.models.alarm import AlarmTable, AlarmDistribution, User, UserSubscription
from src.utils.logger import get_logger
from src.utils.database import get_date_trunc_func, get_database_type_from_url
from src.core.config import settings

logger = get_logger(__name__)


class AlarmAggregator:
    def __init__(self):
        self.aggregation_cache: Dict[str, Dict] = {}
        self.trends_cache: Dict[str, List] = {}
        
    async def get_alarm_summary(self, time_range: str = "24h", system_id: Optional[int] = None) -> Dict[str, Any]:
        """获取告警汇总统计"""
        try:
            start_time = self._get_start_time(time_range)
            
            async with async_session_maker() as session:
                # 基础统计
                basic_stats = await self._get_basic_stats(session, start_time, system_id)
                
                # 按严重程度统计
                severity_stats = await self._get_severity_stats(session, start_time, system_id)
                
                # 按状态统计
                status_stats = await self._get_status_stats(session, start_time, system_id)
                
                # 按来源统计
                source_stats = await self._get_source_stats(session, start_time, system_id)
                
                # 按主机统计
                host_stats = await self._get_host_stats(session, start_time, system_id)
                
                # 按服务统计
                service_stats = await self._get_service_stats(session, start_time, system_id)
                
                return {
                    "time_range": time_range,
                    "start_time": start_time.isoformat(),
                    "basic": basic_stats,
                    "by_severity": severity_stats,
                    "by_status": status_stats,
                    "by_source": source_stats,
                    "by_host": host_stats,
                    "by_service": service_stats
                }
                
        except Exception as e:
            logger.error(f"Failed to get alarm summary: {str(e)}")
            return {}
            
    async def get_alarm_trends(self, time_range: str = "24h", interval: str = "1h", system_id: Optional[int] = None) -> Dict[str, Any]:
        """获取告警趋势数据"""
        try:
            start_time = self._get_start_time(time_range)
            cache_key = f"trends_{time_range}_{interval}"
            
            # 检查缓存
            if cache_key in self.trends_cache:
                cached_data = self.trends_cache[cache_key]
                if cached_data and datetime.fromisoformat(cached_data[0].get("cache_time", "")) > datetime.utcnow() - timedelta(minutes=5):
                    return cached_data[0]
                    
            async with async_session_maker() as session:
                # 时间序列数据
                timeline_data = await self._get_timeline_data(session, start_time, interval)
                
                # 严重程度趋势
                severity_trends = await self._get_severity_trends(session, start_time, interval)
                
                # 来源趋势
                source_trends = await self._get_source_trends(session, start_time, interval)
                
                result = {
                    "time_range": time_range,
                    "interval": interval,
                    "start_time": start_time.isoformat(),
                    "timeline": timeline_data,
                    "severity_trends": severity_trends,
                    "source_trends": source_trends,
                    "cache_time": datetime.utcnow().isoformat()
                }
                
                # 更新缓存
                self.trends_cache[cache_key] = [result]
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get alarm trends: {str(e)}")
            return {}
            
    async def get_top_alarms(self, time_range: str = "24h", limit: int = 10, system_id: Optional[int] = None) -> Dict[str, Any]:
        """获取TOP告警统计"""
        try:
            start_time = self._get_start_time(time_range)
            
            async with async_session_maker() as session:
                # 最频繁的告警
                frequent_alarms = await self._get_frequent_alarms(session, start_time, limit)
                
                # 最久未解决的告警
                longest_unresolved = await self._get_longest_unresolved(session, limit)
                
                # 最新的告警
                latest_alarms = await self._get_latest_alarms(session, limit)
                
                # 最严重的未解决告警
                critical_unresolved = await self._get_critical_unresolved(session, limit)
                
                return {
                    "time_range": time_range,
                    "frequent_alarms": frequent_alarms,
                    "longest_unresolved": longest_unresolved,
                    "latest_alarms": latest_alarms,
                    "critical_unresolved": critical_unresolved
                }
                
        except Exception as e:
            logger.error(f"Failed to get top alarms: {str(e)}")
            return {}
            
    async def get_distribution_stats(self, time_range: str = "24h", system_id: Optional[int] = None) -> Dict[str, Any]:
        """获取告警分发统计"""
        try:
            start_time = self._get_start_time(time_range)
            
            async with async_session_maker() as session:
                # 分发总数统计
                total_result = await session.execute(
                    select(func.count(AlarmDistribution.id)).where(
                        AlarmDistribution.created_at >= start_time
                    )
                )
                total_distributions = total_result.scalar() or 0
                
                # 按状态统计
                status_result = await session.execute(
                    select(
                        AlarmDistribution.status,
                        func.count(AlarmDistribution.id).label('count')
                    ).where(
                        AlarmDistribution.created_at >= start_time
                    ).group_by(AlarmDistribution.status)
                )
                status_stats = {row.status: row.count for row in status_result.all()}
                
                # 按用户统计
                user_result = await session.execute(
                    select(
                        User.username,
                        func.count(AlarmDistribution.id).label('count')
                    ).join(
                        User, AlarmDistribution.user_id == User.id
                    ).where(
                        AlarmDistribution.created_at >= start_time
                    ).group_by(User.username).order_by(desc('count')).limit(10)
                )
                user_stats = [{"username": row.username, "count": row.count} for row in user_result.all()]
                
                # 通知发送统计
                notification_result = await session.execute(
                    select(
                        func.count(AlarmDistribution.id).filter(AlarmDistribution.notification_sent == True).label('sent'),
                        func.count(AlarmDistribution.id).filter(AlarmDistribution.notification_sent == False).label('pending')
                    ).where(
                        AlarmDistribution.created_at >= start_time
                    )
                )
                notification_stats = notification_result.first()
                
                return {
                    "time_range": time_range,
                    "total_distributions": total_distributions,
                    "by_status": status_stats,
                    "top_users": user_stats,
                    "notifications": {
                        "sent": notification_stats.sent or 0,
                        "pending": notification_stats.pending or 0
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get distribution stats: {str(e)}")
            return {}
            
    async def get_correlation_analysis(self, time_range: str = "24h", system_id: Optional[int] = None) -> Dict[str, Any]:
        """获取告警关联分析"""
        try:
            start_time = self._get_start_time(time_range)
            
            async with async_session_maker() as session:
                # 获取告警数据
                result = await session.execute(
                    select(AlarmTable).where(
                        AlarmTable.created_at >= start_time
                    ).order_by(AlarmTable.created_at)
                )
                alarms = result.scalars().all()
                
                # 时间关联分析
                time_correlations = await self._analyze_time_correlations(alarms)
                
                # 主机关联分析
                host_correlations = await self._analyze_host_correlations(alarms)
                
                # 服务关联分析
                service_correlations = await self._analyze_service_correlations(alarms)
                
                # 严重程度关联分析
                severity_correlations = await self._analyze_severity_correlations(alarms)
                
                return {
                    "time_range": time_range,
                    "time_correlations": time_correlations,
                    "host_correlations": host_correlations,
                    "service_correlations": service_correlations,
                    "severity_correlations": severity_correlations
                }
                
        except Exception as e:
            logger.error(f"Failed to get correlation analysis: {str(e)}")
            return {}
    
    def _build_conditions(self, start_time: datetime, system_id: Optional[int] = None) -> list:
        """构建查询条件"""
        conditions = [AlarmTable.created_at >= start_time]
        if system_id is not None:
            conditions.append(AlarmTable.system_id == system_id)
        return conditions
            
    async def _get_basic_stats(self, session: AsyncSession, start_time: datetime, system_id: Optional[int] = None) -> Dict[str, int]:
        """获取基础统计"""
        conditions = [AlarmTable.created_at >= start_time]
        if system_id is not None:
            conditions.append(AlarmTable.system_id == system_id)
            
        result = await session.execute(
            select(
                func.count(AlarmTable.id).label('total'),
                func.count(AlarmTable.id).filter(AlarmTable.status == 'active').label('active'),
                func.count(AlarmTable.id).filter(AlarmTable.status == 'resolved').label('resolved'),
                func.count(AlarmTable.id).filter(AlarmTable.status == 'acknowledged').label('acknowledged'),
                func.count(AlarmTable.id).filter(AlarmTable.is_duplicate == True).label('duplicates')
            ).where(and_(*conditions))
        )
        stats = result.first()
        
        return {
            "total": stats.total or 0,
            "active": stats.active or 0,
            "resolved": stats.resolved or 0,
            "acknowledged": stats.acknowledged or 0,
            "duplicates": stats.duplicates or 0
        }
        
    async def _get_severity_stats(self, session: AsyncSession, start_time: datetime, system_id: Optional[int] = None) -> Dict[str, int]:
        """获取严重程度统计"""
        conditions = self._build_conditions(start_time, system_id)
        result = await session.execute(
            select(
                AlarmTable.severity,
                func.count(AlarmTable.id).label('count')
            ).where(and_(*conditions)).group_by(AlarmTable.severity)
        )
        
        return {row.severity: row.count for row in result.all()}
        
    async def _get_status_stats(self, session: AsyncSession, start_time: datetime, system_id: Optional[int] = None) -> Dict[str, int]:
        """获取状态统计"""
        conditions = self._build_conditions(start_time, system_id)
        result = await session.execute(
            select(
                AlarmTable.status,
                func.count(AlarmTable.id).label('count')
            ).where(and_(*conditions)).group_by(AlarmTable.status)
        )
        
        return {row.status: row.count for row in result.all()}
        
    async def _get_source_stats(self, session: AsyncSession, start_time: datetime, system_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取来源统计"""
        conditions = self._build_conditions(start_time, system_id)
        result = await session.execute(
            select(
                AlarmTable.source,
                func.count(AlarmTable.id).label('count')
            ).where(and_(*conditions)).group_by(AlarmTable.source).order_by(desc('count')).limit(10)
        )
        
        return [{"source": row.source, "count": row.count} for row in result.all()]
        
    async def _get_host_stats(self, session: AsyncSession, start_time: datetime, system_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取主机统计"""
        conditions = self._build_conditions(start_time, system_id)
        conditions.append(AlarmTable.host.isnot(None))
        result = await session.execute(
            select(
                AlarmTable.host,
                func.count(AlarmTable.id).label('count')
            ).where(and_(*conditions)).group_by(AlarmTable.host).order_by(desc('count')).limit(10)
        )
        
        return [{"host": row.host, "count": row.count} for row in result.all()]
        
    async def _get_service_stats(self, session: AsyncSession, start_time: datetime, system_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取服务统计"""
        conditions = self._build_conditions(start_time, system_id)
        conditions.append(AlarmTable.service.isnot(None))
        result = await session.execute(
            select(
                AlarmTable.service,
                func.count(AlarmTable.id).label('count')
            ).where(and_(*conditions)).group_by(AlarmTable.service).order_by(desc('count')).limit(10)
        )
        
        return [{"service": row.service, "count": row.count} for row in result.all()]
        
    async def _get_timeline_data(self, session: AsyncSession, start_time: datetime, interval: str) -> List[Dict[str, Any]]:
        """获取时间线数据"""
        # 数据库兼容的时间截断函数
        trunc_func = get_date_trunc_func(engine, AlarmTable.created_at, interval)
            
        result = await session.execute(
            select(
                trunc_func.label('time_bucket'),
                func.count(AlarmTable.id).label('count')
            ).where(
                AlarmTable.created_at >= start_time
            ).group_by('time_bucket').order_by('time_bucket')
        )
        
        return [
            {
                "time": row.time_bucket,
                "count": row.count
            }
            for row in result.all()
        ]
        
    async def _get_severity_trends(self, session: AsyncSession, start_time: datetime, interval: str) -> List[Dict[str, Any]]:
        """获取严重程度趋势"""
        # 数据库兼容的时间截断函数
        trunc_func = get_date_trunc_func(engine, AlarmTable.created_at, interval)
            
        result = await session.execute(
            select(
                trunc_func.label('time_bucket'),
                AlarmTable.severity,
                func.count(AlarmTable.id).label('count')
            ).where(
                AlarmTable.created_at >= start_time
            ).group_by('time_bucket', AlarmTable.severity).order_by('time_bucket')
        )
        
        # 按时间分组
        trends = defaultdict(dict)
        for row in result.all():
            time_key = row.time_bucket
            trends[time_key][row.severity] = row.count
            
        return [
            {
                "time": time_key,
                **severity_counts
            }
            for time_key, severity_counts in trends.items()
        ]
        
    async def _get_source_trends(self, session: AsyncSession, start_time: datetime, interval: str) -> List[Dict[str, Any]]:
        """获取来源趋势"""
        # 先获取TOP 5来源
        top_sources_result = await session.execute(
            select(
                AlarmTable.source,
                func.count(AlarmTable.id).label('count')
            ).where(
                AlarmTable.created_at >= start_time
            ).group_by(AlarmTable.source).order_by(desc('count')).limit(5)
        )
        top_sources = [row.source for row in top_sources_result.all()]
        
        if not top_sources:
            return []
            
        # SQLite兼容的时间截断函数
        # 数据库兼容的时间截断函数
        trunc_func = get_date_trunc_func(engine, AlarmTable.created_at, interval)
            
        result = await session.execute(
            select(
                trunc_func.label('time_bucket'),
                AlarmTable.source,
                func.count(AlarmTable.id).label('count')
            ).where(
                and_(
                    AlarmTable.created_at >= start_time,
                    AlarmTable.source.in_(top_sources)
                )
            ).group_by('time_bucket', AlarmTable.source).order_by('time_bucket')
        )
        
        # 按时间分组
        trends = defaultdict(dict)
        for row in result.all():
            time_key = row.time_bucket
            trends[time_key][row.source] = row.count
            
        return [
            {
                "time": time_key,
                **source_counts
            }
            for time_key, source_counts in trends.items()
        ]
        
    async def _get_frequent_alarms(self, session: AsyncSession, start_time: datetime, limit: int) -> List[Dict[str, Any]]:
        """获取最频繁的告警"""
        result = await session.execute(
            select(
                AlarmTable.title,
                AlarmTable.source,
                func.count(AlarmTable.id).label('count'),
                func.max(AlarmTable.created_at).label('last_occurrence')
            ).where(
                AlarmTable.created_at >= start_time
            ).group_by(AlarmTable.title, AlarmTable.source).order_by(desc('count')).limit(limit)
        )
        
        return [
            {
                "title": row.title,
                "source": row.source,
                "count": row.count,
                "last_occurrence": row.last_occurrence.isoformat()
            }
            for row in result.all()
        ]
        
    async def _get_longest_unresolved(self, session: AsyncSession, limit: int) -> List[Dict[str, Any]]:
        """获取最久未解决的告警"""
        result = await session.execute(
            select(AlarmTable).where(
                AlarmTable.status == 'active'
            ).order_by(AlarmTable.created_at).limit(limit)
        )
        
        alarms = []
        for alarm in result.scalars().all():
            duration = datetime.utcnow() - alarm.created_at
            alarms.append({
                "id": alarm.id,
                "title": alarm.title,
                "source": alarm.source,
                "severity": alarm.severity,
                "created_at": alarm.created_at.isoformat(),
                "duration_hours": duration.total_seconds() / 3600
            })
            
        return alarms
        
    async def _get_latest_alarms(self, session: AsyncSession, limit: int) -> List[Dict[str, Any]]:
        """获取最新的告警"""
        result = await session.execute(
            select(AlarmTable).order_by(desc(AlarmTable.created_at)).limit(limit)
        )
        
        return [
            {
                "id": alarm.id,
                "title": alarm.title,
                "source": alarm.source,
                "severity": alarm.severity,
                "status": alarm.status,
                "created_at": alarm.created_at.isoformat()
            }
            for alarm in result.scalars().all()
        ]
        
    async def _get_critical_unresolved(self, session: AsyncSession, limit: int) -> List[Dict[str, Any]]:
        """获取最严重的未解决告警"""
        result = await session.execute(
            select(AlarmTable).where(
                and_(
                    AlarmTable.status == 'active',
                    AlarmTable.severity == 'critical'
                )
            ).order_by(AlarmTable.created_at).limit(limit)
        )
        
        alarms = []
        for alarm in result.scalars().all():
            duration = datetime.utcnow() - alarm.created_at
            alarms.append({
                "id": alarm.id,
                "title": alarm.title,
                "source": alarm.source,
                "host": alarm.host,
                "service": alarm.service,
                "created_at": alarm.created_at.isoformat(),
                "duration_hours": duration.total_seconds() / 3600
            })
            
        return alarms
        
    async def _analyze_time_correlations(self, alarms: List[AlarmTable]) -> List[Dict[str, Any]]:
        """分析时间关联"""
        correlations = []
        
        # 按5分钟窗口分组
        time_buckets = defaultdict(list)
        for alarm in alarms:
            bucket = alarm.created_at.replace(minute=alarm.created_at.minute // 5 * 5, second=0, microsecond=0)
            time_buckets[bucket].append(alarm)
            
        # 查找有多个告警的时间窗口
        for bucket_time, bucket_alarms in time_buckets.items():
            if len(bucket_alarms) > 1:
                sources = [alarm.source for alarm in bucket_alarms]
                correlations.append({
                    "time_window": bucket_time.isoformat(),
                    "alarm_count": len(bucket_alarms),
                    "sources": list(set(sources)),
                    "correlation_score": len(bucket_alarms) / len(set(sources))
                })
                
        return sorted(correlations, key=lambda x: x["correlation_score"], reverse=True)[:10]
        
    async def _analyze_host_correlations(self, alarms: List[AlarmTable]) -> List[Dict[str, Any]]:
        """分析主机关联"""
        host_alarms = defaultdict(list)
        
        for alarm in alarms:
            if alarm.host:
                host_alarms[alarm.host].append(alarm)
                
        correlations = []
        for host, host_alarm_list in host_alarms.items():
            if len(host_alarm_list) > 1:
                sources = [alarm.source for alarm in host_alarm_list]
                services = [alarm.service for alarm in host_alarm_list if alarm.service]
                
                correlations.append({
                    "host": host,
                    "alarm_count": len(host_alarm_list),
                    "unique_sources": len(set(sources)),
                    "unique_services": len(set(services)),
                    "sources": list(set(sources)),
                    "services": list(set(services))
                })
                
        return sorted(correlations, key=lambda x: x["alarm_count"], reverse=True)[:10]
        
    async def _analyze_service_correlations(self, alarms: List[AlarmTable]) -> List[Dict[str, Any]]:
        """分析服务关联"""
        service_alarms = defaultdict(list)
        
        for alarm in alarms:
            if alarm.service:
                service_alarms[alarm.service].append(alarm)
                
        correlations = []
        for service, service_alarm_list in service_alarms.items():
            if len(service_alarm_list) > 1:
                hosts = [alarm.host for alarm in service_alarm_list if alarm.host]
                sources = [alarm.source for alarm in service_alarm_list]
                
                correlations.append({
                    "service": service,
                    "alarm_count": len(service_alarm_list),
                    "unique_hosts": len(set(hosts)),
                    "unique_sources": len(set(sources)),
                    "hosts": list(set(hosts)),
                    "sources": list(set(sources))
                })
                
        return sorted(correlations, key=lambda x: x["alarm_count"], reverse=True)[:10]
        
    async def _analyze_severity_correlations(self, alarms: List[AlarmTable]) -> Dict[str, Any]:
        """分析严重程度关联"""
        severity_combinations = []
        
        # 按5分钟窗口分组
        time_buckets = defaultdict(list)
        for alarm in alarms:
            bucket = alarm.created_at.replace(minute=alarm.created_at.minute // 5 * 5, second=0, microsecond=0)
            time_buckets[bucket].append(alarm)
            
        for bucket_time, bucket_alarms in time_buckets.items():
            if len(bucket_alarms) > 1:
                severities = [alarm.severity for alarm in bucket_alarms]
                severity_counter = Counter(severities)
                
                if len(severity_counter) > 1:  # 有不同严重程度的告警
                    severity_combinations.append({
                        "time_window": bucket_time.isoformat(),
                        "severities": dict(severity_counter),
                        "total_alarms": len(bucket_alarms)
                    })
                    
        return {
            "combinations": severity_combinations[:10],
            "total_combinations": len(severity_combinations)
        }
        
    def _get_start_time(self, time_range: str) -> datetime:
        """根据时间范围获取开始时间"""
        now = datetime.utcnow()
        
        if time_range == "1h":
            return now - timedelta(hours=1)
        elif time_range == "6h":
            return now - timedelta(hours=6)
        elif time_range == "24h":
            return now - timedelta(hours=24)
        elif time_range == "7d":
            return now - timedelta(days=7)
        elif time_range == "30d":
            return now - timedelta(days=30)
        else:
            return now - timedelta(hours=24)
            
    async def clear_cache(self):
        """清除缓存"""
        self.aggregation_cache.clear()
        self.trends_cache.clear()
        logger.info("Cleared aggregation cache")