# Alertmanager安装和配置文档

## 安装位置

**二进制文件:**
- `/Users/jun/bin/alertmanager` - 主程序
- `/Users/jun/bin/amtool` - 命令行工具

**配置文件:**
- `/opt/homebrew/etc/alertmanager.yml` - 主配置文件

**数据目录:**
- `/opt/homebrew/var/lib/alertmanager` - 数据存储
- `/opt/homebrew/var/log/alertmanager.log` - 日志文件
- `/opt/homebrew/var/run/alertmanager.pid` - PID文件

**服务脚本:**
- `/opt/homebrew/etc/alertmanager_service.sh` - 服务管理脚本
- `/Users/jun/github/claude/alarm-analysis-system/alertmanager_control.sh` - 简化控制脚本

## 服务管理

### 启动/停止服务

```bash
# 启动Alertmanager
./alertmanager_control.sh start

# 停止Alertmanager  
./alertmanager_control.sh stop

# 重启Alertmanager
./alertmanager_control.sh restart

# 查看状态
./alertmanager_control.sh status
```

### 直接使用服务脚本

```bash
# 启动
/opt/homebrew/etc/alertmanager_service.sh start

# 停止
/opt/homebrew/etc/alertmanager_service.sh stop

# 状态检查
/opt/homebrew/etc/alertmanager_service.sh status
```

## 配置文件说明

### Alertmanager配置 (/opt/homebrew/etc/alertmanager.yml)

```yaml
# 全局配置
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alertmanager@example.com'

# 接收器配置
receivers:
  - name: 'alarm-system-webhook'
    webhook_configs:
      - url: 'http://localhost:8000/api/webhook/alarm/94976120befb45a29189aadedec79e94'
        send_resolved: true
        http_config:
          bearer_token: '94976120befb45a29189aadedec79e94'

# 路由配置
route:
  group_by: ['alertname']
  group_wait: 5s
  group_interval: 5s
  repeat_interval: 12h
  receiver: 'alarm-system-webhook'
  routes:
    - match:
        severity: critical
      receiver: alarm-system-webhook
      group_wait: 1s
      repeat_interval: 5m
    - match:
        severity: warning  
      receiver: alarm-system-webhook
      group_wait: 5s
      repeat_interval: 1h
```

## 服务访问

- **Web界面**: http://localhost:9093
- **API v2**: http://localhost:9093/api/v2/
- **状态检查**: http://localhost:9093/api/v2/status
- **告警列表**: http://localhost:9093/api/v2/alerts

## 与告警系统集成

Alertmanager已配置为将告警发送到告警分析系统：

- **Webhook URL**: `http://localhost:8000/api/webhook/alarm/94976120befb45a29189aadedec79e94`
- **API Token**: `94976120befb45a29189aadedec79e94`
- **字段映射**: 支持Prometheus标准格式的字段映射

## 日志查看

```bash
# 查看实时日志
tail -f /opt/homebrew/var/log/alertmanager.log

# 查看最近日志
tail -100 /opt/homebrew/var/log/alertmanager.log
```

## 故障排除

### 检查服务状态
```bash
ps aux | grep alertmanager
netstat -an | grep 9093
```

### 重新加载配置
```bash
# 重启服务以加载新配置
./alertmanager_control.sh restart
```

### 测试配置文件
```bash
/Users/jun/bin/alertmanager --config.file=/opt/homebrew/etc/alertmanager.yml --config.check
```

## 与Prometheus集成

确保Prometheus配置文件中包含Alertmanager配置：

```yaml
# prometheus.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - localhost:9093
```

## 版本信息

- **Alertmanager版本**: 0.27.0
- **安装日期**: 2025-06-25
- **来源**: 官方二进制包 alertmanager-0.27.0.darwin-arm64.tar.gz