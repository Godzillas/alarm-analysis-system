import { defineStore } from 'pinia'
import userApi from '@/api/user'

export const useUserStore = defineStore('user', {
  state: () => ({
    users: [],
    loading: false,
    error: null,
    pagination: {
      page: 1,
      pageSize: 20,
      total: 0
    },
    filters: {
      search: '',
      is_active: null,
      is_admin: null
    },
    currentUser: null
  }),

  getters: {
    activeUsers: (state) => state.users.filter(user => user.is_active),
    adminUsers: (state) => state.users.filter(user => user.is_admin),
    userOptions: (state) => state.users.map(user => ({
      label: `${user.username} (${user.full_name || user.email})`,
      value: user.id
    }))
  },

  actions: {
    async fetchUsers(params = {}) {
      this.loading = true
      this.error = null
      
      try {
        const response = await userApi.getUsers({
          page: this.pagination.page,
          page_size: this.pagination.pageSize,
          ...this.filters,
          ...params
        })
        
        this.users = response.data
        this.pagination.total = response.total
        
        return response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async createUser(userData) {
      try {
        const response = await userApi.createUser(userData)
        
        // 确保users数组已初始化
        if (!Array.isArray(this.users)) {
          this.users = []
        }
        
        if (this.pagination.page === 1) {
          this.users.unshift(response)
        }
        
        this.pagination.total += 1
        
        return response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async updateUser(id, userData) {
      try {
        const response = await userApi.updateUser(id, userData)
        
        // 确保users数组已初始化
        if (!Array.isArray(this.users)) {
          this.users = []
        }
        
        const index = this.users.findIndex(u => u.id === id)
        if (index !== -1) {
          this.users[index] = response
        }
        
        if (this.currentUser && this.currentUser.id === id) {
          this.currentUser = response
        }
        
        return response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async deleteUser(id) {
      try {
        await userApi.deleteUser(id)
        
        // 确保users数组已初始化
        if (!Array.isArray(this.users)) {
          this.users = []
        }
        
        const index = this.users.findIndex(u => u.id === id)
        if (index !== -1) {
          this.users.splice(index, 1)
          this.pagination.total -= 1
        }
        
        if (this.currentUser && this.currentUser.id === id) {
          this.currentUser = null
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async getUserById(id) {
      try {
        const response = await userApi.getUserById(id)
        this.currentUser = response
        return response
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
        is_active: null,
        is_admin: null
      }
      this.pagination.page = 1
    },

    clearError() {
      this.error = null
    },

    async getUserSystems(userId) {
      try {
        const response = await userApi.getUserSystems(userId)
        return response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async addUserToSystem(userId, systemId) {
      try {
        const response = await userApi.addUserToSystem(userId, systemId)
        return response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async removeUserFromSystem(userId, systemId) {
      try {
        const response = await userApi.removeUserFromSystem(userId, systemId)
        return response
      } catch (error) {
        this.error = error.message
        throw error
      }
    }
  }
})