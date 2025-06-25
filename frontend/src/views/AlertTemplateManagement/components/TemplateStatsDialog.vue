<template>
  <el-dialog
    v-model="visible"
    title="模板统计信息"
    width="800px"
    @opened="loadStats"
  >
    <div v-loading="loading" class="template-stats">
      <!-- 基本信息 -->
      <div class="basic-info">
        <el-row :gutter="20">
          <el-col :span="8">
            <div class="info-item">
              <span class="label">模板名称:</span>
              <span class="value">{{ template?.name }}</span>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="info-item">
              <span class="label">模板类型:</span>
              <el-tag :type="getTypeTagType(template?.template_type)">
                {{ getTypeLabel(template?.template_type) }}
              </el-tag>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="info-item">
              <span class="label">状态:</span>
              <el-tag :type="template?.enabled ? 'success' : 'danger'">
                {{ template?.enabled ? '启用' : '禁用' }}
              </el-tag>
            </div>
          </el-col>
        </el-row>
        <div class="info-item">
          <span class="label">创建时间:</span>
          <span class="value">{{ formatTime(template?.created_at) }}</span>
        </div>
        <div class="info-item">
          <span class="label">最近更新:</span>
          <span class="value">{{ formatTime(template?.updated_at) }}</span>
        </div>
      </div>

      <el-divider />

      <!-- 使用统计 -->
      <div class="usage-stats">
        <h4>使用统计</h4>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card class="stat-card">
              <div class="stat-number">{{ stats.total_usage || 0 }}</div>
              <div class="stat-label">总使用次数</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="stat-card success">
              <div class="stat-number">{{ stats.success_count || 0 }}</div>
              <div class="stat-label">成功次数</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="stat-card danger">
              <div class="stat-number">{{ stats.failure_count || 0 }}</div>
              <div class="stat-label">失败次数</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="stat-card">
              <div class="stat-number">{{ stats.success_rate || 0 }}%</div>
              <div class="stat-label">成功率</div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <el-divider />

      <!-- 使用趋势 -->
      <div class="usage-trend">
        <h4>最近使用记录</h4>
        <el-table
          :data="stats.recent_usage || []"
          style="width: 100%"
          empty-text="暂无使用记录"
        >
          <el-table-column prop="created_at" label="使用时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="alert_title" label="告警标题" show-overflow-tooltip />
          <el-table-column prop="contact_point_name" label="联络点" width="150" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'success' ? 'success' : 'danger'">
                {{ row.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.error_message || '-' }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <el-divider />

      <!-- 性能分析 -->
      <div class="performance-analysis">
        <h4>性能分析</h4>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card>
              <template #header>
                <div class="card-header">
                  <span>渲染性能</span>
                </div>
              </template>
              <div class="performance-metrics">
                <div class="metric-item">
                  <span class="metric-label">平均渲染时间:</span>
                  <span class="metric-value">{{ stats.avg_render_time || 0 }}ms</span>
                </div>
                <div class="metric-item">
                  <span class="metric-label">最大渲染时间:</span>
                  <span class="metric-value">{{ stats.max_render_time || 0 }}ms</span>
                </div>
                <div class="metric-item">
                  <span class="metric-label">最小渲染时间:</span>
                  <span class="metric-value">{{ stats.min_render_time || 0 }}ms</span>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card>
              <template #header>
                <div class="card-header">
                  <span>模板复杂度</span>
                </div>
              </template>
              <div class="complexity-metrics">
                <div class="metric-item">
                  <span class="metric-label">变量数量:</span>
                  <span class="metric-value">{{ stats.variable_count || 0 }}</span>
                </div>
                <div class="metric-item">
                  <span class="metric-label">条件语句:</span>
                  <span class="metric-value">{{ stats.condition_count || 0 }}</span>
                </div>
                <div class="metric-item">
                  <span class="metric-label">循环语句:</span>
                  <span class="metric-value">{{ stats.loop_count || 0 }}</span>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <el-divider />

      <!-- 关联信息 -->
      <div class="related-info">
        <h4>关联信息</h4>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card>
              <template #header>
                <div class="card-header">
                  <span>使用此模板的联络点</span>
                </div>
              </template>
              <div class="related-contact-points">
                <div
                  v-for="cp in stats.related_contact_points || []"
                  :key="cp.id"
                  class="contact-point-item"
                >
                  <el-tag :type="getContactPointTypeTag(cp.contact_type)">
                    {{ cp.name }}
                  </el-tag>
                </div>
                <div v-if="!stats.related_contact_points?.length" class="empty-text">
                  暂无关联的联络点
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card>
              <template #header>
                <div class="card-header">
                  <span>告警来源分布</span>
                </div>
              </template>
              <div class="source-distribution">
                <div
                  v-for="source in stats.source_distribution || []"
                  :key="source.name"
                  class="source-item"
                >
                  <div class="source-name">{{ source.name }}</div>
                  <div class="source-count">{{ source.count }} 次</div>
                </div>
                <div v-if="!stats.source_distribution?.length" class="empty-text">
                  暂无告警来源数据
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">关闭</el-button>
        <el-button type="primary" @click="exportStats">
          导出统计
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useAlertTemplateStore } from '@/store/alertTemplate'
import dayjs from 'dayjs'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  template: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const alertTemplateStore = useAlertTemplateStore()

