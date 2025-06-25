#!/bin/bash

# 快速开发启动脚本
# 自动构建前端并启动后端

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "🚀 快速启动告警分析系统..."

# 检查并创建logs目录
mkdir -p logs

# 启动Redis
echo "📡 启动 Redis 服务..."
if ! pgrep -x "redis-server" > /dev/null; then
    if command -v brew &> /dev/null; then
        brew services start redis > /dev/null 2>&1
    fi
fi

# 构建前端
echo "🔨 构建前端项目..."
cd "$FRONTEND_DIR"

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install > /dev/null 2>&1
fi

# 清理旧的构建文件
cd "$PROJECT_DIR"
if [ -d "static/dist" ]; then
    rm -rf static/dist
fi

cd "$FRONTEND_DIR"

# 构建项目 (跳过ESLint检查以避免格式化警告)
echo "⚙️  正在编译前端代码..."
npm run build -- --skip-plugins @vue/cli-plugin-eslint > /dev/null 2>&1

# 检查构建是否成功
cd "$PROJECT_DIR"
if [ -d "static/dist" ]; then
    echo "✅ 前端构建完成"
    echo "📁 静态文件已生成到 static/dist"
else
    echo "❌ 前端构建失败"
    exit 1
fi

# 启动后端
cd "$PROJECT_DIR"
echo "🔥 启动后端服务..."

# 激活虚拟环境
source venv/bin/activate

# 安装缺失的依赖
if ! python -c "import greenlet" 2>/dev/null; then
    echo "📦 安装缺失的依赖..."
    pip install greenlet -i https://mirrors.aliyun.com/pypi/simple/ > /dev/null 2>&1
fi

echo ""
echo "🎉 启动完成!"
echo "📱 访问地址: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/docs"
echo "💡 按 Ctrl+C 停止服务"
echo ""

# 启动服务器
python main.py
