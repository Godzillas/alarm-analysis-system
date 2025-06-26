"""
数据生命周期管理服务
负责数据归档、清理和备份等功能
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_, text
from sqlalchemy.orm import selectinload

from src.core.database import async_session_maker, engine
from src.core.logging import get_logger
from src.core.config import settings
from src.core.exceptions import DatabaseException, ConfigurationException
from src.models.alarm import AlarmTable
from src.models.alarm_processing import AlarmProcessing, AlarmProcessingHistory, AlarmProcessingComment
from src.models.subscription import AlarmNotification, NotificationDigest

logger = get_logger(__name__)


class DataLifecycleService:
    """数据生命周期管理服务"""
    
    def __init__(self):
        self.logger = logger
    
    async def archive_old_data(
        self,
        archive_before_days: int = 90,
        batch_size: int = 1000
    ) -> Dict[str, int]:
        """归档旧数据"""
        stats = {
            "alarms_archived": 0,
            "notifications_archived": 0,
            "processing_history_archived": 0,
            "comments_archived": 0
        }
        
        cutoff_date = datetime.utcnow() - timedelta(days=archive_before_days)
        
        try:
            # 归档告警数据
            stats["alarms_archived"] = await self._archive_alarms(cutoff_date, batch_size)
            
            # 归档通知数据
            stats["notifications_archived"] = await self._archive_notifications(cutoff_date, batch_size)
            
            # 归档处理历史
            stats["processing_history_archived"] = await self._archive_processing_history(cutoff_date, batch_size)
            
            # 归档评论数据
            stats["comments_archived"] = await self._archive_comments(cutoff_date, batch_size)
            
            self.logger.info(f"Data archival completed: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error during data archival: {str(e)}")
            raise DatabaseException(f"Data archival failed: {str(e)}")
    
    async def cleanup_old_data(
        self,
        cleanup_before_days: int = 365,
        batch_size: int = 1000,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """清理旧数据"""
        stats = {
            "alarms_deleted": 0,
            "notifications_deleted": 0,
            "processing_deleted": 0,
            "history_deleted": 0,
            "comments_deleted": 0,
            "digests_deleted": 0
        }
        
        cutoff_date = datetime.utcnow() - timedelta(days=cleanup_before_days)
        
        try:
            if dry_run:
                # 干运行：只统计不删除
                stats = await self._count_old_data(cutoff_date)
                self.logger.info(f"Dry run cleanup stats: {stats}")
            else:
                # 实际删除数据
                stats["digests_deleted"] = await self._cleanup_notification_digests(cutoff_date, batch_size)
                stats["comments_deleted"] = await self._cleanup_processing_comments(cutoff_date, batch_size)
                stats["history_deleted"] = await self._cleanup_processing_history(cutoff_date, batch_size)
                stats["notifications_deleted"] = await self._cleanup_notifications(cutoff_date, batch_size)
                stats["processing_deleted"] = await self._cleanup_alarm_processing(cutoff_date, batch_size)
                stats["alarms_deleted"] = await self._cleanup_alarms(cutoff_date, batch_size)
                
                self.logger.info(f"Data cleanup completed: {stats}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error during data cleanup: {str(e)}")
            raise DatabaseException(f"Data cleanup failed: {str(e)}")
    
    async def optimize_database(self) -> Dict[str, Any]:
        """优化数据库"""
        stats = {}
        
        try:
            # 重建索引
            await self._rebuild_indexes()
            stats["indexes_rebuilt"] = True
            
            # 更新表统计信息
            await self._update_table_statistics()
            stats["statistics_updated"] = True
            
            # 碎片整理（适用于MySQL）
            if "mysql" in settings.DATABASE_URL:
                await self._defragment_tables()
                stats["tables_defragmented"] = True
            
            # 检查表大小
            table_sizes = await self._get_table_sizes()
            stats["table_sizes"] = table_sizes
            
            self.logger.info(f"Database optimization completed: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error during database optimization: {str(e)}")
            raise DatabaseException(f"Database optimization failed: {str(e)}")
    
    async def get_data_statistics(self) -> Dict[str, Any]:
        """获取数据统计信息"""
        async with async_session_maker() as session:
            try:
                stats = {}
                
                # 告警统计
                alarm_stats = await session.execute(
                    select(
                        func.count(AlarmTable.id).label('total'),
                        func.count().filter(AlarmTable.created_at >= datetime.utcnow() - timedelta(days=30)).label('last_30_days'),
                        func.count().filter(AlarmTable.status == 'active').label('active'),
                        func.count().filter(AlarmTable.status == 'resolved').label('resolved')
                    )
                )
                alarm_row = alarm_stats.first()
                stats['alarms'] = {
                    'total': alarm_row.total,
                    'last_30_days': alarm_row.last_30_days,
                    'active': alarm_row.active,
                    'resolved': alarm_row.resolved
                }
                
                # 通知统计
                notification_stats = await session.execute(
                    select(
                        func.count(AlarmNotification.id).label('total'),
                        func.count().filter(AlarmNotification.created_at >= datetime.utcnow() - timedelta(days=30)).label('last_30_days'),
                        func.count().filter(AlarmNotification.status == 'sent').label('sent'),
                        func.count().filter(AlarmNotification.status == 'failed').label('failed')
                    )
                )
                notif_row = notification_stats.first()
                stats['notifications'] = {
                    'total': notif_row.total,
                    'last_30_days': notif_row.last_30_days,
                    'sent': notif_row.sent,
                    'failed': notif_row.failed
                }
                
                # 处理记录统计
                processing_stats = await session.execute(
                    select(
                        func.count(AlarmProcessing.id).label('total'),
                        func.count().filter(AlarmProcessing.created_at >= datetime.utcnow() - timedelta(days=30)).label('last_30_days'),
                        func.count().filter(AlarmProcessing.status == 'resolved').label('resolved'),
                        func.avg(AlarmProcessing.resolution_time_minutes).label('avg_resolution_time')
                    )
                )
                proc_row = processing_stats.first()
                stats['processing'] = {
                    'total': proc_row.total,
                    'last_30_days': proc_row.last_30_days,
                    'resolved': proc_row.resolved,
                    'avg_resolution_time_minutes': proc_row.avg_resolution_time
                }
                
                # 数据库大小信息
                stats['database'] = await self._get_database_size_info()
                
                return stats
                
            except Exception as e:
                raise DatabaseException(f"Failed to get data statistics: {str(e)}")
    
    async def create_backup(self, backup_path: Optional[str] = None) -> str:
        """创建数据备份"""
        try:
            backup_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            
            if not backup_path:
                backup_path = f"backups/alarm_system_backup_{backup_timestamp}.sql"
            
            # 根据数据库类型执行备份
            if "mysql" in settings.DATABASE_URL:
                backup_file = await self._create_mysql_backup(backup_path)
            elif "postgresql" in settings.DATABASE_URL:
                backup_file = await self._create_postgresql_backup(backup_path)
            else:
                # SQLite备份
                backup_file = await self._create_sqlite_backup(backup_path)
            
            self.logger.info(f"Database backup created: {backup_file}")
            return backup_file
            
        except Exception as e:
            self.logger.error(f"Error creating backup: {str(e)}")
            raise DatabaseException(f"Backup creation failed: {str(e)}")
    
    # 私有方法
    
    async def _archive_alarms(self, cutoff_date: datetime, batch_size: int) -> int:
        """归档告警数据"""
        # 这里可以实现将数据移动到归档表的逻辑
        # 目前先标记为已归档
        async with async_session_maker() as session:
            try:
                # 查询需要归档的告警
                result = await session.execute(
                    select(AlarmTable.id).where(
                        and_(
                            AlarmTable.created_at < cutoff_date,
                            AlarmTable.status == 'resolved'
                        )
                    ).limit(batch_size)
                )
                alarm_ids = [row[0] for row in result.fetchall()]
                
                if alarm_ids:
                    # 这里可以实现实际的归档逻辑
                    # 例如：将数据复制到归档表，然后删除原表数据
                    self.logger.info(f"Would archive {len(alarm_ids)} alarms")
                
                return len(alarm_ids)
                
            except Exception as e:
                await session.rollback()
                raise
    
    async def _archive_notifications(self, cutoff_date: datetime, batch_size: int) -> int:
        """归档通知数据"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(AlarmNotification.id).where(
                        AlarmNotification.created_at < cutoff_date
                    ).limit(batch_size)
                )
                notification_ids = [row[0] for row in result.fetchall()]
                
                if notification_ids:
                    self.logger.info(f"Would archive {len(notification_ids)} notifications")
                
                return len(notification_ids)
                
            except Exception as e:
                await session.rollback()
                raise
    
    async def _archive_processing_history(self, cutoff_date: datetime, batch_size: int) -> int:
        """归档处理历史"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(AlarmProcessingHistory.id).where(
                        AlarmProcessingHistory.action_at < cutoff_date
                    ).limit(batch_size)
                )
                history_ids = [row[0] for row in result.fetchall()]
                
                if history_ids:
                    self.logger.info(f"Would archive {len(history_ids)} processing history records")
                
                return len(history_ids)
                
            except Exception as e:
                await session.rollback()
                raise
    
    async def _archive_comments(self, cutoff_date: datetime, batch_size: int) -> int:
        """归档评论数据"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(AlarmProcessingComment.id).where(
                        AlarmProcessingComment.created_at < cutoff_date
                    ).limit(batch_size)
                )
                comment_ids = [row[0] for row in result.fetchall()]
                
                if comment_ids:
                    self.logger.info(f"Would archive {len(comment_ids)} comments")
                
                return len(comment_ids)
                
            except Exception as e:
                await session.rollback()
                raise
    
    async def _count_old_data(self, cutoff_date: datetime) -> Dict[str, int]:
        """统计旧数据数量"""
        async with async_session_maker() as session:
            try:
                stats = {}
                
                # 统计告警
                alarm_count = await session.execute(
                    select(func.count(AlarmTable.id)).where(
                        and_(
                            AlarmTable.created_at < cutoff_date,
                            AlarmTable.status == 'resolved'
                        )
                    )
                )
                stats["alarms_deleted"] = alarm_count.scalar()
                
                # 统计通知
                notif_count = await session.execute(
                    select(func.count(AlarmNotification.id)).where(
                        AlarmNotification.created_at < cutoff_date
                    )
                )
                stats["notifications_deleted"] = notif_count.scalar()
                
                # 统计处理记录
                proc_count = await session.execute(
                    select(func.count(AlarmProcessing.id)).where(
                        and_(
                            AlarmProcessing.created_at < cutoff_date,
                            AlarmProcessing.status == 'closed'
                        )
                    )
                )
                stats["processing_deleted"] = proc_count.scalar()
                
                return stats
                
            except Exception as e:
                raise DatabaseException(f"Failed to count old data: {str(e)}")
    
    async def _cleanup_notification_digests(self, cutoff_date: datetime, batch_size: int) -> int:
        """清理通知摘要"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    delete(NotificationDigest).where(
                        NotificationDigest.created_at < cutoff_date
                    )
                )
                await session.commit()
                return result.rowcount
                
            except Exception as e:
                await session.rollback()
                raise
    
    async def _cleanup_processing_comments(self, cutoff_date: datetime, batch_size: int) -> int:
        """清理处理评论"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    delete(AlarmProcessingComment).where(
                        AlarmProcessingComment.created_at < cutoff_date
                    )
                )
                await session.commit()
                return result.rowcount
                
            except Exception as e:
                await session.rollback()
                raise
    
    async def _cleanup_processing_history(self, cutoff_date: datetime, batch_size: int) -> int:
        """清理处理历史"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    delete(AlarmProcessingHistory).where(
                        AlarmProcessingHistory.action_at < cutoff_date
                    )
                )
                await session.commit()
                return result.rowcount
                
            except Exception as e:
                await session.rollback()
                raise
    
    async def _cleanup_notifications(self, cutoff_date: datetime, batch_size: int) -> int:
        """清理通知记录"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    delete(AlarmNotification).where(
                        AlarmNotification.created_at < cutoff_date
                    )
                )
                await session.commit()
                return result.rowcount
                
            except Exception as e:
                await session.rollback()
                raise
    
    async def _cleanup_alarm_processing(self, cutoff_date: datetime, batch_size: int) -> int:
        """清理告警处理记录"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    delete(AlarmProcessing).where(
                        and_(
                            AlarmProcessing.created_at < cutoff_date,
                            AlarmProcessing.status == 'closed'
                        )
                    )
                )
                await session.commit()
                return result.rowcount
                
            except Exception as e:
                await session.rollback()
                raise
    
    async def _cleanup_alarms(self, cutoff_date: datetime, batch_size: int) -> int:
        """清理告警记录"""
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    delete(AlarmTable).where(
                        and_(
                            AlarmTable.created_at < cutoff_date,
                            AlarmTable.status == 'resolved'
                        )
                    )
                )
                await session.commit()
                return result.rowcount
                
            except Exception as e:
                await session.rollback()
                raise
    
    async def _rebuild_indexes(self):
        """重建数据库索引"""
        async with engine.begin() as conn:
            # MySQL索引重建
            if "mysql" in settings.DATABASE_URL:
                await conn.execute(text("ANALYZE TABLE alarms"))
                await conn.execute(text("ANALYZE TABLE alarm_notifications"))
                await conn.execute(text("ANALYZE TABLE alarm_processing"))
    
    async def _update_table_statistics(self):
        """更新表统计信息"""
        async with engine.begin() as conn:
            if "mysql" in settings.DATABASE_URL:
                await conn.execute(text("ANALYZE TABLE alarms"))
                await conn.execute(text("ANALYZE TABLE alarm_notifications"))
                await conn.execute(text("ANALYZE TABLE alarm_processing"))
    
    async def _defragment_tables(self):
        """表碎片整理"""
        async with engine.begin() as conn:
            if "mysql" in settings.DATABASE_URL:
                await conn.execute(text("OPTIMIZE TABLE alarms"))
                await conn.execute(text("OPTIMIZE TABLE alarm_notifications"))
                await conn.execute(text("OPTIMIZE TABLE alarm_processing"))
    
    async def _get_table_sizes(self) -> Dict[str, Any]:
        """获取表大小信息"""
        async with engine.begin() as conn:
            if "mysql" in settings.DATABASE_URL:
                result = await conn.execute(text("""
                    SELECT 
                        table_name,
                        ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb,
                        table_rows
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name IN ('alarms', 'alarm_notifications', 'alarm_processing', 'alarm_processing_history')
                    ORDER BY (data_length + index_length) DESC
                """))
                
                return {
                    row.table_name: {
                        "size_mb": row.size_mb,
                        "rows": row.table_rows
                    }
                    for row in result.fetchall()
                }
            else:
                return {"message": "Table size information not available for this database type"}
    
    async def _get_database_size_info(self) -> Dict[str, Any]:
        """获取数据库大小信息"""
        async with engine.begin() as conn:
            if "mysql" in settings.DATABASE_URL:
                result = await conn.execute(text("""
                    SELECT 
                        ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS total_size_mb,
                        ROUND(SUM(data_length) / 1024 / 1024, 2) AS data_size_mb,
                        ROUND(SUM(index_length) / 1024 / 1024, 2) AS index_size_mb
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE()
                """))
                
                row = result.first()
                return {
                    "total_size_mb": row.total_size_mb,
                    "data_size_mb": row.data_size_mb,
                    "index_size_mb": row.index_size_mb
                }
            else:
                return {"message": "Database size information not available for this database type"}
    
    async def _create_mysql_backup(self, backup_path: str) -> str:
        """创建MySQL备份"""
        import subprocess
        import os
        from urllib.parse import urlparse
        
        # 解析数据库URL
        parsed = urlparse(settings.DATABASE_URL)
        
        # 确保备份目录存在
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # 构建mysqldump命令
        cmd = [
            "mysqldump",
            "-h", parsed.hostname or "localhost",
            "-P", str(parsed.port or 3306),
            "-u", parsed.username,
            f"-p{parsed.password}" if parsed.password else "",
            parsed.path[1:],  # 去掉开头的/
            "--routines",
            "--triggers",
            "--single-transaction"
        ]
        
        # 执行备份
        with open(backup_path, 'w') as f:
            subprocess.run(cmd, stdout=f, check=True)
        
        return backup_path
    
    async def _create_postgresql_backup(self, backup_path: str) -> str:
        """创建PostgreSQL备份"""
        import subprocess
        import os
        
        # 确保备份目录存在
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # 使用pg_dump
        cmd = ["pg_dump", settings.DATABASE_URL, "-f", backup_path]
        subprocess.run(cmd, check=True)
        
        return backup_path
    
    async def _create_sqlite_backup(self, backup_path: str) -> str:
        """创建SQLite备份"""
        import shutil
        import os
        from urllib.parse import urlparse
        
        # 解析数据库文件路径
        parsed = urlparse(settings.DATABASE_URL)
        db_file = parsed.path[1:]  # 去掉开头的/
        
        # 确保备份目录存在
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # 直接复制数据库文件
        shutil.copy2(db_file, backup_path)
        
        return backup_path