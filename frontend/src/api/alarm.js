import request from './request'

export default {
  // 获取告警列表
  getAlarms(params) {
    return request({
      url: '/alarms/',
      method: 'get',
      params
    })
  },

  // 获取告警统计
  getStats(params) {
    return request({
      url: '/alarms/stats/summary',
      method: 'get',
      params
    })
  },

  // 获取告警详情
  getAlarmById(id) {
    return request({
      url: `/alarms/${id}`,
      method: 'get'
    })
  },

  // 确认告警
  acknowledgeAlarm(id) {
    return request({
      url: `/alarms/${id}/acknowledge`,
      method: 'post'
    })
  },

  // 解决告警
  resolveAlarm(id) {
    return request({
      url: `/alarms/${id}/resolve`,
      method: 'post'
    })
  },

  // 批量操作告警
  batchOperation(action, alarmIds) {
    return request({
      url: '/alarms/batch',
      method: 'post',
      data: {
        action,
        alarm_ids: alarmIds
      }
    })
  },

  // 创建告警
  createAlarm(data) {
    return request({
      url: '/alarms/',
      method: 'post',
      data
    })
  },

  // 更新告警
  updateAlarm(id, data) {
    return request({
      url: `/alarms/${id}`,
      method: 'put',
      data
    })
  },

  // 删除告警
  deleteAlarm(id) {
    return request({
      url: `/alarms/${id}`,
      method: 'delete'
    })
  }
}