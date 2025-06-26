#!/usr/bin/env python3
"""
初始化通知模板脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from src.services.template_service import TemplateService


async def main():
    """初始化默认通知模板"""
    print("开始初始化通知模板...")
    
    template_service = TemplateService()
    
    try:
        await template_service.create_builtin_templates()
        print("✅ 通知模板初始化完成")
    except Exception as e:
        print(f"❌ 通知模板初始化失败: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())