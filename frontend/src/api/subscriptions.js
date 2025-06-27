/**
 * 告警订阅管理 API
 */
import request from './request'

// 订阅管理
export function createSubscription(data) {
  return request({
    url: '/subscriptions/',
    method: 'post',
    data
  })
}

export function getSubscriptions(params = {}) {
  return request({
    url: '/subscriptions/',
    method: 'get',
    params
  })
}

export function getSubscription(subscriptionId) {
  return request({
    url: `/subscriptions/${subscriptionId}`,
    method: 'get'
  })
}

export function updateSubscription(subscriptionId, data) {
  return request({
    url: `/subscriptions/${subscriptionId}`,
    method: 'put',
    data
  })
}

export function deleteSubscription(subscriptionId) {
  return request({
    url: `/subscriptions/${subscriptionId}`,
    method: 'delete'
  })
}

export function testSubscription(subscriptionId, testData) {
  return request({
    url: `/subscriptions/${subscriptionId}/test`,
    method: 'post',
    data: testData
  })
}

// 通知历史
export function getNotifications(params = {}) {
  return request({
    url: '/notifications',
    method: 'get',
    params
  })
}

export function retryNotification(notificationId) {
  return request({
    url: `/notifications/${notificationId}/retry`,
    method: 'post'
  })
}

export function getNotificationStatistics(params = {}) {
  return request({
    url: '/notifications/statistics',
    method: 'get',
    params
  })
}

export function sendTestNotification(data) {
  return request({
    url: '/test-notification',
    method: 'post',
    data
  })
}

// 通知模板
export function createTemplate(data) {
  return request({
    url: '/templates/',
    method: 'post',
    data
  })
}

export function getTemplates(params = {}) {
  return request({
    url: '/templates/',
    method: 'get',
    params
  })
}

export function testTemplate(templateId, testData) {
  return request({
    url: `/templates/${templateId}/test`,
    method: 'post',
    data: testData
  })
}

export function getTemplateVariables() {
  return request({
    url: '/templates/variables',
    method: 'get'
  })
}

// 引擎状态
export function getEngineStatus() {
  return request({
    url: '/engine/status',
    method: 'get'
  })
}

// 枚举和配置
export function getSubscriptionTypes() {
  return request({
    url: '/enums/subscription-types',
    method: 'get'
  })
}

export function getNotificationStatusOptions() {
  return request({
    url: '/enums/notification-status',
    method: 'get'
  })
}

export function getFilterExamples() {
  return request({
    url: '/filter-examples',
    method: 'get'
  })
}