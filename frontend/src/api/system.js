import request from './request'

export default {
  // 获取系统列表
  getSystems(params) {
    return request({
      url: '/systems/',
      method: 'get',
      params
    })
  },

  // 创建系统
  createSystem(data) {
    return request({
      url: '/systems/',
      method: 'post',
      data
    })
  },

  // 获取系统详情
  getSystemById(id) {
    return request({
      url: `/systems/${id}`,
      method: 'get'
    })
  },

  // 更新系统
  updateSystem(id, data) {
    return request({
      url: `/systems/${id}`,
      method: 'put',
      data
    })
  },

  // 删除系统
  deleteSystem(id) {
    return request({
      url: `/systems/${id}`,
      method: 'delete'
    })
  },

  // 获取系统关联用户
  getSystemUsers(id) {
    return request({
      url: `/systems/${id}/users`,
      method: 'get'
    })
  },

  // 添加用户到系统
  addUserToSystem(systemId, userId) {
    return request({
      url: `/systems/${systemId}/users/${userId}`,
      method: 'post'
    })
  },

  // 从系统移除用户
  removeUserFromSystem(systemId, userId) {
    return request({
      url: `/systems/${systemId}/users/${userId}`,
      method: 'delete'
    })
  },

  // 获取系统统计
  getSystemStats(id) {
    return request({
      url: `/systems/${id}/stats`,
      method: 'get'
    })
  }
}