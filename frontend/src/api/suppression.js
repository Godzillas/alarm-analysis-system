/**
 * 告警抑制管理 API
 */
import request from './request'

// 抑制规则管理
export function createSuppression(data) {
  return request({
    url: '/suppressions/',
    method: 'post',
    data
  })
}

export function getSuppressions(params = {}) {
  return request({
    url: '/suppressions/',
    method: 'get',
    params
  })
}

export function getSuppression(suppressionId) {
  return request({
    url: `/suppressions/${suppressionId}`,
    method: 'get'
  })
}

export function updateSuppression(suppressionId, data) {
  return request({
    url: `/suppressions/${suppressionId}`,
    method: 'put',
    data
  })
}

export function deleteSuppression(suppressionId) {
  return request({
    url: `/suppressions/${suppressionId}`,
    method: 'delete'
  })
}

export function testSuppressionRule(data) {
  return request({
    url: '/suppressions/test',
    method: 'post',
    data
  })
}

export function getSuppressionTemplates() {
  return request({
    url: '/suppressions/templates',
    method: 'get'
  })
}

// 维护窗口管理
export function createMaintenanceWindow(data) {
  return request({
    url: '/maintenance-windows/',
    method: 'post',
    data
  })
}

export function getMaintenanceWindows(params = {}) {
  return request({
    url: '/maintenance-windows/',
    method: 'get',
    params
  })
}

// 依赖关系管理
export function createDependencyMap(data) {
  return request({
    url: '/dependencies',
    method: 'post',
    data
  })
}

// 抑制统计和状态
export function getSuppressionStats(params = {}) {
  return request({
    url: '/suppressions/stats/summary',
    method: 'get',
    params
  })
}

export function pauseSuppression(suppressionId) {
  return request({
    url: `/suppressions/${suppressionId}/pause`,
    method: 'post'
  })
}

export function resumeSuppression(suppressionId) {
  return request({
    url: `/suppressions/${suppressionId}/resume`,
    method: 'post'
  })
}

export function reloadSuppressionCache() {
  return request({
    url: '/suppressions/reload-cache',
    method: 'post'
  })
}

// 条件验证
export function validateSuppressionConditions(conditions) {
  return request({
    url: '/suppressions/validate-conditions',
    method: 'post',
    data: conditions
  })
}

// 抑制日志
export function getSuppressionLogs(suppressionId, params = {}) {
  return request({
    url: `/suppressions/${suppressionId}/logs`,
    method: 'get',
    params
  })
}

// 批量操作
export function batchPauseSuppressions(suppressionIds) {
  return request({
    url: '/suppressions/batch-pause',
    method: 'post',
    data: suppressionIds
  })
}

export function batchResumeSuppressions(suppressionIds) {
  return request({
    url: '/suppressions/batch-resume',
    method: 'post',
    data: suppressionIds
  })
}