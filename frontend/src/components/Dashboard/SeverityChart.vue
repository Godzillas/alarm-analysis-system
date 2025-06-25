<template>
  <div class="severity-chart">
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
import { computed } from 'vue'

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

const severityColors = {
  critical: '#F56C6C',
  high: '#E6A23C', 
  medium: '#409EFF',
  low: '#67C23A',
  info: '#909399'
}

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

  const chartData = props.data.map(item => ({
    name: item.severity || item.name,
    value: item.count || item.value,
    itemStyle: {
      color: severityColors[item.severity || item.name] || '#409EFF'
    }
  }))

  return {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      bottom: '5%',
      left: 'center'
    },
    series: [{
      name: '严重程度分布',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: false,
        position: 'center'
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 20,
          fontWeight: 'bold'
        }
      },
      labelLine: {
        show: false
      },
      data: chartData
    }]
  }
})
</script>

<style lang="scss" scoped>
.severity-chart {
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