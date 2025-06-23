# 🚨 智能告警分析系统

一个现代化的企业级告警管理和分析平台，支持多数据源接入、实时分析、智能聚合和可视化展示。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-red.svg)

## ✨ 主要特性

### 🔌 多数据源接入
- **Prometheus** - 监控告警接入，支持AlertManager格式
- **Grafana** - 仪表板告警，支持Webhook通知
- **Zabbix** - 传统监控系统，完整的触发器支持
- **ELK Stack** - 日志告警，Elasticsearch查询告警
- **自定义API** - 灵活的告警接入，支持任意格式
- **Webhook支持** - RESTful API接口，安全令牌认证

### 📊 智能分析
- **实时聚合** - 告警数据实时统计分析
- **趋势分析** - 24小时/7天/30天趋势图表
- **关联分析** - 智能识别告警关联关系
- **严重程度分布** - 可视化告警严重程度
- **TOP统计** - 最频繁、最严重告警排行
- **自动去重** - 基于相似度的重复告警检测

### 🎯 规则引擎
- **分发规则** - 灵活的告警分发配置
- **用户订阅** - 个性化告警订阅
- **条件匹配** - 支持复杂的逻辑条件
- **状态管理** - 完整的告警生命周期

### 🖥️ 现代化界面
- **响应式设计** - 支持桌面和移动设备
- **实时更新** - WebSocket推送实时数据
- **主题切换** - 深色/浅色主题
- **交互式图表** - 丰富的数据可视化
- **企业级UI** - 现代化设计风格

## 🚀 快速开始

### 环境要求
- Python 3.8+
- FastAPI
- SQLAlchemy
- SQLite/PostgreSQL

### 安装步骤

1. **克隆仓库**
```bash
git clone https://github.com/your-username/alarm-analysis-system.git
cd alarm-analysis-system
```

2. **创建虚拟环境**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **初始化数据库和接入点**
```bash
python create_endpoints_and_test.py
```

5. **生成示例数据**
```bash
python simple_chart_data.py
```

6. **启动服务**
```bash
python main.py
```

7. **访问系统**
- 🏠 主页: http://localhost:8000
- 📊 管理后台: http://localhost:8000/admin
- 📚 API文档: http://localhost:8000/docs

### 一键测试
```bash
# 测试所有接入点功能
./test_webhook_endpoints.sh
```

## 📡 接入点配置

系统支持多种监控系统的告警接入，每个接入点都有唯一的API令牌和URL：

### Prometheus 接入示例
```bash
curl -X POST "http://localhost:8000/api/webhook/alarm/{API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "alertname": "HighCPUUsage",
    "summary": "CPU使用率过高警告",
    "severity": "critical",
    "instance": "web-server-01:9090",
    "job": "webapp",
    "labels": {
      "env": "production",
      "team": "devops"
    }
  }'
```

### Grafana 接入示例
```bash
curl -X POST "http://localhost:8000/api/webhook/alarm/{API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "磁盘空间不足警告",
    "message": "服务器磁盘使用率超过85%",
    "state": "alerting",
    "tags": {
      "instance": "db-server-02",
      "service": "database"
    }
  }'
```

### Zabbix 接入示例
```bash
curl -X POST "http://localhost:8000/api/webhook/alarm/{API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_name": "内存使用率过高",
    "trigger_description": "内存使用率超过80%",
    "trigger_severity": "4",
    "host_name": "cache-server-01",
    "item_name": "memory.util"
  }'
```

### 批量告警接收
```bash
curl -X POST "http://localhost:8000/api/webhook/batch/{API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "alertname": "HighCPUUsage",
      "severity": "critical",
      "instance": "web-01"
    },
    {
      "alertname": "HighMemoryUsage", 
      "severity": "warning",
      "instance": "web-02"
    }
  ]'
```

## 🔧 API 文档

### 告警管理
```bash
# 获取告警列表
curl "http://localhost:8000/api/alarms/?status=active&limit=10"

# 创建告警
curl -X POST "http://localhost:8000/api/alarms/" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "custom",
    "title": "应用服务异常",
    "severity": "high",
    "host": "app-server-01"
  }'

# 更新告警状态
curl -X PUT "http://localhost:8000/api/alarms/1" \
  -H "Content-Type: application/json" \
  -d '{"status": "resolved"}'
```

