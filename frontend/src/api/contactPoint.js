import request from './request'

export default {
  // 获取联络点列表
  getContactPoints(params) {
    return request({
      url: '/contact-points/',
      method: 'get',
      params
    })
  },

  // 创建联络点
  createContactPoint(data) {
    return request({
      url: '/contact-points/',
      method: 'post',
      data
    })
  },

  // 获取联络点详情
  getContactPoint(id) {
    return request({
      url: `/contact-points/${id}`,
      method: 'get'
    })
  },

  // 更新联络点
  updateContactPoint(id, data) {
    return request({
      url: `/contact-points/${id}`,
      method: 'put',
      data
    })
  },

  // 删除联络点
  deleteContactPoint(id) {
    return request({
      url: `/contact-points/${id}`,
      method: 'delete'
    })
  },

  // 测试联络点
  testContactPoint(id) {
    return request({
      url: `/contact-points/${id}/test`,
      method: 'post'
    })
  },

  // 获取联络点统计
  getContactPointStats(id) {
    return request({
      url: `/contact-points/${id}/stats`,
      method: 'get'
    })
  },

  // 获取联络点类型
  getContactPointTypes() {
    return request({
      url: '/contact-points/types/',
      method: 'get'
    })
  }
}