const loading = ref(false)
const stats = reactive({})

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const getTypeTagType = (type) => {
  const typeMap = {
    email: 'success',
    webhook: 'warning',
    feishu: 'info'
  }
  return typeMap[type] || 'primary'
}

const getTypeLabel = (type) => {
  return alertTemplateStore.getTemplateTypeLabel(type)
}

const getContactPointTypeTag = (type) => {
  const typeMap = {
    email: 'success',
    webhook: 'warning',
    feishu: 'info'
  }
  return typeMap[type] || 'primary'
}

const loadStats = async () => {
  if (!props.template) return

  loading.value = true
  try {
    const result = await alertTemplateStore.getTemplateStats(props.template.id)
    Object.assign(stats, result)
  } catch (error) {
    ElMessage.error('加载统计信息失败')
    // 提供默认统计数据
    Object.assign(stats, {
      total_usage: 0,
      success_count: 0,
      failure_count: 0,
      success_rate: 0,
      avg_render_time: 0,
      max_render_time: 0,
      min_render_time: 0,
      variable_count: 0,
      condition_count: 0,
      loop_count: 0,
      recent_usage: [],
      related_contact_points: [],
      source_distribution: []
    })
  } finally {
    loading.value = false
  }
}

const exportStats = () => {
  const exportData = {
    template: props.template,
    stats: stats,
    exported_at: new Date().toISOString()
  }

  const dataStr = JSON.stringify(exportData, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${props.template.name}-stats.json`
  link.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('统计信息已导出')
}
</script>

<style lang="scss" scoped>
.template-stats {
  .basic-info {
    background-color: var(--el-bg-color-page);
    padding: 15px;
    border-radius: 6px;

    .info-item {
      display: flex;
      align-items: center;
      margin-bottom: 10px;

      &:last-child {
        margin-bottom: 0;
      }

      .label {
        font-weight: 500;
        color: var(--el-text-color-regular);
        margin-right: 10px;
        min-width: 80px;
      }

      .value {
        color: var(--el-text-color-primary);
      }
    }
  }

  h4 {
    margin: 0 0 15px 0;
    color: var(--el-text-color-primary);
  }

  .usage-stats {
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
  }

  .performance-metrics,
  .complexity-metrics {
    .metric-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid var(--el-border-color-lighter);

      &:last-child {
        border-bottom: none;
      }

      .metric-label {
        color: var(--el-text-color-regular);
      }

      .metric-value {
        font-weight: 500;
        color: var(--el-text-color-primary);
      }
    }
  }

  .related-contact-points {
    .contact-point-item {
      margin-bottom: 8px;

      &:last-child {
        margin-bottom: 0;
      }
    }
  }

  .source-distribution {
    .source-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid var(--el-border-color-lighter);

      &:last-child {
        border-bottom: none;
      }

      .source-name {
        color: var(--el-text-color-regular);
      }

      .source-count {
        font-weight: 500;
        color: var(--el-text-color-primary);
      }
    }
  }

  .empty-text {
    color: var(--el-text-color-secondary);
    text-align: center;
    padding: 20px;
    font-style: italic;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>