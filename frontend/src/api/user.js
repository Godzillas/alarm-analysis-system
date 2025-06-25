import request from './request'

export default {
  // 获取用户列表
  getUsers(params) {
    return request({
      url: '/users/',
      method: 'get',
      params
    })
  },

  // 创建用户
  createUser(data) {
    return request({
      url: '/users/',
      method: 'post',
      data
    })
  },

  // 获取用户详情
  getUserById(id) {
    return request({
      url: `/users/${id}`,
      method: 'get'
    })
  },

  // 更新用户
  updateUser(id, data) {
    return request({
      url: `/users/${id}`,
      method: 'put',
      data
    })
  },

  // 删除用户
  deleteUser(id) {
    return request({
      url: `/users/${id}`,
      method: 'delete'
    })
  },

  // 获取用户订阅
  getUserSubscriptions(userId) {
    return request({
      url: `/users/${userId}/subscriptions`,
      method: 'get'
    })
  },

  // 创建用户订阅
  createUserSubscription(userId, data) {
    return request({
      url: `/users/${userId}/subscriptions`,
      method: 'post',
      data
    })
  },

  // 更新用户订阅
  updateUserSubscription(userId, subscriptionId, data) {
    return request({
      url: `/users/${userId}/subscriptions/${subscriptionId}`,
      method: 'put',
      data
    })
  },

  // 删除用户订阅
  deleteUserSubscription(userId, subscriptionId) {
    return request({
      url: `/users/${userId}/subscriptions/${subscriptionId}`,
      method: 'delete'
    })
  },

  // 获取用户关联的系统
  getUserSystems(userId) {
    return request({
      url: `/users/${userId}/systems`,
      method: 'get'
    })
  },

  // 添加用户到系统
  addUserToSystem(userId, systemId) {
    return request({
      url: `/systems/${systemId}/users/${userId}`,
      method: 'post'
    })
  },

  // 从系统移除用户
  removeUserFromSystem(userId, systemId) {
    return request({
      url: `/systems/${systemId}/users/${userId}`,
      method: 'delete'
    })
  }
}