<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside 
      :width="sidebarWidth" 
      class="app-sidebar"
      :class="{ 'is-collapsed': themeStore.sidebarCollapsed }"
    >
      <Sidebar />
    </el-aside>

    <!-- 主容器 -->
    <el-container class="app-main">
      <!-- 顶部导航 -->
      <el-header class="app-header" height="60px">
        <Header />
      </el-header>

      <!-- 内容区域 -->
      <el-main class="app-content">
        <router-view v-slot="{ Component }">
          <transition name="fade-transform" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useThemeStore } from '@/store/theme'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'

const themeStore = useThemeStore()

const sidebarWidth = computed(() => {
  return themeStore.sidebarCollapsed ? '64px' : '240px'
})
</script>

<style lang="scss" scoped>
.app-container {
  height: 100vh;
}

.app-sidebar {
  background-color: var(--el-bg-color-page);
  border-right: 1px solid var(--el-border-color);
  transition: width 0.3s ease;
  overflow: hidden;

  &.is-collapsed {
    width: 64px !important;
  }
}

.app-main {
  background-color: var(--el-bg-color-page);
}

.app-header {
  background-color: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
  display: flex;
  align-items: center;
  padding: 0;
}

.app-content {
  padding: 20px;
  background-color: var(--el-bg-color-page);
  overflow-y: auto;
}

// 页面切换动画
.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: all 0.3s;
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}
</style>