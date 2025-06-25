import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', {
  state: () => ({
    isDark: false,
    sidebarCollapsed: false
  }),

  getters: {
    theme: (state) => (state.isDark ? 'dark' : 'light')
  },

  actions: {
    initTheme() {
      const savedTheme = localStorage.getItem('theme')
      if (savedTheme) {
        this.isDark = savedTheme === 'dark'
      } else {
        // 检测系统主题偏好
        this.isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      }
      this.applyTheme()
    },

    toggleTheme() {
      this.isDark = !this.isDark
      this.applyTheme()
      localStorage.setItem('theme', this.theme)
    },

    setTheme(theme) {
      this.isDark = theme === 'dark'
      this.applyTheme()
      localStorage.setItem('theme', theme)
    },

    applyTheme() {
      document.documentElement.setAttribute('data-theme', this.theme)
      document.documentElement.classList.toggle('dark', this.isDark)
    },

    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },

    setSidebarCollapsed(collapsed) {
      this.sidebarCollapsed = collapsed
    }
  }
})