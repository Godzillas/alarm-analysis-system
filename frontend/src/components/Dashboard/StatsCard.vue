<template>
  <el-card class="stats-card" :class="{ urgent: urgent }">
    <div class="stats-header">
      <div class="stats-info">
        <p class="stats-title">{{ title }}</p>
        <h2 class="stats-value">{{ formatValue(value) }}</h2>
      </div>
      <div class="stats-icon" :style="{ backgroundColor: color + '20', color: color }">
        <el-icon :size="24">
          <component :is="icon" />
        </el-icon>
      </div>
    </div>
    
    <div class="stats-footer" v-if="trend || description">
      <div class="trend" :class="trendClass">
        <el-icon v-if="trend" :size="14">
          <ArrowUp v-if="isPositiveTrend" />
          <ArrowDown v-else />
        </el-icon>
        <span class="trend-value">{{ trend }}</span>
      </div>
      <span class="description">{{ description }}</span>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    required: true
  },
  icon: {
    type: String,
    required: true
  },
  color: {
    type: String,
    default: '#409EFF'
  },
  trend: {
    type: String,
    default: ''
  },
  description: {
    type: String,
    default: ''
  },
  urgent: {
    type: Boolean,
    default: false
  }
})

// 格式化数值
const formatValue = (value) => {
  if (typeof value === 'number') {
    return value.toLocaleString()
  }
  return value
}

// 判断趋势是否为正
const isPositiveTrend = computed(() => {
  if (!props.trend) return false
  return props.trend.startsWith('+')
})

// 趋势样式类
const trendClass = computed(() => {
  if (!props.trend) return ''
  return isPositiveTrend.value ? 'positive' : 'negative'
})
</script>

<style lang="scss" scoped>
.stats-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  transition: all 0.3s ease;
  
  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }

  &.urgent {
    border-color: #f56c6c;
    box-shadow: 0 0 0 1px rgba(245, 108, 108, 0.2);
    
    &:hover {
      box-shadow: 0 4px 12px rgba(245, 108, 108, 0.3);
    }
  }

  :deep(.el-card__body) {
    padding: 20px;
  }
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.stats-info {
  flex: 1;

  .stats-title {
    margin: 0 0 8px 0;
    font-size: 14px;
    color: var(--el-text-color-regular);
    font-weight: 500;
  }

  .stats-value {
    margin: 0;
    font-size: 28px;
    font-weight: 700;
    color: var(--el-text-color-primary);
    line-height: 1;
  }
}

.stats-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stats-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);

  .trend {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 600;

    &.positive {
      color: #67c23a;
    }

    &.negative {
      color: #f56c6c;
    }
  }

  .description {
    font-size: 12px;
    color: var(--el-text-color-regular);
  }
}

// 响应式设计
@media (max-width: 768px) {
  .stats-info {
    .stats-value {
      font-size: 24px;
    }
  }

  .stats-icon {
    width: 40px;
    height: 40px;
  }
}
</style>