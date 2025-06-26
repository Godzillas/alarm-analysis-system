# 开发指南

## 启动项目

### 开发模式（推荐）
```bash
# 启动开发模式，支持热重载
./dev.sh
```

开发模式特性：
- 🎨 前端开发服务器: http://localhost:8080 (支持热重载)
- 🔥 后端API服务器: http://localhost:8000 (支持热重载)
- 📚 API文档: http://localhost:8000/docs
- 📝 前端日志: `tail -f logs/frontend.log`
- ⚡ 修改前端代码后自动刷新浏览器
- 🔄 修改后端代码后自动重启服务器

### 生产模式
```bash
# 构建并启动生产版本
./dev.sh prod
```

## 前端样式规范

### 表单控件尺寸规范

已统一定义了表单控件的标准尺寸，使用CSS类名：

#### 下拉框 (el-select)
```vue
<!-- 语义化类名 -->
<el-select class="el-select--status">     <!-- 120px - 状态类型 -->
<el-select class="el-select--severity">   <!-- 120px - 严重程度 -->
<el-select class="el-select--type">       <!-- 160px - 一般类型 -->
<el-select class="el-select--system">     <!-- 200px - 系统选择 -->
<el-select class="el-select--user">       <!-- 200px - 用户选择 -->

<!-- 尺寸类名 -->
<el-select class="el-select--xs">         <!-- 80px -->
<el-select class="el-select--sm">         <!-- 120px -->
<el-select class="el-select--md">         <!-- 160px -->
<el-select class="el-select--lg">         <!-- 200px -->
<el-select class="el-select--xl">         <!-- 240px -->
```

#### 输入框 (el-input)
```vue
<!-- 语义化类名 -->
<el-input class="el-input--search">       <!-- 200px - 搜索框 -->
<el-input class="el-input--name">         <!-- 280px - 名称输入 -->
<el-input class="el-input--url">          <!-- 360px - URL输入 -->

<!-- 尺寸类名 -->
<el-input class="el-input--xs">           <!-- 80px -->
<el-input class="el-input--sm">           <!-- 120px -->
<el-input class="el-input--md">           <!-- 200px -->
<el-input class="el-input--lg">           <!-- 280px -->
<el-input class="el-input--xl">           <!-- 360px -->
```

#### 筛选表单
```vue
<el-form :model="filters" inline class="filter-form">
  <!-- 自动应用间距和响应式布局 -->
</el-form>
```

### 响应式设计

样式已支持响应式：
- 大屏 (>1200px): 标准尺寸
- 中屏 (768px-1200px): 适中缩减
- 小屏 (<768px): 紧凑布局

## 开发最佳实践

### 1. 表单筛选器
```vue
<template>
  <div class="filters">
    <el-form :model="filters" inline class="filter-form">
      <el-form-item label="状态">
        <el-select 
          v-model="filters.status" 
          placeholder="全部" 
          clearable
          class="el-select--status"
          @change="handleStatusChange"
        >
          <el-option label="活跃" value="active" />
        </el-select>
      </el-form-item>
    </el-form>
  </div>
</template>
```

### 2. 样式文件组织
```
src/styles/
├── index.scss          # 主样式文件
├── variables.scss      # CSS变量
├── reset.scss         # 重置样式
├── transitions.scss   # 过渡动画
└── form-controls.scss # 表单控件规范（新增）
```

### 3. 组件规范
- 使用语义化的CSS类名
- 遵循Element Plus设计规范
- 支持响应式布局
- 保持一致的间距和字体

## 项目结构

```
alarm-analysis-system/
├── frontend/           # Vue.js前端
│   ├── src/
│   │   ├── views/      # 页面组件
│   │   ├── components/ # 通用组件
│   │   ├── styles/     # 样式文件
│   │   └── store/      # Pinia状态管理
├── src/               # Python后端
│   ├── api/           # API路由
│   ├── models/        # 数据模型
│   ├── services/      # 业务逻辑
│   └── core/          # 核心配置
├── static/            # 静态文件（生产构建）
├── requirements.txt   # Python依赖
├── dev.sh            # 开发启动脚本
└── logs/             # 日志文件
```

## 常用命令

```bash
# 安装依赖（使用国内源）
./install_deps.sh

# 启动开发模式
./dev.sh

# 启动生产模式
./dev.sh prod

# 查看前端日志
tail -f logs/frontend.log

# 重启服务
# 开发模式: Ctrl+C 然后重新运行 ./dev.sh
# 生产模式: 同样使用 Ctrl+C 停止

# 清理端口（如有冲突）
lsof -ti:8000 | xargs kill -9
lsof -ti:8080 | xargs kill -9
```

## 故障排除

### 端口占用
如果遇到端口占用，脚本会自动清理，也可手动清理：
```bash
lsof -ti:8000 | xargs kill -9  # 清理后端端口
lsof -ti:8080 | xargs kill -9  # 清理前端端口
```

### 依赖问题
```bash
# 重新安装Python依赖
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements.txt

# 重新安装前端依赖
cd frontend && npm install
```

### 数据库连接
确保MySQL服务已启动：
```bash
brew services start mysql
```

### Redis连接
确保Redis服务已启动：
```bash
brew services start redis
```