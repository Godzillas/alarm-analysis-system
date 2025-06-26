#!/bin/bash
# Alertmanager控制脚本 - 模拟brew services接口

case "$1" in
    "start")
        echo "Starting alertmanager..."
        /opt/homebrew/etc/alertmanager_service.sh start
        ;;
    "stop")
        echo "Stopping alertmanager..."
        /opt/homebrew/etc/alertmanager_service.sh stop
        ;;
    "restart")
        echo "Restarting alertmanager..."
        /opt/homebrew/etc/alertmanager_service.sh restart
        ;;
    "status")
        /opt/homebrew/etc/alertmanager_service.sh status
        ;;
    "list")
        echo "Available services:"
        echo "  alertmanager   (running)" if /opt/homebrew/etc/alertmanager_service.sh status >/dev/null 2>&1
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|list}"
        echo ""
        echo "管理Alertmanager服务的命令:"
        echo "  start   - 启动Alertmanager"
        echo "  stop    - 停止Alertmanager"  
        echo "  restart - 重启Alertmanager"
        echo "  status  - 查看Alertmanager状态"
        echo "  list    - 列出服务状态"
        echo ""
        echo "示例:"
        echo "  $0 start"
        echo "  $0 status"
        exit 1
        ;;
esac