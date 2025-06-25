<template>
  <el-dialog
    v-model="visible"
    title="联络点统计信息"
    width="800px"
    @opened="loadStats"
  >
    <div v-loading="loading" class="stats-content">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-number">{{ stats.total_sent || 0 }}</div>
            <div class="stat-label">总发送数</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card success">
            <div class="stat-number">{{ stats.success_count || 0 }}</div>
            <div class="stat-label">成功数</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card danger">
            <div class="stat-number">{{ stats.failure_count || 0 }}</div>
            <div class="stat-label">失败数</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-number">{{ stats.success_rate || 0 }}%</div>
            <div class="stat-label">成功率</div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="12">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>基本信息</span>
              </div>
            </template>
            <div class="info-content">
              <div class="info-item">
                <span class="info-label">联络点名称:</span>
                <span class="info-value">{{ stats.name }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">联络点类型:</span>
                <span class="info-value">{{ getTypeLabel(stats.contact_type) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">启用状态:</span>
                <el-tag :type="stats.enabled ? 'success' : 'danger'">
                  {{ stats.enabled ? '启用' : '禁用' }}
                </el-tag>
              </div>
              <div class="info-item">
                <span class="info-label">最近发送:</span>
                <span class="info-value">
                  {{ stats.last_sent ? formatTime(stats.last_sent) : '从未发送' }}
                </span>
              </div>
              <div class="info-item">
                <span class="info-label">最近成功:</span>
                <span class="info-value">
                  {{ stats.last_success ? formatTime(stats.last_success) : '从未成功' }}
                </span>
              </div>
              <div class="info-item">
                <span class="info-label">最近失败:</span>
                <span class="info-value">
                  {{ stats.last_failure ? formatTime(stats.last_failure) : '从未失败' }}
                </span>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>性能分析</span>
              </div>
            </template>
            <div class="performance-content">
              <!-- 成功率环形图 -->
              <div class="success-rate-chart">
                <div class="chart-container">
                  <div class="progress-circle" :style="getProgressStyle()">
                    <div class="progress-text">
                      <div class="rate">{{ stats.success_rate || 0 }}%</div>
                      <div class="label">成功率</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 健康状态 -->
              <div class="health-status">
                <div class="health-item">
                  <span class="health-label">健康状态:</span>
                  <el-tag :type="getHealthType()">{{ getHealthText() }}</el-tag>
                </div>
                <div class="health-item">
                  <span class="health-label">可靠性:</span>
                  <div class="reliability-bar">
                    <div 
                      class="reliability-fill" 
                      :style="`width: ${stats.success_rate || 0}%`"
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 操作区域 -->
      <div class="actions" style="margin-top: 20px">
        <el-button type="primary" @click="testContactPoint">
          <el-icon><Operation /></el-icon>
          测试连接
        </el-button>
        <el-button @click="refreshStats">
          <el-icon><Refresh /></el-icon>
          刷新统计
        </el-button>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">关闭</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Operation, Refresh } from '@element-plus/icons-vue'
import { useContactPointStore } from '@/store/contactPoint'
import dayjs from 'dayjs'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  contactPoint: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const contactPointStore = useContactPointStore()

const loading = ref(false)
const stats = reactive({})

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const getTypeLabel = (type) => {
  return contactPointStore.getTypeLabel(type)
}

const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const getProgressStyle = () => {
  const rate = stats.success_rate || 0
  const color = rate >= 95 ? '#67c23a' : rate >= 80 ? '#e6a23c' : '#f56c6c'
  return {
    background: `conic-gradient(${color} ${rate * 3.6}deg, #f0f0f0 0deg)`
  }
}

const getHealthType = () => {
  const rate = stats.success_rate || 0
  if (rate >= 95) return 'success'
  if (rate >= 80) return 'warning'
  return 'danger'
}

const getHealthText = () => {
  const rate = stats.success_rate || 0
  if (rate >= 95) return '健康'
  if (rate >= 80) return '一般'
  return '异常'
}

const loadStats = async () => {
  if (!props.contactPoint) return

  loading.value = true
  try {
    const result = await contactPointStore.getContactPointStats(props.contactPoint.id)
    Object.assign(stats, result)
  } catch (error) {
    ElMessage.error('加载统计信息失败')
  } finally {
    loading.value = false
  }
}

const refreshStats = () => {
  loadStats()
}

const testContactPoint = async () => {
  if (!props.contactPoint) return

  try {
    ElMessage.info('正在测试联络点...')
    const result = await contactPointStore.testContactPoint(props.contactPoint.id)
    
    if (result.success) {
      ElMessage.success('联络点测试成功')
      // 测试成功后刷新统计
      setTimeout(() => {
        refreshStats()
      }, 1000)
    } else {
      ElMessage.error(`联络点测试失败: ${result.error}`)
    }
  } catch (error) {
    ElMessage.error('测试联络点失败')
  }
}
</script>

<style lang="scss" scoped>
.stats-content {
  min-height: 300px;

  .stat-card {
    text-align: center;
    
    .stat-number {
      font-size: 24px;
      font-weight: bold;
      color: var(--el-text-color-primary);
    }
    
    .stat-label {
      font-size: 14px;
      color: var(--el-text-color-secondary);
      margin-top: 5px;
    }

    &.success .stat-number {
      color: #67c23a;
    }

    &.danger .stat-number {
      color: #f56c6c;
    }
  }

  .info-content {
    .info-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid var(--el-border-color-lighter);

      &:last-child {
        border-bottom: none;
      }

      .info-label {
        font-weight: 500;
        color: var(--el-text-color-regular);
      }

      .info-value {
        color: var(--el-text-color-primary);
      }
    }
  }

  .performance-content {
    .success-rate-chart {
      text-align: center;
      margin-bottom: 20px;

      .chart-container {
        display: inline-block;
        position: relative;
      }

      .progress-circle {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;

        .progress-text {
          background: white;
          border-radius: 50%;
          width: 80px;
          height: 80px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;

          .rate {
            font-size: 20px;
            font-weight: bold;
            color: var(--el-text-color-primary);
          }

          .label {
            font-size: 12px;
            color: var(--el-text-color-secondary);
          }
        }
      }
    }

    .health-status {
      .health-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;

        .health-label {
          font-weight: 500;
          color: var(--el-text-color-regular);
        }

        .reliability-bar {
          width: 100px;
          height: 8px;
          background: #f0f0f0;
          border-radius: 4px;
          overflow: hidden;

          .reliability-fill {
            height: 100%;
            background: linear-gradient(90deg, #f56c6c 0%, #e6a23c 50%, #67c23a 100%);
            transition: width 0.3s ease;
          }
        }
      }
    }
  }

  .actions {
    text-align: center;
  }
}

.dialog-footer {
  text-align: right;
}
</style>