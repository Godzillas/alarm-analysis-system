import { defineStore } from 'pinia'
import systemApi from '@/api/system'

export const useSystemStore = defineStore('system', {
  state: () => ({
    systems: [],
    loading: false,
    error: null,
    pagination: {
      page: 1,
      pageSize: 20,
      total: 0
    },
    filters: {
      search: '',
      enabled: null
    },
    currentSystem: null,
    systemUsers: []
  }),

  getters: {
    enabledSystems: (state) => state.systems.filter(system => system.enabled),
    disabledSystems: (state) => state.systems.filter(system => !system.enabled),
    systemOptions: (state) => state.systems.map(system => ({
      label: system.name,
      value: system.id,
      code: system.code
    }))
  },

  actions: {
    async fetchSystems(params = {}) {
      this.loading = true
      this.error = null
      
      try {
        const response = await systemApi.getSystems({
          page: this.pagination.page,
          page_size: this.pagination.pageSize,
          ...this.filters,
          ...params
        })
        
        // 确保响应格式正确
        if (response && response.data) {
          this.systems = response.data
          this.pagination.total = response.total || 0
          this.pagination.page = response.page || 1
          this.pagination.pageSize = response.page_size || 20
        } else if (Array.isArray(response)) {
          // 兼容直接返回数组的情况
          this.systems = response
          this.pagination.total = response.length
        } else {
          console.warn('Unexpected response format:', response)
          this.systems = []
          this.pagination.total = 0
        }
        
        return response
      } catch (error) {
        this.error = error.message || '获取系统列表失败'
        this.systems = []
        this.pagination.total = 0
        throw error
      } finally {
        this.loading = false
      }
    },

    async createSystem(systemData) {
      try {
        const response = await systemApi.createSystem(systemData)
        
        // 如果当前在第一页，直接添加到列表
        if (this.pagination.page === 1) {
          this.systems.unshift(response)
        }
        
        // 更新总数
        this.pagination.total += 1
        
        return response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async updateSystem(id, systemData) {
      try {
        const response = await systemApi.updateSystem(id, systemData)
        
        // 更新列表中的系统
        const index = this.systems.findIndex(s => s.id === id)
        if (index !== -1) {
          this.systems[index] = response
        }
        
        // 更新当前系统
        if (this.currentSystem && this.currentSystem.id === id) {
          this.currentSystem = response
        }
        
        return response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async deleteSystem(id) {
      try {
        await systemApi.deleteSystem(id)
        
        // 从列表中移除
        const index = this.systems.findIndex(s => s.id === id)
        if (index !== -1) {
          this.systems.splice(index, 1)
          this.pagination.total -= 1
        }
        
        // 清除当前系统
        if (this.currentSystem && this.currentSystem.id === id) {
          this.currentSystem = null
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async getSystemById(id) {
      try {
        const response = await systemApi.getSystemById(id)
        this.currentSystem = response
        return response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async getSystemUsers(id) {
      try {
        const response = await systemApi.getSystemUsers(id)
        this.systemUsers = response
        return response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async addUserToSystem(systemId, userId) {
      try {
        await systemApi.addUserToSystem(systemId, userId)
        
        // 重新获取系统用户列表
        if (this.currentSystem && this.currentSystem.id === systemId) {
          await this.getSystemUsers(systemId)
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async removeUserFromSystem(systemId, userId) {
      try {
        await systemApi.removeUserFromSystem(systemId, userId)
        
        // 从用户列表中移除
        const index = this.systemUsers.findIndex(u => u.id === userId)
        if (index !== -1) {
          this.systemUsers.splice(index, 1)
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async getSystemStats(id) {
      try {
        return await systemApi.getSystemStats(id)
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
        search: '',
        enabled: null
      }
      this.pagination.page = 1
    },

    clearError() {
      this.error = null
    },

    async fetchAllSystems(enabledOnly = true) {
      this.loading = true
      this.error = null
      
      try {
        const response = await systemApi.getSystems({
          page: 1,
          page_size: 1000,
          enabled: enabledOnly
        })
        
        if (response && response.data) {
          this.systems = response.data
          return response.data
        } else if (Array.isArray(response)) {
          this.systems = response
          return response
        } else {
          console.warn('Unexpected response format:', response)
          this.systems = []
          return []
        }
      } catch (error) {
        this.error = error.message || '获取系统列表失败'
        this.systems = []
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})