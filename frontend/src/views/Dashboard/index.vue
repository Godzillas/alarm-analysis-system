<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <StatsCard
        title="总告警数"
        :value="alarmStore.stats.total"
        icon="Warning"
        color="#409EFF"
        trend="+12%"
        description="较昨日"
      />
      <StatsCard
        title="活跃告警"
        :value="alarmStore.stats.active"
        icon="Bell"
        color="#F56C6C"
        trend="-5%"
        description="较昨日"
        urgent
      />
      <StatsCard
        title="已解决"
        :value="alarmStore.stats.resolved"
        icon="CircleCheck"
        color="#67C23A"
        trend="+8%"
        description="今日解决"
      />
      <StatsCard
        title="严重告警"
        :value="alarmStore.stats.critical"
        icon="WarnTriangleFilled"
        color="#E6A23C"
        trend="-2%"
        description="较昨日"
      />
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <!-- 趋势图 -->
      <el-card class="chart-card">
        <template #header>
          <div class="card-header">
            <h3>告警趋势</h3>
            <el-radio-group v-model="trendTimeRange" size="small">
              <el-radio-button label="1h">1小时</el-radio-button>
              <el-radio-button label="24h">24小时</el-radio-button>
              <el-radio-button label="7d">7天</el-radio-button>
            </el-radio-group>
          </div>
        </template>
        <TrendChart 
          :loading="trendsLoading"
          :data="trendsData"
          height="300px"
        />
      </el-card>

      <!-- 严重程度分布 -->
      <el-card class="chart-card">
        <template #header>
          <div class="card-header">
            <h3>严重程度分布</h3>
          </div>
        </template>
        <SeverityChart 
          :loading="distributionLoading"
          :data="severityData"
          height="300px"
        />
      </el-card>
    </div>

    <!-- 最新告警列表 -->
    <el-card class="recent-alarms">
      <template #header>
        <div class="card-header">
          <h3>最新告警</h3>
          <el-button type="primary" size="small" @click="$router.push('/alarms')">
            查看全部
          </el-button>
        </div>
      </template>
      <RecentAlarmsList 
        :loading="alarmsLoading"
        :data="recentAlarms"
        :limit="10"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAlarmStore } from '@/store/alarm'
import StatsCard from '@/components/Dashboard/StatsCard.vue'
import TrendChart from '@/components/Dashboard/TrendChart.vue'
import SeverityChart from '@/components/Dashboard/SeverityChart.vue'
import RecentAlarmsList from '@/components/Dashboard/RecentAlarmsList.vue'
import analyticsApi from '@/api/analytics'

const alarmStore = useAlarmStore()

// 响应式数据
const trendTimeRange = ref('24h')
const trendsLoading = ref(false)
const distributionLoading = ref(false)
const alarmsLoading = ref(false)

const trendsData = ref([])
const severityData = ref([])
const recentAlarms = ref([])

// 加载趋势数据
const loadTrendsData = async () => {
  trendsLoading.value = true
  try {
    const response = await analyticsApi.getTrends({
      time_range: trendTimeRange.value,
      interval: trendTimeRange.value === '1h' ? '1h' : 
                trendTimeRange.value === '24h' ? '1h' : '1d'
    })
    // 转换数据格式为图表所需格式
    if (response && response.trends) {
      trendsData.value = response.trends.map(item => ({
        time: item.time,
        value: item.count || 0
      }))
    }
  } catch (error) {
    console.error('加载趋势数据失败:', error)
    // 提供默认数据
    trendsData.value = []
  } finally {
    trendsLoading.value = false
  }
}

// 加载分布数据
const loadDistributionData = async () => {
  distributionLoading.value = true
  try {
    const response = await analyticsApi.getDistribution({
      time_range: '24h'
    })
    // 转换数据格式为图表所需格式
    if (response && response.severity_distribution) {
      severityData.value = Object.entries(response.severity_distribution).map(([name, value]) => ({
        name,
        value
      }))
    }
  } catch (error) {
    console.error('加载分布数据失败:', error)
    // 提供默认数据
    severityData.value = []
  } finally {
    distributionLoading.value = false
  }
}

// 加载最新告警
const loadRecentAlarms = async () => {
  alarmsLoading.value = true
  try {
    const response = await alarmStore.fetchAlarms({ limit: 10 })
    // 使用store中的alarms数据，它已经正确处理了分页格式
    recentAlarms.value = alarmStore.alarms.slice(0, 10)
  } catch (error) {
    console.error('加载最新告警失败:', error)
  } finally {
    alarmsLoading.value = false
  }
}

// 监听时间范围变化
watch(trendTimeRange, () => {
  loadTrendsData()
})

onMounted(() => {
  // 加载统计数据
  alarmStore.fetchStats()
  
  // 加载图表数据
  loadTrendsData()
  loadDistributionData()
  loadRecentAlarms()
})
</script>

<style lang="scss" scoped>
.dashboard {
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 20px;
    margin-bottom: 20px;
  }

  .charts-grid {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 20px;
    margin-bottom: 20px;

    @media (max-width: 1200px) {
      grid-template-columns: 1fr;
    }
  }

  .chart-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: var(--el-text-color-primary);
      }
    }
  }

  .recent-alarms {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: var(--el-text-color-primary);
      }
    }
  }
}
</style>