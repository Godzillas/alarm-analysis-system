<template>
  <div class="trend-chart">
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    <v-chart 
      v-else
      :option="chartOption" 
      :style="{ height: height }"
      autoresize
    />
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  height: {
    type: String,
    default: '300px'
  }
})

const chartOption = computed(() => {
  if (!props.data || props.data.length === 0) {
    return {
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'middle',
        textStyle: {
          color: '#999'
        }
      }
    }
  }

  return {
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: props.data.map(item => item.time || item.label),
      boundaryGap: false
    },
    yAxis: {
      type: 'value'
    },
    series: [{
      name: '告警数量',
      type: 'line',
      data: props.data.map(item => item.count || item.value),
      smooth: true,
      lineStyle: {
        color: '#409EFF'
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [{
            offset: 0, color: 'rgba(64, 158, 255, 0.3)'
          }, {
            offset: 1, color: 'rgba(64, 158, 255, 0.1)'
          }]
        }
      }
    }],
    tooltip: {
      trigger: 'axis'
    }
  }
})
</script>

<style lang="scss" scoped>
.trend-chart {
  width: 100%;
  
  .loading-container {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    height: 200px;
    color: var(--el-text-color-regular);
    
    .el-icon {
      font-size: 24px;
      margin-bottom: 8px;
    }
  }
}
</style>