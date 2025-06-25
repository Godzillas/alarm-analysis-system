<template>
  <div class="recent-alarms-list">
    <el-table 
      :data="displayData" 
      :loading="loading"
      stripe
      style="width: 100%"
      @row-click="handleRowClick"
    >
      <el-table-column prop="severity" label="严重程度" width="100">
        <template #default="{ row }">
          <el-tag 
            :type="getSeverityType(row.severity)"
            size="small"
          >
            {{ getSeverityText(row.severity) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column prop="title" label="告警标题" min-width="200" />
      
      <el-table-column prop="source" label="来源" width="120" />
      
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag 
            :type="getStatusType(row.status)"
            size="small"
          >
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column prop="created_at" label="创建时间" width="150">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button 
            v-if="row.status === 'active'"
            type="primary" 
            size="small"
            @click.stop="handleAcknowledge(row)"
          >
            确认
          </el-button>
          <el-button 
            v-if="row.status !== 'resolved'"
            type="success" 
            size="small"
            @click.stop="handleResolve(row)"
          >
            解决
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <div v-if="!loading && (!data || data.length === 0)" class="empty-state">
      <el-empty description="暂无告警数据" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAlarmStore } from '@/store/alarm'
import dayjs from 'dayjs'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  limit: {
    type: Number,
    default: 10
  }
})

const alarmStore = useAlarmStore()

const displayData = computed(() => {
  if (!props.data) return []
  return props.data.slice(0, props.limit)
})

const getSeverityType = (severity) => {
  const types = {
    critical: 'danger',
    high: 'warning',
    medium: 'primary',
    low: 'success',
    info: 'info'
  }
  return types[severity] || 'info'
}

const getSeverityText = (severity) => {
  const texts = {
    critical: '严重',
    high: '高',
    medium: '中',
    low: '低',
    info: '信息'
  }
  return texts[severity] || severity
}

const getStatusType = (status) => {
  const types = {
    active: 'danger',
    acknowledged: 'warning',
    resolved: 'success'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    active: '活跃',
    acknowledged: '已确认',
    resolved: '已解决'
  }
  return texts[status] || status
}

const formatTime = (time) => {
  return dayjs(time).format('MM-DD HH:mm')
}

const handleRowClick = (row) => {
  // 可以跳转到详情页面
  console.log('查看告警详情:', row)
}

const handleAcknowledge = async (row) => {
  try {
    await ElMessageBox.confirm('确认此告警?', '提示', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await alarmStore.acknowledgeAlarm(row.id)
    ElMessage.success('告警已确认')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('确认失败')
    }
  }
}

const handleResolve = async (row) => {
  try {
    await ElMessageBox.confirm('解决此告警?', '提示', {
      confirmButtonText: '解决',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await alarmStore.resolveAlarm(row.id)
    ElMessage.success('告警已解决')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('解决失败')
    }
  }
}
</script>

<style lang="scss" scoped>
.recent-alarms-list {
  .empty-state {
    padding: 40px 0;
  }
  
  :deep(.el-table__row) {
    cursor: pointer;
    
    &:hover {
      background-color: var(--el-table-row-hover-bg-color);
    }
  }
}
</style>