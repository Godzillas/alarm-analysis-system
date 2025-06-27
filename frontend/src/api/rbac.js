/**
 * 权限管理 API
 */
import request from './request'

// 用户管理
export function getUsers(params = {}) {
  return request({
    url: '/users/',
    method: 'get',
    params
  })
}

export function createUser(data) {
  return request({
    url: '/users/',
    method: 'post',
    data
  })
}

export function updateUser(userId, data) {
  return request({
    url: `/users/${userId}`,
    method: 'put',
    data
  })
}

export function deleteUser(userId) {
  return request({
    url: `/users/${userId}`,
    method: 'delete'
  })
}

export function getUserProfile(userId) {
  return request({
    url: `/users/${userId}/profile`,
    method: 'get'
  })
}

// 角色管理
export function getRoles(params = {}) {
  return request({
    url: '/roles/',
    method: 'get',
    params
  })
}

export function createRole(data) {
  return request({
    url: '/roles/',
    method: 'post',
    data
  })
}

export function updateRole(roleId, data) {
  return request({
    url: `/roles/${roleId}`,
    method: 'put',
    data
  })
}

export function deleteRole(roleId) {
  return request({
    url: `/roles/${roleId}`,
    method: 'delete'
  })
}

// 权限管理
export function getPermissions() {
  return request({
    url: '/permissions',
    method: 'get'
  })
}

export function getUserPermissions(userId) {
  return request({
    url: `/users/${userId}/permissions`,
    method: 'get'
  })
}

export function assignUserRoles(userId, roleIds) {
  return request({
    url: `/users/${userId}/roles`,
    method: 'post',
    data: { role_ids: roleIds }
  })
}

export function revokeUserRoles(userId, roleIds) {
  return request({
    url: `/users/${userId}/roles`,
    method: 'delete',
    data: { role_ids: roleIds }
  })
}

export function assignRolePermissions(roleId, permissionIds) {
  return request({
    url: `/roles/${roleId}/permissions`,
    method: 'post',
    data: { permission_ids: permissionIds }
  })
}

export function revokeRolePermissions(roleId, permissionIds) {
  return request({
    url: `/roles/${roleId}/permissions`,
    method: 'delete',
    data: { permission_ids: permissionIds }
  })
}

// 组织管理
export function getOrganizations(params = {}) {
  return request({
    url: '/organizations',
    method: 'get',
    params
  })
}

export function createOrganization(data) {
  return request({
    url: '/organizations',
    method: 'post',
    data
  })
}

export function updateOrganization(orgId, data) {
  return request({
    url: `/organizations/${orgId}`,
    method: 'put',
    data
  })
}

export function getOrganizationMembers(orgId, params = {}) {
  return request({
    url: `/organizations/${orgId}/members`,
    method: 'get',
    params
  })
}

export function addOrganizationMember(orgId, data) {
  return request({
    url: `/organizations/${orgId}/members`,
    method: 'post',
    data
  })
}

export function removeOrganizationMember(orgId, userId) {
  return request({
    url: `/organizations/${orgId}/members/${userId}`,
    method: 'delete'
  })
}

// 认证管理
export function login(credentials) {
  return request({
    url: '/auth/login',
    method: 'post',
    data: credentials
  })
}

export function logout() {
  return request({
    url: '/auth/logout',
    method: 'post'
  })
}

export function refreshToken() {
  return request({
    url: '/auth/refresh',
    method: 'post'
  })
}

export function getCurrentUser() {
  return request({
    url: '/auth/me',
    method: 'get'
  })
}

export function changePassword(data) {
  return request({
    url: '/auth/change-password',
    method: 'post',
    data
  })
}

export function resetPassword(email) {
  return request({
    url: '/auth/reset-password',
    method: 'post',
    data: { email }
  })
}

// API 密钥管理
export function getApiKeys(params = {}) {
  return request({
    url: '/api-keys',
    method: 'get',
    params
  })
}

export function createApiKey(data) {
  return request({
    url: '/api-keys',
    method: 'post',
    data
  })
}

export function deleteApiKey(keyId) {
  return request({
    url: `/api-keys/${keyId}`,
    method: 'delete'
  })
}

export function updateApiKeyPermissions(keyId, permissions) {
  return request({
    url: `/api-keys/${keyId}/permissions`,
    method: 'put',
    data: { permissions }
  })
}