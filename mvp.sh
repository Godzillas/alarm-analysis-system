#!/bin/bash

# MVP 快速启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}"
    echo "========================================"
    echo "   智能告警分析系统 MVP 启动器"
    echo "========================================"
    echo -e "${NC}"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    print_message "Docker 环境检查通过"
}

start_services() {
    print_message "正在启动服务..."
    
    # 停止已存在的服务
    docker-compose down --remove-orphans 2>/dev/null || true
    
    # 构建并启动服务
    docker-compose up --build -d
    
    # 等待服务启动
    print_message "等待服务启动完成..."
    sleep 30
    
    # 检查服务状态
    if docker-compose ps | grep -q "Up"; then
        print_message "服务启动成功"
    else
        print_error "服务启动失败，请检查日志"
        docker-compose logs
        exit 1
    fi
}

show_info() {
    echo
    print_message "🎉 MVP 启动完成！"
    echo
    echo -e "${BLUE}访问地址：${NC}"
    echo "  主页面: http://localhost:8000"
    echo "  API文档: http://localhost:8000/docs"
    echo "  管理面板: http://localhost:8000/admin"
    echo
    echo -e "${BLUE}默认账户：${NC}"
    echo "  用户名: admin"
    echo "  密码: admin123456"
    echo
    echo -e "${BLUE}测试接口：${NC}"
    echo "  Webhook: http://localhost:8000/api/webhook/alarm/demo-token"
    echo
    echo -e "${BLUE}服务管理：${NC}"
    echo "  查看日志: docker-compose logs -f"
    echo "  停止服务: docker-compose down"
    echo "  重启服务: docker-compose restart"
    echo
}

send_test_alert() {
    print_message "发送测试告警..."
    
    # 等待应用完全启动
    sleep 10
    
    curl -X POST "http://localhost:8000/api/webhook/alarm/demo-token" \
        -H "Content-Type: application/json" \
        -d '{
            "title": "测试告警",
            "description": "这是一个测试告警，用于验证系统功能",
            "severity": "high",
            "source": "mvp-test",
            "host": "localhost",
            "service": "demo-service",
            "environment": "test",
            "tags": {"type": "test", "component": "demo"}
        }' || print_warning "测试告警发送失败，请稍后手动测试"
}

main() {
    print_header
    
    case "${1:-start}" in
        "start")
            check_docker
            start_services
            show_info
            send_test_alert
            ;;
        "stop")
            print_message "停止服务..."
            docker-compose down
            print_message "服务已停止"
            ;;
        "restart")
            print_message "重启服务..."
            docker-compose down
            docker-compose up -d
            print_message "服务已重启"
            ;;
        "logs")
            docker-compose logs -f
            ;;
        "status")
            docker-compose ps
            ;;
        "clean")
            print_warning "这将删除所有数据，是否继续? (y/N)"
            read -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                docker-compose down -v
                docker system prune -f
                print_message "清理完成"
            fi
            ;;
        *)
            echo "智能告警分析系统 MVP 启动器"
            echo ""
            echo "用法: $0 [命令]"
            echo ""
            echo "命令:"
            echo "  start     启动所有服务 (默认)"
            echo "  stop      停止所有服务"
            echo "  restart   重启所有服务"
            echo "  logs      查看服务日志"
            echo "  status    查看服务状态"
            echo "  clean     清理所有数据"
            echo ""
            ;;
    esac
}

main "$@"