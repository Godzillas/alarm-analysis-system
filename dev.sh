#!/bin/bash

# 开发模式启动脚本
# 支持前后端热重载和自动构建

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# 检查是否为开发模式
DEV_MODE=${1:-"dev"}

echo "🚀 启动告警分析系统 (${DEV_MODE}模式)..."

# 检查并创建logs目录
mkdir -p logs

# 清理函数
cleanup() {
    echo ""
    echo "🧹 正在清理进程..."
    # 清理后台进程
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID > /dev/null 2>&1 || true
    fi
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID > /dev/null 2>&1 || true
    fi
    # 清理端口上的进程
    lsof -ti:8000 | xargs kill -9 > /dev/null 2>&1 || true
    lsof -ti:8080 | xargs kill -9 > /dev/null 2>&1 || true
    echo "✅ 清理完成"
    exit 0
}

# 注册清理函数
trap cleanup SIGINT SIGTERM EXIT

# 启动Redis
echo "📡 启动 Redis 服务..."
if ! pgrep -x "redis-server" > /dev/null; then
    if command -v brew &> /dev/null; then
        brew services start redis > /dev/null 2>&1
    fi
fi

# 清理端口
echo "🧹 清理端口..."
lsof -ti:8000 | xargs kill -9 > /dev/null 2>&1 || true
lsof -ti:8080 | xargs kill -9 > /dev/null 2>&1 || true

cd "$FRONTEND_DIR"

# 检查前端依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi

if [ "$DEV_MODE" == "dev" ]; then
    echo "🔧 启动开发模式 (热重载)..."
    
    # 启动前端开发服务器
    echo "🎨 启动前端开发服务器 (端口8080)..."
    npm run serve > "$PROJECT_DIR/logs/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    
    # 等待前端服务器启动
    echo "⏳ 等待前端服务器启动..."
    sleep 5
    
    # 启动后端开发服务器 (热重载)
    cd "$PROJECT_DIR"
    echo "🔥 启动后端开发服务器 (热重载)..."
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        echo "📦 创建虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 安装依赖
    echo "📦 检查后端依赖..."
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements.txt > /dev/null 2>&1
    
    # 等待并获取前端实际端口
    echo "🔍 检测前端服务器地址..."
    sleep 2
    FRONTEND_URL=$(grep -o "http://localhost:[0-9]*" logs/frontend.log | tail -1)
    if [ -z "$FRONTEND_URL" ]; then
        FRONTEND_URL="http://localhost:3001"
    fi
    
    echo ""
    echo "🎉 开发服务器启动完成!"
    echo "🎨 前端开发服务器: $FRONTEND_URL"
    echo "🔥 后端API服务器: http://localhost:8000"
    echo "📚 API文档: http://localhost:8000/docs"
    echo "📝 前端日志: tail -f logs/frontend.log"
    echo ""
    echo "⚠️  请访问前端地址查看最新修改: $FRONTEND_URL"
    echo "⚠️  不要访问 http://localhost:8000 的静态页面!"
    echo "💡 按 Ctrl+C 停止所有服务"
    echo ""
    
    # 启动后端 (热重载)
    DEV_MODE=true python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
    
else
    echo "🔨 生产模式构建..."
    
    # 构建前端
    echo "⚙️  构建前端..."
    npm run build
    
    # 移动构建文件
    cd "$PROJECT_DIR"
    if [ -d "static/dist" ]; then
        rm -rf static/dist
    fi
    cp -r "$FRONTEND_DIR/dist" static/
    
    echo "✅ 前端构建完成"
    
    # 启动后端
    echo "🔥 启动后端服务..."
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        echo "📦 创建虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 安装依赖
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements.txt > /dev/null 2>&1
    
    echo ""
    echo "🎉 启动完成!"
    echo "📱 访问地址: http://localhost:8000"
    echo "📚 API文档: http://localhost:8000/docs"
    echo "💡 按 Ctrl+C 停止服务"
    echo ""
    
    # 启动服务器
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
fi