### 分析统计
```bash
# 获取告警汇总
curl "http://localhost:8000/api/analytics/summary?time_range=24h"

# 获取告警趋势
curl "http://localhost:8000/api/analytics/trends?time_range=24h&interval=1h"

# 获取TOP告警
curl "http://localhost:8000/api/analytics/top?time_range=24h&limit=10"
```

### 接入点管理
```bash
# 获取接入点列表
curl "http://localhost:8000/api/endpoints/"

# 创建接入点
curl -X POST "http://localhost:8000/api/endpoints/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "prometheus-alerts",
    "endpoint_type": "webhook",
    "description": "Prometheus告警接入"
  }'

# 测试接入点
curl "http://localhost:8000/api/webhook/test/{API_TOKEN}"
```

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   监控系统      │    │   告警系统      │    │   用户界面      │
│                 │    │                 │    │                 │
│ Prometheus      │───▶│ Webhook API     │───▶│ Web Dashboard   │
│ Grafana         │    │ Rule Engine     │    │ Real-time UI    │
│ Zabbix          │    │ Aggregator      │    │ API Docs        │
│ ELK Stack       │    │ Analyzer        │    │ Mobile Ready    │
│ Custom APIs     │    │ WebSocket       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 项目结构

```
alarm-analysis-system/
├── src/                    # 源代码目录
│   ├── api/               # API路由和端点
│   │   └── routers.py     # 主要路由定义
│   ├── core/              # 核心配置
│   │   ├── config.py      # 系统配置
│   │   └── database.py    # 数据库配置
│   ├── models/            # 数据模型
│   │   └── alarm.py       # 告警相关模型
│   ├── services/          # 业务服务
│   │   ├── collector.py   # 告警收集服务
│   │   ├── analyzer.py    # 智能分析服务
│   │   ├── aggregator.py  # 聚合统计服务
│   │   ├── endpoint_manager.py  # 接入点管理
│   │   ├── user_manager.py      # 用户管理
│   │   ├── rule_engine.py       # 规则引擎
│   │   └── websocket_manager.py # WebSocket管理
│   └── utils/             # 工具函数
│       └── logger.py      # 日志工具
├── static/                # 静态资源
│   ├── css/              # 样式文件
│   │   └── modern.css    # 现代化CSS框架
│   └── js/               # JavaScript文件
│       ├── modern-framework.js  # 前端框架
│       └── admin-app.js         # 管理应用
├── templates/             # HTML模板
│   └── modern-admin.html  # 现代化管理界面
├── main.py               # 应用入口点
├── requirements.txt      # Python依赖
├── create_endpoints_and_test.py  # 初始化脚本
├── simple_chart_data.py          # 数据生成脚本
└── README.md            # 项目文档
```

## 🧪 测试

### 自动化测试
```bash
# 完整功能测试
python complete_test.py

# 生成图表数据
python simple_chart_data.py

# 测试所有接入点
./test_webhook_endpoints.sh
```

### 手动测试
```bash
# 创建测试接入点和用户
python create_endpoints_and_test.py

# 检查API状态
curl http://localhost:8000/api/alarms/stats/summary

# 查看接入点
curl http://localhost:8000/api/endpoints/
```

## 🔧 配置说明

### 环境变量
```bash
# 数据库配置
DATABASE_URL=sqlite:///alarm_system.db

# 服务配置
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Redis配置（可选）
REDIS_URL=redis://localhost:6379

# 日志配置
LOG_LEVEL=INFO
```

### 接入点配置
每个接入点支持以下配置选项：
- `field_mapping`: 字段映射配置
- `severity_mapping`: 严重程度映射
- `default_severity`: 默认严重程度
- `rate_limit`: 请求限流设置

## 🚀 部署

### Docker 部署
```bash
# 构建镜像
docker build -t alarm-system .

# 运行容器
docker run -p 8000:8000 alarm-system
```

### 生产环境
```bash
# 使用 Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app

# 使用 Uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL工具包
- [Chart.js](https://www.chartjs.org/) - 优秀的图表库

## 📞 联系

如有问题或建议，请通过以下方式联系：

- 提交 [Issue](https://github.com/your-username/alarm-analysis-system/issues)
- 发送邮件: your-email@example.com

---

⭐ 如果这个项目对你有帮助，请给它一个星标！