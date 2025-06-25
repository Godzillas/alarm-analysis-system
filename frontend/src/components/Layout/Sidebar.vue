<template>
  <div class="sidebar">
    <!-- Logo区域 -->
    <div class="sidebar-logo">
      <router-link to="/" class="logo-link">
        <el-icon class="logo-icon" :size="28">
          <Warning />
        </el-icon>
        <span v-show="!themeStore.sidebarCollapsed" class="logo-text">
          告警分析系统
        </span>
      </router-link>
    </div>

    <!-- 导航菜单 -->
    <el-menu
      :default-active="$route.path"
      :collapse="themeStore.sidebarCollapsed"
      :unique-opened="true"
      router
      class="sidebar-menu"
    >
      <template v-for="route in menuRoutes" :key="route.path">
        <el-menu-item 
          v-if="!route.children" 
          :index="route.path"
          class="menu-item"
        >
          <el-icon>
            <component :is="route.meta.icon" />
          </el-icon>
          <template #title>{{ route.meta.title }}</template>
        </el-menu-item>

        <el-sub-menu 
          v-else 
          :index="route.path"
          class="menu-item"
        >
          <template #title>
            <el-icon>
              <component :is="route.meta.icon" />
            </el-icon>
            <span>{{ route.meta.title }}</span>
          </template>
          <el-menu-item
            v-for="child in route.children"
            :key="child.path"
            :index="child.path"
          >
            {{ child.meta.title }}
          </el-menu-item>
        </el-sub-menu>
      </template>
    </el-menu>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeStore } from '@/store/theme'

const router = useRouter()
const themeStore = useThemeStore()

// 获取菜单路由
const menuRoutes = computed(() => {
  return router.getRoutes()
    .find(route => route.path === '/')
    ?.children?.filter(route => route.meta?.title) || []
})
</script>

<style lang="scss" scoped>
.sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--el-border-color);
  padding: 0 16px;

  .logo-link {
    display: flex;
    align-items: center;
    text-decoration: none;
    color: var(--el-text-color-primary);
    font-weight: 600;
    font-size: 18px;
  }

  .logo-icon {
    color: var(--el-color-primary);
    margin-right: 12px;
  }

  .logo-text {
    white-space: nowrap;
  }
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  
  :deep(.el-menu-item) {
    height: 48px;
    line-height: 48px;
    
    &.is-active {
      background-color: var(--el-color-primary-light-9);
      color: var(--el-color-primary);
      
      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 3px;
        background-color: var(--el-color-primary);
      }
    }
  }

  :deep(.el-sub-menu__title) {
    height: 48px;
    line-height: 48px;
  }

  &.el-menu--collapse {
    .menu-item {
      padding: 0 16px;
      text-align: center;
    }
  }
}

// 暗色主题适配
html[data-theme='dark'] {
  .sidebar-menu {
    :deep(.el-menu-item.is-active) {
      background-color: var(--el-color-primary);
      color: #fff;
    }
  }
}
</style>