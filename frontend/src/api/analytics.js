import request from './request'

export default {
  // 获取趋势数据
  getTrends(params) {
    return request({
      url: '/analytics/trends',
      method: 'get',
      params
    })
  },

  // 获取汇总数据
  getSummary(params) {
    return request({
      url: '/analytics/summary',
      method: 'get',
      params
    })
  },

  // 获取TOP数据
  getTopData(params) {
    return request({
      url: '/analytics/top',
      method: 'get',
      params
    })
  },

  // 获取分布数据
  getDistribution(params) {
    return request({
      url: '/analytics/distribution',
      method: 'get',
      params
    })
  },

  // 获取响应时间统计
  getResponseTime(params) {
    return request({
      url: '/analytics/response-time',
      method: 'get',
      params
    })
  }
}