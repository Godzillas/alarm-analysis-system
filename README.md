# 智能告警分析系统

> 基于人工智能的企业级告警管理平台

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-red.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

## 🎯 项目概述

智能告警分析系统是一个现代化的告警管理平台，专注于通过AI技术提升告警处理效率。系统采用微服务架构，支持多种监控系统集成，提供智能告警聚合、关联分析、通知分发等核心功能。

### 核心特性

- 🤖 **AI驱动**: 基于机器学习的重复告警检测和关联分析
- 🔗 **多源集成**: 支持Prometheus、Grafana、Webhook等多种数据源
- 📧 **多渠道通知**: 支持邮件、飞书、钉钉、企业微信等8种通知渠道
- 🎨 **灵活模板**: 基于Jinja2的强大模板系统
- 📊 **实时分析**: 提供丰富的数据分析和可视化能力
- 🏗️ **现代架构**: FastAPI + Vue3 + MySQL + Redis 技术栈

### 环境要求

- Docker & Docker Compose
- 8GB+ 内存
- 端口 3306, 6379, 8000 可用

### 一键启动

```bash
# 克隆项目
git clone <repository-url>
cd alarm

# 启动MVP
./mvp.sh start
```

启动完成后访问：
- **主页面**: http://localhost:8000
- **API文档**: http://localhost:8000/docs  
- **MVP演示**: http://localhost:8000/mvp

### 默认账户

- **用户名**: admin
- **密码**: admin123456

## 📋 功能模块

### 告警管理
- 告警收集与处理
- 重复告警智能检测
- 告警状态生命周期管理
- 批量操作支持

### 智能分析
- 基于TF-IDF的文本相似度分析
- 多维度告警关联分析
- 实时统计和趋势分析
- 自定义聚合规则

### 通知系统
- 多渠道通知支持
- 灵活的模板系统
- 通知规则引擎
- 发送状态跟踪

### 用户管理
- 基于JWT的身份认证
- 角色权限控制
- 系统级数据隔离
- 订阅管理

### 系统管理
- 多系统支持
- 接入点管理
- 联络点配置
- 实时监控面板

## 🛠️ 开发指南

### 本地开发

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置数据库等信息

# 启动服务
python main.py
```

### 项目结构

```
alarm/
├── src/                    # 源代码
│   ├── api/               # API路由
│   ├── core/              # 核心配置
│   ├── models/            # 数据模型
│   ├── services/          # 业务服务
│   └── utils/             # 工具函数
├── static/                # 静态文件
├── scripts/               # 脚本工具
├── docs/                  # 文档
├── docker-compose.yml     # Docker配置
├── Dockerfile            # 容器构建
├── requirements.txt      # Python依赖
└── mvp.sh               # MVP启动脚本
```

### API接口

系统提供完整的RESTful API，详细文档见：http://localhost:8000/docs

主要接口：
- `/api/alarms/` - 告警管理
- `/api/auth/` - 用户认证
- `/api/systems/` - 系统管理
- `/api/contact-points/` - 联络点管理
- `/api/webhook/` - Webhook接入

## 🧪 测试与验证

### 发送测试告警

```bash
# 使用测试脚本
python scripts/test_alerts.py --count 10

# 或使用curl
curl -X POST "http://localhost:8000/api/webhook/alarm/demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试告警",
    "description": "这是一个测试告警",
    "severity": "high",
    "source": "test",
    "host": "localhost",
    "service": "demo"
  }'
```

### 验证功能

1. **告警接收**: 通过Webhook发送告警
2. **重复检测**: 发送相似告警验证聚合功能
3. **通知测试**: 配置联络点并测试通知
4. **API测试**: 通过API文档测试各种接口

## 📊 监控与运维

### 日志查看

```bash
# 查看应用日志
docker-compose logs -f alarm_app

# 查看所有服务日志
docker-compose logs -f
```

### 性能监控

- **应用指标**: /api/analytics/summary
- **系统状态**: /api/dashboard/metrics
- **健康检查**: /docs

### 数据备份

```bash
# 备份MySQL数据
docker exec alarm_mysql mysqldump -u alarm_user -p alarm_system > backup.sql

# 备份Redis数据
docker exec alarm_redis redis-cli BGSAVE
```

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DATABASE_URL | 数据库连接URL | mysql+aiomysql://... |
| REDIS_URL | Redis连接URL | redis://localhost:6379/0 |
| SECRET_KEY | JWT密钥 | 需要修改 |
| DEBUG | 调试模式 | false |
| LOG_LEVEL | 日志级别 | INFO |

详细配置参见 `.env.example` 文件。

### 通知渠道配置

支持的通知渠道：
- **邮件**: SMTP配置
- **飞书**: Webhook URL
- **钉钉**: Webhook URL + 签名
- **企业微信**: Webhook URL
- **Slack**: Webhook URL
- **短信**: 第三方SMS服务
- **自定义**: Webhook

## 🚀 部署指南

### Docker部署 (推荐)

```bash
# 生产环境部署
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Kubernetes部署

```bash
# 使用Helm部署
helm install alarm-system ./helm/alarm-system
```

### 传统部署

详见文档：[部署指南](docs/deployment.md)

## 🤝 贡献指南

欢迎贡献代码！请阅读 [贡献指南](CONTRIBUTING.md) 了解更多信息。

### 开发流程

1. Fork 项目
2. 创建特性分支
3. 提交变更
4. 创建Pull Request

### 代码规范

- Python: PEP8 + Black
- TypeScript: ESLint + Prettier
- 提交信息: Conventional Commits

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

## 🔗 相关链接

- [产品功能对比分析](docs/product-analysis.md)
- [API文档](http://localhost:8000/docs)
- [技术架构文档](docs/architecture.md)
- [常见问题](docs/faq.md)

## 📞 联系我们

- 项目仓库: [GitHub](https://github.com/your-org/alarm-system)
- 问题反馈: [Issues](https://github.com/your-org/alarm-system/issues)
- 邮箱: support@example.com

---

⭐ 如果这个项目对你有帮助，请给我们一个Star！