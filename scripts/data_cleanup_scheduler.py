#!/usr/bin/env python3
"""
数据清理调度脚本
可以通过cron或其他调度器定期执行
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import argparse
from datetime import datetime
from src.services.data_lifecycle_service import DataLifecycleService
from src.core.logging import get_logger

logger = get_logger(__name__)


async def run_data_cleanup(
    archive_days: int = 90,
    cleanup_days: int = 365,
    dry_run: bool = True,
    optimize_db: bool = False
):
    """运行数据清理任务"""
    service = DataLifecycleService()
    
    try:
        logger.info(f"开始数据清理任务 - 归档: {archive_days}天前, 清理: {cleanup_days}天前, 演练模式: {dry_run}")
        
        # 获取当前数据统计
        stats = await service.get_data_statistics()
        logger.info(f"当前数据统计: {stats}")
        
        # 执行归档
        if archive_days > 0:
            logger.info("开始数据归档...")
            archive_result = await service.archive_old_data(
                archive_before_days=archive_days,
                batch_size=1000
            )
            logger.info(f"归档结果: {archive_result}")
        
        # 执行清理
        if cleanup_days > 0:
            logger.info(f"开始数据清理 (演练模式: {dry_run})...")
            cleanup_result = await service.cleanup_old_data(
                cleanup_before_days=cleanup_days,
                batch_size=1000,
                dry_run=dry_run
            )
            logger.info(f"清理结果: {cleanup_result}")
        
        # 数据库优化
        if optimize_db:
            logger.info("开始数据库优化...")
            optimize_result = await service.optimize_database()
            logger.info(f"优化结果: {optimize_result}")
        
        # 获取清理后的统计
        final_stats = await service.get_data_statistics()
        logger.info(f"清理后数据统计: {final_stats}")
        
        logger.info("数据清理任务完成")
        
    except Exception as e:
        logger.error(f"数据清理任务失败: {str(e)}")
        raise


def main():
    parser = argparse.ArgumentParser(description="数据生命周期管理工具")
    parser.add_argument("--archive-days", type=int, default=90, 
                       help="归档多少天前的数据 (默认: 90)")
    parser.add_argument("--cleanup-days", type=int, default=365,
                       help="清理多少天前的数据 (默认: 365)")
    parser.add_argument("--real-run", action="store_true",
                       help="实际执行清理 (默认为演练模式)")
    parser.add_argument("--optimize", action="store_true",
                       help="执行数据库优化")
    parser.add_argument("--archive-only", action="store_true",
                       help="仅执行归档，不清理数据")
    parser.add_argument("--cleanup-only", action="store_true",
                       help="仅执行清理，不归档数据")
    
    args = parser.parse_args()
    
    # 确定要执行的操作
    archive_days = 0 if args.cleanup_only else args.archive_days
    cleanup_days = 0 if args.archive_only else args.cleanup_days
    dry_run = not args.real_run
    
    print(f"数据清理任务配置:")
    print(f"  归档天数: {archive_days} (0=跳过)")
    print(f"  清理天数: {cleanup_days} (0=跳过)")
    print(f"  演练模式: {dry_run}")
    print(f"  数据库优化: {args.optimize}")
    print(f"  开始时间: {datetime.now()}")
    print("-" * 50)
    
    if dry_run:
        print("⚠️  当前为演练模式，不会实际删除数据")
        print("   使用 --real-run 参数执行实际清理")
        print("-" * 50)
    
    try:
        asyncio.run(run_data_cleanup(
            archive_days=archive_days,
            cleanup_days=cleanup_days,
            dry_run=dry_run,
            optimize_db=args.optimize
        ))
        print(f"✅ 数据清理任务成功完成 - {datetime.now()}")
    except Exception as e:
        print(f"❌ 数据清理任务失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()