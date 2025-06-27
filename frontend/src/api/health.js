/**
 * 系统健康监控 API
 */
import request from './request'

// 系统健康检查
export function getSystemHealth() {
  return request({
    url: '/health/',
    method: 'get'
  })
}

export function getSystemStatus() {
  return request({
    url: '/health/status',
    method: 'get'
  })
}

export function getSystemMetrics() {
  return request({
    url: '/health/metrics',
    method: 'get'
  })
}

export function getSystemInfo() {
  return request({
    url: '/health/info',
    method: 'get'
  })
}

// 组件健康检查
export function getDatabaseHealth() {
  return request({
    url: '/health/database',
    method: 'get'
  })
}

export function getRedisHealth() {
  return request({
    url: '/health/redis',
    method: 'get'
  })
}

export function getWebSocketHealth() {
  return request({
    url: '/health/websocket',
    method: 'get'
  })
}

export function getNotificationHealth() {
  return request({
    url: '/health/notification',
    method: 'get'
  })
}

// 性能监控
export function getPerformanceMetrics(params = {}) {
  return request({
    url: '/health/performance',
    method: 'get',
    params
  })
}

export function getResourceUsage() {
  return request({
    url: '/health/resources',
    method: 'get'
  })
}

export function getServiceDependencies() {
  return request({
    url: '/health/dependencies',
    method: 'get'
  })
}

// 健康检查配置
export function getHealthCheckConfig() {
  return request({
    url: '/health/config',
    method: 'get'
  })
}

export function updateHealthCheckConfig(config) {
  return request({
    url: '/health/config',
    method: 'put',
    data: config
  })
}

// 监控告警
export function getHealthAlerts(params = {}) {
  return request({
    url: '/health/alerts',
    method: 'get',
    params
  })
}

export function acknowledgeHealthAlert(alertId) {
  return request({
    url: `/health/alerts/${alertId}/acknowledge`,
    method: 'post'
  })
}

// 历史数据
export function getHealthHistory(params = {}) {
  return request({
    url: '/health/history',
    method: 'get',
    params
  })
}

export function getUptimeStats(params = {}) {
  return request({
    url: '/health/uptime',
    method: 'get',
    params
  })
}