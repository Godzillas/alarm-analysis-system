"""
数据库工具函数
"""

from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine


def get_date_trunc_func(engine, column, interval: str):
    """
    获取数据库兼容的日期截断函数
    
    Args:
        engine: 数据库引擎
        column: 要截断的日期列
        interval: 时间间隔 ('1h' 表示小时, '1d' 表示天)
    
    Returns:
        SQLAlchemy 函数表达式
    """
    # 获取数据库方言名称
    if hasattr(engine, 'dialect'):
        dialect_name = engine.dialect.name
    elif hasattr(engine, 'engine'):
        dialect_name = engine.engine.dialect.name
    else:
        # 默认假设是异步引擎，通过URL判断
        dialect_name = 'sqlite'  # 默认值
        
    if dialect_name == 'mysql':
        # MySQL 8.0 使用 DATE_FORMAT
        if interval == "1h":
            return func.date_format(column, '%Y-%m-%d %H:00:00')
        elif interval == "1d":
            return func.date_format(column, '%Y-%m-%d 00:00:00')
        else:
            return func.date_format(column, '%Y-%m-%d %H:00:00')
    else:
        # SQLite 使用 strftime
        if interval == "1h":
            return func.strftime('%Y-%m-%d %H:00:00', column)
        elif interval == "1d":
            return func.strftime('%Y-%m-%d 00:00:00', column)
        else:
            return func.strftime('%Y-%m-%d %H:00:00', column)


def get_database_type_from_url(database_url: str) -> str:
    """
    从数据库URL获取数据库类型
    
    Args:
        database_url: 数据库连接URL
        
    Returns:
        数据库类型 ('mysql', 'sqlite', 'postgresql')
    """
    if database_url.startswith('mysql'):
        return 'mysql'
    elif database_url.startswith('sqlite'):
        return 'sqlite'
    elif database_url.startswith('postgresql'):
        return 'postgresql'
    else:
        return 'sqlite'  # 默认