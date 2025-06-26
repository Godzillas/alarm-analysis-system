"""
数据库连接和会话管理
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from src.core.config import settings
from sqlalchemy.ext.declarative import declarative_base

# 创建Base类，避免循环导入
Base = declarative_base()


if settings.DATABASE_URL.startswith("sqlite"):
    async_database_url = settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
    engine = create_async_engine(
        async_database_url, 
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_recycle=settings.DATABASE_POOL_RECYCLE
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL, 
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_recycle=settings.DATABASE_POOL_RECYCLE
    )

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db_session():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库，创建表结构"""
    try:
        # 对于MySQL，先创建数据库（如果不存在）
        if settings.DATABASE_URL.startswith("mysql"):
            await create_mysql_database_if_not_exists()
        
        # 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        print("✅ 数据库表结构同步完成")
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {str(e)}")
        raise


async def create_mysql_database_if_not_exists():
    """为MySQL创建数据库（如果不存在）"""
    import re
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    
    # 解析数据库URL获取数据库名
    match = re.search(r'/([^/]+)(?:\?|$)', settings.DATABASE_URL)
    if not match:
        raise ValueError("无法从DATABASE_URL解析数据库名")
    
    db_name = match.group(1)
    
    # 创建连接到MySQL服务器（不指定数据库）的URL
    server_url = settings.DATABASE_URL.rsplit('/', 1)[0]
    
    # 连接到MySQL服务器
    server_engine = create_async_engine(server_url, echo=settings.DEBUG)
    
    try:
        async with server_engine.begin() as conn:
            # 检查数据库是否存在
            result = await conn.execute(
                text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{db_name}'")
            )
            if not result.fetchone():
                # 创建数据库
                await conn.execute(text(f"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                print(f"✅ 已创建MySQL数据库: {db_name}")
            else:
                print(f"✅ MySQL数据库已存在: {db_name}")
                
    finally:
        await server_engine.dispose()