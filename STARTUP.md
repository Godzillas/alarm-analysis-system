# 🚀 告警分析系统启动指南

基于 **FastAPI + Vue.js + Element UI** 的现代化告警分析系统

## 📋 快速启动

### 方式一：一键启动 (推荐)

```bash
# 快速启动 (自动构建+启动)
./dev.sh

# 或者使用 npm 脚本
npm run dev
```

### 方式二：完整启动脚本

```bash
# 开发模式 (前端:3000, 后端:8000)
./start.sh dev

# 生产模式 (端口:8000)  
./start.sh prod

# 仅构建前端
./start.sh build

# 安装所有依赖
./start.sh install
```

### 方式三：手动启动

```bash
# 1. 安装后端依赖
source venv/bin/activate
pip install -r requirements.txt
pip install greenlet

# 2. 启动Redis
brew services start redis

# 3. 构建前端
cd frontend
npm install
npm run build

# 4. 启动后端
cd ..
python main.py
```

## 🌐 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| **主应用** | http://localhost:8000 | Vue.js + Element UI 界面 |
| **API文档** | http://localhost:8000/docs | FastAPI Swagger 文档 |
| **管理后台** | http://localhost:8000/admin | 原始管理界面(备用) |

## 🛠️ 可用命令

```bash
# NPM 脚本
npm run dev              # 快速启动
npm run start            # 生产模式启动
npm run build            # 构建前端
npm run install:deps     # 安装依赖
npm run stop             # 停止服务
npm run restart          # 重启服务

# 启动脚本
./dev.sh                 # 快速开发启动
./start.sh dev           # 开发模式
./start.sh prod          # 生产模式
./start.sh build         # 构建前端
./start.sh install       # 安装依赖
./start.sh stop          # 停止服务
./start.sh restart       # 重启服务
./start.sh help          # 帮助信息
```

## 🏗️ 项目结构

```
alarm-analysis-system/
├── frontend/              # Vue.js 前端项目
│   ├── src/
│   │   ├── components/    # 公共组件
│   │   ├── views/         # 页面组件
│   │   ├── store/         # Pinia 状态管理
│   │   ├── api/           # API 接口
│   │   └── styles/        # 样式文件
│   ├── package.json       # 前端依赖
│   └── vue.config.js      # Vue CLI 配置
├── src/                   # FastAPI 后端代码
│   ├── api/               # API 路由
│   ├── core/              # 核心配置
│   ├── models/            # 数据模型
│   └── services/          # 业务服务
├── static/                # 静态文件
│   ├── dist/              # Vue.js 构建输出
│   ├── css/               # 原始CSS
│   └── js/                # 原始JS
├── templates/             # HTML模板
├── logs/                  # 日志文件
├── venv/                  # Python虚拟环境
├── main.py                # FastAPI 主入口
├── requirements.txt       # Python 依赖
├── start.sh               # 启动脚本
├── dev.sh                 # 快速开发脚本
└── package.json           # 项目配置
```

## ⚙️ 技术栈

### 前端
- **Vue 3** - 渐进式JavaScript框架
- **Element Plus** - Vue 3组件库
- **Pinia** - 状态管理
- **Vue Router** - 路由管理
- **ECharts** - 数据可视化
- **Axios** - HTTP客户端

### 后端
- **FastAPI** - 现代Python Web框架
- **SQLAlchemy** - ORM数据库工具
- **Redis** - 缓存和消息队列
- **WebSocket** - 实时通信
- **Uvicorn** - ASGI服务器

## 🔧 开发配置

### 环境要求
- Python 3.9+
- Node.js 16+
- Redis 6+
- npm 8+

### 端口配置
- **前端开发**: http://localhost:3000 (dev模式)
- **后端API**: http://localhost:8000
- **Redis**: 127.0.0.1:6379

### 代理配置
前端开发模式自动代理API请求到后端：
```
/api/* -> http://localhost:8000/api/*
/ws/*  -> ws://localhost:8000/ws/*
```

## 🚨 常见问题

### 1. 端口被占用
```bash
# 查看端口占用
lsof -ti:8000

# 强制终止进程
lsof -ti:8000 | xargs kill -9
```

### 2. Redis 连接失败
```bash
# 启动Redis
brew services start redis

# 检查Redis状态
redis-cli ping
```

### 3. 前端构建失败
```bash
# 重新安装依赖
cd frontend
rm -rf node_modules package-lock.json
npm install

# 跳过ESLint构建
npm run build -- --skip-plugins @vue/cli-plugin-eslint
```

### 4. Python依赖问题
```bash
# 重建虚拟环境
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install greenlet
```

## 🎯 功能特性

### 界面特性
- ✅ 现代化 Material Design 风格
- ✅ 响应式布局 (桌面/移动端)
- ✅ 明暗主题切换
- ✅ 实时数据更新
- ✅ 组件化架构

### 系统功能
- 📊 **仪表板** - 数据概览和可视化
- 🚨 **告警管理** - 告警列表和处理
- 📈 **分析统计** - 数据分析和报表
- 🔗 **接入点管理** - 数据源配置
- 👥 **用户管理** - 用户和权限
- ⚙️ **系统设置** - 配置管理

## 📝 开发说明

### 添加新页面
1. 在 `frontend/src/views/` 创建组件
2. 在 `frontend/src/router/index.js` 添加路由
3. 重新构建前端

### 添加API接口
1. 在 `src/api/` 创建路由文件
2. 在 `main.py` 注册路由
3. 重启后端服务

### 修改样式主题
- 编辑 `frontend/src/styles/variables.scss`
- 在 `frontend/src/App.vue` 中定义CSS变量

## 📄 许可证

MIT License