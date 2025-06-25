<template>
  <div class="header">
    <!-- 左侧 -->
    <div class="header-left">
      <!-- 菜单折叠按钮 -->
      <el-button 
        type="text" 
        @click="themeStore.toggleSidebar()"
        class="sidebar-toggle"
      >
        <el-icon :size="20">
          <Fold v-if="!themeStore.sidebarCollapsed" />
          <Expand v-else />
        </el-icon>
      </el-button>

      <!-- 面包屑导航 -->
      <el-breadcrumb separator="/" class="breadcrumb">
        <el-breadcrumb-item>
          <router-link to="/">首页</router-link>
        </el-breadcrumb-item>
        <el-breadcrumb-item v-if="$route.meta?.title">
          {{ $route.meta.title }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 右侧 -->
    <div class="header-right">
      <!-- 全屏按钮 -->
      <el-tooltip content="全屏">
        <el-button 
          type="text" 
          @click="toggleFullscreen"
          class="header-btn"
        >
          <el-icon :size="18">
            <FullScreen />
          </el-icon>
        </el-button>
      </el-tooltip>

      <!-- 主题切换 -->
      <el-tooltip :content="themeStore.isDark ? '切换到浅色模式' : '切换到深色模式'">
        <el-button 
          type="text" 
          @click="themeStore.toggleTheme()"
          class="header-btn"
        >
          <el-icon :size="18">
            <Sunny v-if="themeStore.isDark" />
            <Moon v-else />
          </el-icon>
        </el-button>
      </el-tooltip>

      <!-- 实时状态指示器 -->
      <div class="status-indicator">
        <el-badge :value="alarmStore.stats.active" :max="99" type="danger">
          <el-icon :size="20" color="#f56c6c">
            <Bell />
          </el-icon>
        </el-badge>
      </div>

      <!-- 用户菜单 -->
      <el-dropdown trigger="click" class="user-dropdown">
        <div class="user-info">
          <el-avatar :size="32" :src="userAvatar">
            <el-icon><User /></el-icon>
          </el-avatar>
          <span class="username">管理员</span>
          <el-icon class="arrow-down" :size="12">
            <ArrowDown />
          </el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item>
              <el-icon><User /></el-icon>
              个人中心
            </el-dropdown-item>
            <el-dropdown-item>
              <el-icon><Setting /></el-icon>
              系统设置
            </el-dropdown-item>
            <el-dropdown-item divided>
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useThemeStore } from '@/store/theme'
import { useAlarmStore } from '@/store/alarm'
import { ElMessage } from 'element-plus'

const themeStore = useThemeStore()
const alarmStore = useAlarmStore()

const userAvatar = ref('')

// 全屏切换
const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {
      ElMessage.error('浏览器不支持全屏模式')
    })
  } else {
    document.exitFullscreen()
  }
}

onMounted(() => {
  // 加载告警统计
  alarmStore.fetchStats()
})
</script>

<style lang="scss" scoped>
.header {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;

  .sidebar-toggle {
    color: var(--el-text-color-regular);
    
    &:hover {
      color: var(--el-color-primary);
    }
  }

  .breadcrumb {
    :deep(.el-breadcrumb__item) {
      .el-breadcrumb__inner {
        color: var(--el-text-color-regular);
        
        &.is-link:hover {
          color: var(--el-color-primary);
        }
      }
    }
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;

  .header-btn {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    color: var(--el-text-color-regular);
    
    &:hover {
      background-color: var(--el-fill-color-light);
      color: var(--el-color-primary);
    }
  }

  .status-indicator {
    margin-right: 8px;
  }

  .user-dropdown {
    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.3s;

      &:hover {
        background-color: var(--el-fill-color-light);
      }

      .username {
        font-size: 14px;
        color: var(--el-text-color-primary);
        font-weight: 500;
      }

      .arrow-down {
        color: var(--el-text-color-regular);
        transition: transform 0.3s;
      }

      &:hover .arrow-down {
        transform: rotate(180deg);
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .header {
    padding: 0 16px;
  }

  .header-left {
    .breadcrumb {
      display: none;
    }
  }

  .header-right {
    gap: 12px;

    .user-info .username {
      display: none;
    }
  }
}
</style>