import { defineStore } from 'pinia'
import contactPointApi from '@/api/contactPoint'

export const useContactPointStore = defineStore('contactPoint', {
  state: () => ({
    contactPoints: [],
    contactPointTypes: [],
    pagination: {
      page: 1,
      pageSize: 20,
      total: 0,
      pages: 0
    },
    filters: {
      system_id: null,
      contact_type: '',
      enabled: null,
      search: ''
    },
    loading: false,
    currentContactPoint: null
  }),

  getters: {
    enabledContactPoints: (state) => {
      return state.contactPoints.filter(cp => cp.enabled)
    },

    contactPointsByType: (state) => {
      const grouped = {}
      state.contactPoints.forEach(cp => {
        if (!grouped[cp.contact_type]) {
          grouped[cp.contact_type] = []
        }
        grouped[cp.contact_type].push(cp)
      })
      return grouped
    },

    getTypeLabel: (state) => (type) => {
      const typeInfo = state.contactPointTypes.find(t => t.value === type)
      return typeInfo ? typeInfo.label : type
    }
  },

  actions: {
    async fetchContactPoints(params = {}) {
      this.loading = true
      try {
        const requestParams = {
          page: this.pagination.page,
          page_size: this.pagination.pageSize,
          ...this.filters,
          ...params
        }

        // 清理空值
        Object.keys(requestParams).forEach(key => {
          if (requestParams[key] === '' || requestParams[key] === null) {
            delete requestParams[key]
          }
        })

        const response = await contactPointApi.getContactPoints(requestParams)
        
        this.contactPoints = response.data.data || []
        this.pagination = {
          page: response.data.page,
          pageSize: response.data.page_size,
          total: response.data.total,
          pages: response.data.pages
        }
      } catch (error) {
        console.error('获取联络点列表失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchContactPointTypes() {
      try {
        const response = await contactPointApi.getContactPointTypes()
        this.contactPointTypes = response.data || []
      } catch (error) {
        console.error('获取联络点类型失败:', error)
        throw error
      }
    },

    async createContactPoint(data) {
      try {
        const response = await contactPointApi.createContactPoint(data)
        await this.fetchContactPoints()
        return response.data
      } catch (error) {
        console.error('创建联络点失败:', error)
        throw error
      }
    },

    async updateContactPoint(id, data) {
      try {
        const response = await contactPointApi.updateContactPoint(id, data)
        await this.fetchContactPoints()
        return response.data
      } catch (error) {
        console.error('更新联络点失败:', error)
        throw error
      }
    },

    async deleteContactPoint(id) {
      try {
        await contactPointApi.deleteContactPoint(id)
        await this.fetchContactPoints()
      } catch (error) {
        console.error('删除联络点失败:', error)
        throw error
      }
    },

    async testContactPoint(id) {
      try {
        const response = await contactPointApi.testContactPoint(id)
        return response.data
      } catch (error) {
        console.error('测试联络点失败:', error)
        throw error
      }
    },

    async getContactPointStats(id) {
      try {
        const response = await contactPointApi.getContactPointStats(id)
        return response.data
      } catch (error) {
        console.error('获取联络点统计失败:', error)
        throw error
      }
    },

    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
    },

    clearFilters() {
      this.filters = {
        system_id: null,
        contact_type: '',
        enabled: null,
        search: ''
      }
    },

    setPage(page) {
      this.pagination.page = page
    },

    setPageSize(pageSize) {
      this.pagination.pageSize = pageSize
      this.pagination.page = 1
    },

    setCurrentContactPoint(contactPoint) {
      this.currentContactPoint = contactPoint
    }
  }
})