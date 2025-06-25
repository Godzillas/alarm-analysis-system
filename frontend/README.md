# 告警分析系统前端

基于 Vue 3 + Element Plus 构建的现代化告警分析系统前端。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **Element Plus** - Vue 3 组件库
- **Pinia** - Vue 状态管理
- **Vue Router** - 官方路由
- **ECharts** - 数据可视化
- **Axios** - HTTP 客户端
- **Sass** - CSS 预处理器

## 项目结构

```
frontend/
├── public/                 # 静态资源
├── src/
│   ├── api/               # API 接口
│   ├── components/        # 公共组件
│   │   ├── Layout/        # 布局组件
│   │   └── Dashboard/     # 仪表板组件
│   ├── router/            # 路由配置
│   ├── store/             # 状态管理
│   ├── styles/            # 全局样式
│   ├── utils/             # 工具函数
│   ├── views/             # 页面组件
│   ├── App.vue            # 根组件
│   └── main.js            # 入口文件
├── package.json
├── vue.config.js          # Vue CLI 配置
└── README.md
```

## 开发指南

### 安装依赖

```bash
cd frontend
npm install
```

### 开发模式

```bash
npm run serve
```

访问 http://localhost:3000

### 构建生产版本

```bash
npm run build
```

构建产物将输出到 `../static/dist/` 目录。

### 代码检查

```bash
npm run lint
```

## 功能特性

### 🎨 现代化设计
- 基于 Element Plus 设计语言
- 支持明暗主题切换
- 响应式布局设计

### 📊 数据可视化
- ECharts 图表集成
- 实时数据更新
- 多种图表类型支持

### 🔧 开发体验
- TypeScript 支持
- 热重载开发
- 组件自动导入
- ESLint + Prettier

### 🚀 性能优化
- 代码分割
- 懒加载路由
- 组件按需加载
- 生产环境优化

## 页面结构

- **仪表板** - 系统概览和统计数据
- **告警管理** - 告警列表和处理
- **分析统计** - 数据分析和报表
- **接入点管理** - 数据源管理
- **用户管理** - 用户和权限管理
- **规则管理** - 告警规则配置
- **系统设置** - 系统参数配置

## 组件说明

### Layout 组件
- `Layout/index.vue` - 主布局容器
- `Layout/Sidebar.vue` - 侧边导航栏
- `Layout/Header.vue` - 顶部导航栏

### Dashboard 组件
- `Dashboard/StatsCard.vue` - 统计卡片
- `Dashboard/TrendChart.vue` - 趋势图表
- `Dashboard/SeverityChart.vue` - 严重程度分布
- `Dashboard/RecentAlarmsList.vue` - 最新告警列表

## 状态管理

使用 Pinia 进行状态管理：

- `theme.js` - 主题和界面状态
- `alarm.js` - 告警数据状态
- 更多 store 模块...

## API 集成

所有 API 调用都通过 `src/api/` 目录下的模块处理：

- `request.js` - 请求拦截器和错误处理
- `alarm.js` - 告警相关 API
- `analytics.js` - 分析统计 API

## 主题定制

支持明暗主题切换，可在 `src/styles/` 目录下定制：

- `variables.scss` - SCSS 变量
- `index.scss` - 全局样式
- `reset.scss` - 重置样式

## 浏览器支持

- Chrome >= 80
- Firefox >= 74
- Safari >= 13
- Edge >= 80

## 开发规范

### 组件命名
- 使用 PascalCase 命名组件文件
- 组件名称应具有描述性

### 样式规范
- 使用 scoped 样式
- 遵循 BEM 命名规范
- 使用 SCSS 变量保持一致性

### 代码规范
- 使用 ESLint + Prettier
- 遵循 Vue 3 Composition API 最佳实践
- 适当添加注释