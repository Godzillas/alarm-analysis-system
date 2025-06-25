<template>
  <div class="analytics">
    <!-- 时间范围选择 -->
    <el-card class="time-filter">
      <el-row :gutter="20" justify="space-between" align="middle">
        <el-col :span="12">
          <h2>分析统计</h2>
        </el-col>
        <el-col :span="12" class="text-right">
          <el-radio-group v-model="timeRange" @change="onTimeRangeChange">
            <el-radio-button label="1h">1小时</el-radio-button>
            <el-radio-button label="6h">6小时</el-radio-button>
            <el-radio-button label="24h">24小时</el-radio-button>
            <el-radio-button label="7d">7天</el-radio-button>
            <el-radio-button label="30d">30天</el-radio-button>
          </el-radio-group>
        </el-col>
      </el-row>
    </el-card>

    <!-- 总览统计 -->
    <div class="overview-stats">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon total">
                <el-icon><Warning /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ overviewStats.total || 0 }}</div>
                <div class="stat-label">总告警数</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon active">
                <el-icon><Bell /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ overviewStats.active || 0 }}</div>
                <div class="stat-label">活跃告警</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon resolved">
                <el-icon><CircleCheck /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ overviewStats.resolved || 0 }}</div>
                <div class="stat-label">已解决</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon resolution-rate">
                <el-icon><TrendCharts /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ resolutionRate }}%</div>
                <div class="stat-label">解决率</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 图表区域 -->
    <div class="charts-section">
      <el-row :gutter="20">
        <!-- 告警趋势 -->
        <el-col :span="12">
          <el-card>
            <template #header>
              <div class="card-header">
                <h3>告警趋势</h3>
                <el-select v-model="trendInterval" size="small" style="width: 80px">
                  <el-option label="1小时" value="1h" />
                  <el-option label="1天" value="1d" />
                </el-select>
              </div>
            </template>
            <div ref="trendChartRef" style="height: 350px"></div>
          </el-card>
        </el-col>

        <!-- 严重程度分布 -->
        <el-col :span="12">
          <el-card>
            <template #header>
              <h3>严重程度分布</h3>
            </template>
            <div ref="severityChartRef" style="height: 350px"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" style="margin-top: 20px">
        <!-- 告警来源统计 -->
        <el-col :span="12">
          <el-card>
            <template #header>
              <h3>告警来源分布</h3>
            </template>
            <div ref="sourceChartRef" style="height: 350px"></div>
          </el-card>
        </el-col>

        <!-- 响应时间分析 -->
        <el-col :span="12">
          <el-card>
            <template #header>
              <h3>响应时间分析</h3>
            </template>
            <div ref="responseChartRef" style="height: 350px"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- TOP统计表格 -->
    <div class="top-stats">
      <el-row :gutter="20">
        <!-- TOP告警服务 -->
        <el-col :span="8">
          <el-card>
            <template #header>
              <h3>TOP 告警服务</h3>
            </template>
            <el-table :data="topServices" style="width: 100%">
              <el-table-column prop="name" label="服务名称" />
              <el-table-column prop="count" label="告警数量" width="80" />
              <el-table-column label="占比" width="80">
                <template #default="scope">
                  {{ ((scope.row.count / overviewStats.total) * 100).toFixed(1) }}%
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>

        <!-- TOP告警主机 -->
        <el-col :span="8">
          <el-card>
            <template #header>
              <h3>TOP 告警主机</h3>
            </template>
            <el-table :data="topHosts" style="width: 100%">
              <el-table-column prop="name" label="主机名称" />
              <el-table-column prop="count" label="告警数量" width="80" />
              <el-table-column label="占比" width="80">
                <template #default="scope">
                  {{ ((scope.row.count / overviewStats.total) * 100).toFixed(1) }}%
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>

        <!-- 最近告警趋势 -->
        <el-col :span="8">
          <el-card>
            <template #header>
              <h3>最近活跃告警</h3>
            </template>
            <el-table :data="recentActiveAlarms" style="width: 100%">
              <el-table-column prop="title" label="告警标题" show-overflow-tooltip />
              <el-table-column prop="severity" label="严重程度" width="90">
                <template #default="scope">
                  <el-tag :type="getSeverityType(scope.row.severity)" size="small">
                    {{ scope.row.severity }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="时间" width="100">
                <template #default="scope">
                  {{ formatRelativeTime(scope.row.created_at) }}
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, nextTick } from 'vue'
import { Warning, Bell, CircleCheck, TrendCharts } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import analyticsApi from '@/api/analytics'
import alarmApi from '@/api/alarm'

// 响应式数据
const timeRange = ref('24h')
const trendInterval = ref('1h')
const overviewStats = reactive({
  total: 0,
  active: 0,
  resolved: 0,
  acknowledged: 0
})

const topServices = ref([])
const topHosts = ref([])
const recentActiveAlarms = ref([])

// 图表引用
const trendChartRef = ref()
const severityChartRef = ref()
const sourceChartRef = ref()
const responseChartRef = ref()

// 图表实例
let trendChart = null
let severityChart = null
let sourceChart = null
let responseChart = null

// 计算解决率
const resolutionRate = computed(() => {
  if (overviewStats.total === 0) return 0
  return ((overviewStats.resolved / overviewStats.total) * 100).toFixed(1)
})

// 严重程度类型映射
const getSeverityType = (severity) => {
  const types = {
    critical: 'danger',
    high: 'warning',
    medium: '',
    low: 'info',
    info: 'success'
  }
  return types[severity] || ''
}

// 格式化相对时间
const formatRelativeTime = (timeStr) => {
  const now = new Date()
  const time = new Date(timeStr)
  const diff = now - time
  const hours = Math.floor(diff / (1000 * 60 * 60))
  if (hours < 1) return '刚刚'
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  return `${days}天前`
}

