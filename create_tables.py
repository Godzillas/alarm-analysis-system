#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建数据库表结构
"""

import asyncio
from src.core.database import init_db

async def main():
    print("Creating database tables...")
    await init_db()
    print("Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(main())