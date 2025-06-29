#!/usr/bin/env python3
"""
测试WebSocket阻止功能
"""

import asyncio
import websockets
import json
import sys


async def test_normal_connection():
    """测试正常连接"""
    print("🔗 测试正常WebSocket连接...")
    try:
        uri = "ws://localhost:8000/ws"
        headers = {
            "Origin": "http://localhost:3001",
            "User-Agent": "Test Client/1.0"
        }
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            print("✅ 连接成功")
            
            # 发送初始化消息
            await websocket.send(json.dumps({"type": "init", "client": "test"}))
            print("📤 发送初始化消息")
            
            # 接收响应
            response = await websocket.recv()
            print(f"📨 收到响应: {response}")
            
            # 保持连接一会儿
            await asyncio.sleep(2)
            print("⏰ 连接保持2秒")
            
    except Exception as e:
        print(f"❌ 连接失败: {e}")


async def test_browser_like_connection():
    """测试类似浏览器的连接（应该被阻止）"""
    print("\n🌐 测试浏览器类连接...")
    try:
        uri = "ws://localhost:8000/ws"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        }
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            print("⚠️  连接意外成功（应该被阻止）")
            
            # 尝试保持连接但不发送消息（模拟开发工具行为）
            await asyncio.sleep(5)
            
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"✅ 连接被正确阻止: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")


async def test_rapid_connections():
    """测试快速连接（应该触发频率限制）"""
    print("\n⚡ 测试快速连接...")
    
    for i in range(5):
        try:
            uri = "ws://localhost:8000/ws"
            headers = {
                "Origin": "http://localhost:3001",
                "User-Agent": "Rapid Test Client/1.0"
            }
            
            async with websockets.connect(uri, extra_headers=headers) as websocket:
                print(f"  连接 {i+1} 成功")
                await websocket.send(json.dumps({"type": "test", "id": i}))
                await websocket.recv()
                
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"  连接 {i+1} 被频率限制阻止: {e}")
        except Exception as e:
            print(f"  连接 {i+1} 失败: {e}")
        
        await asyncio.sleep(0.5)


async def main():
    """主测试函数"""
    print("🧪 WebSocket阻止功能测试")
    print("=" * 50)
    
    await test_normal_connection()
    await test_browser_like_connection()
    await test_rapid_connections()
    
    print("\n🏁 测试完成")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 测试中断")