// 初始化图表
const initCharts = async () => {
  await nextTick()

  // 趋势图
  if (trendChartRef.value) {
    trendChart = echarts.init(trendChartRef.value)
    trendChart.setOption({
      title: { text: '' },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value' },
      series: [{
        name: '告警数量',
        type: 'line',
        data: [],
        smooth: true,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.6)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
          ])
        }
      }]
    })
  }

  // 严重程度分布饼图
  if (severityChartRef.value) {
    severityChart = echarts.init(severityChartRef.value)
    severityChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { orient: 'vertical', left: 'left' },
      series: [{
        name: '严重程度',
        type: 'pie',
        radius: '50%',
        data: [],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }]
    })
  }

  // 来源分布柱状图
  if (sourceChartRef.value) {
    sourceChart = echarts.init(sourceChartRef.value)
    sourceChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value' },
      series: [{
        name: '告警数量',
        type: 'bar',
        data: []
      }]
    })
  }

  // 响应时间图
  if (responseChartRef.value) {
    responseChart = echarts.init(responseChartRef.value)
    responseChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value', name: '响应时间(分钟)' },
      series: [{
        name: '平均响应时间',
        type: 'bar',
        data: []
      }]
    })
  }
}

// 加载数据
const loadData = async () => {
  try {
    // 加载总览统计
    const stats = await alarmApi.getStats()
    Object.assign(overviewStats, stats)

    // 加载趋势数据
    const trends = await analyticsApi.getTrends({
      time_range: timeRange.value,
      interval: trendInterval.value
    })
    updateTrendChart(trends)

    // 加载分布数据
    const distribution = await analyticsApi.getDistribution({
      time_range: timeRange.value
    })
    updateDistributionCharts(distribution)

    // 加载TOP数据
    const topData = await analyticsApi.getTopData({
      time_range: timeRange.value,
      limit: 10
    })
    updateTopData(topData)

    // 加载最近活跃告警
    const recentAlarms = await alarmApi.getAlarms({
      status: 'active',
      limit: 10,
      skip: 0
    })
    recentActiveAlarms.value = recentAlarms

  } catch (error) {
    console.error('加载分析数据失败:', error)
  }
}

// 更新趋势图
const updateTrendChart = (trends) => {
  if (!trendChart || !trends || !trends.trends) return

  const times = trends.trends.map(item => {
    const date = new Date(item.time)
    return timeRange.value === '1h' || timeRange.value === '6h' 
      ? date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      : date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  })
  
  const values = trends.trends.map(item => item.count)

  trendChart.setOption({
    xAxis: { data: times },
    series: [{ data: values }]
  })
}

// 更新分布图表
const updateDistributionCharts = (distribution) => {
  if (!distribution) return

  // 更新严重程度分布
  if (severityChart && distribution.severity_distribution) {
    const severityData = Object.entries(distribution.severity_distribution).map(([name, value]) => ({
      name: name.toUpperCase(),
      value
    }))
    
    severityChart.setOption({
      series: [{ data: severityData }]
    })
  }

  // 更新来源分布
  if (sourceChart && distribution.source_distribution) {
    const sources = Object.keys(distribution.source_distribution)
    const values = Object.values(distribution.source_distribution)
    
    sourceChart.setOption({
      xAxis: { data: sources },
      series: [{ data: values }]
    })
  }
}

// 更新TOP数据
const updateTopData = (topData) => {
  if (!topData) return

  if (topData.top_services) {
    topServices.value = topData.top_services.map(item => ({
      name: item.service || '未知服务',
      count: item.count
    }))
  }

  if (topData.top_hosts) {
    topHosts.value = topData.top_hosts.map(item => ({
      name: item.host || '未知主机',
      count: item.count
    }))
  }

  // 模拟响应时间数据
  if (responseChart) {
    const responseData = [
      { name: '0-5min', value: Math.floor(Math.random() * 100) },
      { name: '5-15min', value: Math.floor(Math.random() * 80) },
      { name: '15-30min', value: Math.floor(Math.random() * 60) },
      { name: '30-60min', value: Math.floor(Math.random() * 40) },
      { name: '>1h', value: Math.floor(Math.random() * 20) }
    ]

    responseChart.setOption({
      xAxis: { data: responseData.map(item => item.name) },
      series: [{ data: responseData.map(item => item.value) }]
    })
  }
}

// 时间范围变化
const onTimeRangeChange = () => {
  loadData()
}

onMounted(async () => {
  await initCharts()
  await loadData()
})
</script>

<style lang="scss" scoped>
.analytics {
  .time-filter {
    margin-bottom: 20px;
    
    h2 {
      margin: 0;
      color: var(--el-text-color-primary);
    }
    
    .text-right {
      text-align: right;
    }
  }
  
  .overview-stats {
    margin-bottom: 20px;
    
    .stat-card {
      .stat-content {
        display: flex;
        align-items: center;
        
        .stat-icon {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-right: 15px;
          font-size: 24px;
          color: white;
          
          &.total {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          }
          
          &.active {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
          }
          
          &.resolved {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
          }
          
          &.resolution-rate {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
          }
        }
        
        .stat-info {
          flex: 1;
          
          .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: var(--el-text-color-primary);
            line-height: 1;
          }
          
          .stat-label {
            font-size: 14px;
            color: var(--el-text-color-secondary);
            margin-top: 5px;
          }
        }
      }
    }
  }
  
  .charts-section {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      h3 {
        margin: 0;
        color: var(--el-text-color-primary);
      }
    }
  }
  
  .top-stats {
    h3 {
      margin: 0;
      color: var(--el-text-color-primary);
    }
  }
}
</style>