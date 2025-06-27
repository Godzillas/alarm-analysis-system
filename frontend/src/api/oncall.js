/**
 * 值班管理 API
 */
import request from './request'

// 团队管理
export function createTeam(data) {
  return request({
    url: '/teams',
    method: 'post',
    data
  })
}

export function getTeams() {
  return request({
    url: '/teams',
    method: 'get'
  })
}

export function getTeam(teamId) {
  return request({
    url: `/teams/${teamId}`,
    method: 'get'
  })
}

export function updateTeam(teamId, data) {
  return request({
    url: `/teams/${teamId}`,
    method: 'put',
    data
  })
}

export function deleteTeam(teamId) {
  return request({
    url: `/teams/${teamId}`,
    method: 'delete'
  })
}

// 团队成员管理
export function addTeamMember(teamId, data) {
  return request({
    url: `/teams/${teamId}/members`,
    method: 'post',
    data
  })
}

export function getTeamMembers(teamId) {
  return request({
    url: `/teams/${teamId}/members`,
    method: 'get'
  })
}

export function getCurrentOncall(teamId) {
  return request({
    url: `/teams/${teamId}/current-oncall`,
    method: 'get'
  })
}

// 值班计划管理
export function createSchedule(data) {
  return request({
    url: '/schedules',
    method: 'post',
    data
  })
}

export function getSchedules(params = {}) {
  return request({
    url: '/schedules',
    method: 'get',
    params
  })
}

export function getTeamSchedule(teamId, params = {}) {
  return request({
    url: `/teams/${teamId}/schedule`,
    method: 'get',
    params
  })
}

// 值班覆盖
export function createOverride(data) {
  return request({
    url: '/overrides',
    method: 'post',
    data
  })
}

// 升级策略
export function createEscalationPolicy(data) {
  return request({
    url: '/escalation-policies',
    method: 'post',
    data
  })
}

export function getEscalationPolicies(params = {}) {
  return request({
    url: '/escalation-policies',
    method: 'get',
    params
  })
}

// 升级处理
export function triggerEscalation(alarmId, params = {}) {
  return request({
    url: `/escalation/${alarmId}/trigger`,
    method: 'post',
    params
  })
}

export function acknowledgeEscalation(alarmId) {
  return request({
    url: `/escalation/${alarmId}/acknowledge`,
    method: 'post'
  })
}

export function resolveEscalation(alarmId) {
  return request({
    url: `/escalation/${alarmId}/resolve`,
    method: 'post'
  })
}

export function getEscalationStatus(alarmId) {
  return request({
    url: `/escalation/${alarmId}/status`,
    method: 'get'
  })
}

export function getActiveEscalations() {
  return request({
    url: '/escalations/active',
    method: 'get'
  })
}

// 统计信息
export function getMemberStats(memberId, params = {}) {
  return request({
    url: `/members/${memberId}/stats`,
    method: 'get',
    params
  })
}