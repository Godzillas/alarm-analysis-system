import { defineStore } from 'pinia'
import alarmApi from '@/api/alarm'

export const useAlarmStore = defineStore('alarm', {
  state: () => ({
    alarms: [],
    stats: {
      total: 0,
      active: 0,
      resolved: 0,
      critical: 0
    },
    loading: false,
    error: null,
    pagination: {
      page: 1,
      pageSize: 20,
      total: 0
    },
    filters: {
      severity: '',
      status: '',
      source: '',
      search: '',
      system_id: null
    }
  }),

  getters: {
    activeAlarms: (state) => state.alarms.filter(alarm => alarm.status === 'active'),
    criticalAlarms: (state) => state.alarms.filter(alarm => alarm.severity === 'critical'),
    filteredAlarms: (state) => {
      let filtered = state.alarms
      
      if (state.filters.severity) {
        filtered = filtered.filter(alarm => alarm.severity === state.filters.severity)
      }
      if (state.filters.status) {
        filtered = filtered.filter(alarm => alarm.status === state.filters.status)
      }
      if (state.filters.source) {
        filtered = filtered.filter(alarm => alarm.source.includes(state.filters.source))
      }
      if (state.filters.search) {
        const search = state.filters.search.toLowerCase()
        filtered = filtered.filter(alarm => 
          alarm.title.toLowerCase().includes(search) ||
          alarm.description.toLowerCase().includes(search)
        )
      }
      if (state.filters.system_id) {
        filtered = filtered.filter(alarm => alarm.system_id === state.filters.system_id)
      }
      
      return filtered
    }
  },

  actions: {
    async fetchAlarms(params = {}) {
      this.loading = true
      this.error = null
      
      try {
        // 计算skip参数（从0开始）
        const skip = (this.pagination.page - 1) * this.pagination.pageSize
        
        const response = await alarmApi.getAlarms({
          skip: skip,
          limit: this.pagination.pageSize,
          // 只传递非空的过滤参数
          ...(this.filters.severity && { severity: this.filters.severity }),
          ...(this.filters.status && { status: this.filters.status }),
          ...(this.filters.source && { source: this.filters.source }),
          ...(this.filters.search && { search: this.filters.search }),
          ...(this.filters.system_id && { system_id: this.filters.system_id }),
          ...params
        })
        
        // 处理分页响应
        if (response.data && Array.isArray(response.data)) {
          this.alarms = response.data
          this.pagination.total = response.total || 0
          this.pagination.page = response.page || this.pagination.page
        } else if (Array.isArray(response)) {
          // 兼容旧的响应格式
          this.alarms = response
          this.pagination.total = response.length
        } else {
          this.alarms = response.data || []
          this.pagination.total = response.total || 0
        }
        
        return response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchStats() {
      try {
        const stats = await alarmApi.getStats()
        this.stats = stats
        return stats
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async acknowledgeAlarm(alarmId) {
      try {
        await alarmApi.acknowledgeAlarm(alarmId)
        const alarm = this.alarms.find(a => a.id === alarmId)
        if (alarm) {
          alarm.status = 'acknowledged'
          alarm.acknowledged_at = new Date().toISOString()
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async resolveAlarm(alarmId) {
      try {
        await alarmApi.resolveAlarm(alarmId)
        const alarm = this.alarms.find(a => a.id === alarmId)
        if (alarm) {
          alarm.status = 'resolved'
          alarm.resolved_at = new Date().toISOString()
        }
        // 更新统计
        this.stats.active = Math.max(0, this.stats.active - 1)
        this.stats.resolved += 1
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    setPage(page) {
      this.pagination.page = page
    },

    setPageSize(pageSize) {
      this.pagination.pageSize = pageSize
      this.pagination.page = 1
    },

    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
      this.pagination.page = 1
    },

    clearFilters() {
      this.filters = {
        severity: '',
        status: '',
        source: '',
        search: '',
        system_id: null
      }
      this.pagination.page = 1
    },

    // WebSocket实时更新
    addAlarm(alarm) {
      this.alarms.unshift(alarm)
      this.stats.total += 1
      this.stats.active += 1
    },

    updateAlarm(updatedAlarm) {
      const index = this.alarms.findIndex(a => a.id === updatedAlarm.id)
      if (index !== -1) {
        this.alarms[index] = updatedAlarm
      }
    },

    removeAlarm(alarmId) {
      const index = this.alarms.findIndex(a => a.id === alarmId)
      if (index !== -1) {
        this.alarms.splice(index, 1)
        this.stats.total = Math.max(0, this.stats.total - 1)
      }
    }
  }
})