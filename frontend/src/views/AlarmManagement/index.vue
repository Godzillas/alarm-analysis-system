<template>
  <div class="alarm-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <h3>告警管理</h3>
          <div class="header-actions">
            <el-button type="primary" @click="refreshData">刷新</el-button>
          </div>
        </div>
      </template>
      
      <!-- 筛选器 -->
      <div class="filters">
        <el-form :model="filters" inline class="filter-form">
          <el-form-item label="所属系统">
            <el-select 
              v-model="filters.system_id" 
              placeholder="全部系统" 
              clearable 
              filterable
              class="el-select--system"
              :loading="systemStore.loading"
              loading-text="加载系统列表中..."
              no-data-text="暂无可用系统"
            >
              <el-option
                v-for="system in availableSystems"
                :key="system.id"
                :label="system.name"
                :value="system.id"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="严重程度">
            <el-select 
              v-model="filters.severity" 
              placeholder="全部" 
              clearable
              class="el-select--severity"
              @change="handleSeverityChange"
            >
              <el-option label="严重" value="critical" />
              <el-option label="高" value="high" />
              <el-option label="中" value="medium" />
              <el-option label="低" value="low" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="状态">
            <el-select 
              v-model="filters.status" 
              placeholder="全部" 
              clearable
              class="el-select--status"
              @change="handleStatusChange"
            >
              <el-option label="活跃" value="active" />
              <el-option label="已确认" value="acknowledged" />
              <el-option label="已解决" value="resolved" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="搜索">
            <el-input 
              v-model="filters.search" 
              placeholder="搜索告警标题..."
              clearable
              class="el-input--search"
              @input="handleSearchInput"
            />
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="handleReset">重置</el-button>
            <el-button 
              v-if="systemStore.error" 
              type="warning" 
              @click="loadAvailableSystems"
              :loading="systemStore.loading"
              size="small"
            >
              重新加载系统
            </el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <!-- 告警表格 -->
      <el-table 
        :data="alarmStore.alarms" 
        :loading="alarmStore.loading"
        stripe
        style="width: 100%"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="severity" label="严重程度" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)">
              {{ getSeverityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="title" label="告警标题" min-width="200">
          <template #default="{ row }">
            <el-button 
              type="text" 
              @click="showAlarmDetail(row)"
              style="color: var(--el-color-primary)"
            >
              {{ row.title }}
            </el-button>
          </template>
        </el-table-column>
        
        <el-table-column prop="source" label="来源" width="120" />
        
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="host" label="主机" width="120" />
        
        <el-table-column prop="service" label="服务" width="100" />
        
        <el-table-column prop="count" label="次数" width="60" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.count > 1" type="warning" size="small">
              {{ row.count }}
            </el-tag>
            <span v-else>{{ row.count }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="created_at" label="创建时间" width="150">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="row.status === 'active'"
              type="warning" 
              size="small" 
              @click="handleAcknowledge(row)"
              :loading="row.acknowledging"
            >
              确认
            </el-button>
            
            <el-button 
              v-if="row.status !== 'resolved'"
              type="success" 
              size="small" 
              @click="handleResolve(row)"
              :loading="row.resolving"
            >
              解决
            </el-button>
            
            <el-button 
              type="primary" 
              size="small" 
              @click="showAlarmDetail(row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="alarmStore.pagination.page"
          v-model:page-size="alarmStore.pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="alarmStore.pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
    
    <!-- 告警详情弹窗 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="告警详情"
      width="80%"
      destroy-on-close
    >
      <div v-if="selectedAlarm" class="alarm-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="告警标题">
            {{ selectedAlarm.title }}
          </el-descriptions-item>
          <el-descriptions-item label="来源">
            <el-tag>{{ selectedAlarm.source }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag :type="getSeverityType(selectedAlarm.severity)">
              {{ getSeverityText(selectedAlarm.severity) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedAlarm.status)">
              {{ getStatusText(selectedAlarm.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="主机">
            {{ selectedAlarm.host || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="服务">
            {{ selectedAlarm.service || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="环境">
            {{ selectedAlarm.environment || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="触发次数">
            <el-tag v-if="selectedAlarm.count > 1" type="warning">
              {{ selectedAlarm.count }} 次
            </el-tag>
            <span v-else>{{ selectedAlarm.count }} 次</span>
          </el-descriptions-item>
          <el-descriptions-item label="首次触发">
            {{ formatTime(selectedAlarm.first_occurrence) }}
          </el-descriptions-item>
          <el-descriptions-item label="最后触发">
            {{ formatTime(selectedAlarm.last_occurrence) }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatTime(selectedAlarm.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatTime(selectedAlarm.updated_at) }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedAlarm.acknowledged_at" label="确认时间">
            {{ formatTime(selectedAlarm.acknowledged_at) }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedAlarm.resolved_at" label="解决时间">
            {{ formatTime(selectedAlarm.resolved_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            <div class="alarm-description">
              {{ selectedAlarm.description || '无描述' }}
            </div>
          </el-descriptions-item>
        </el-descriptions>
        
        <!-- 标签信息 -->
        <div v-if="selectedAlarm.tags && Object.keys(selectedAlarm.tags).length" class="alarm-tags">
          <h4>标签信息</h4>
          <el-tag 
            v-for="(value, key) in selectedAlarm.tags" 
            :key="key" 
            style="margin: 4px"
            type="info"
          >
            {{ key }}: {{ value }}
          </el-tag>
        </div>
        
        <!-- 元数据信息 -->
        <div v-if="selectedAlarm.alarm_metadata" class="alarm-metadata">
          <h4>元数据信息</h4>
          <el-scrollbar height="300px">
            <pre>{{ JSON.stringify(selectedAlarm.alarm_metadata, null, 2) }}</pre>
          </el-scrollbar>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button 
            v-if="selectedAlarm && selectedAlarm.status === 'active'"
            type="warning" 
            @click="handleAcknowledge(selectedAlarm)"
            :loading="selectedAlarm?.acknowledging"
          >
            确认告警
          </el-button>
          <el-button 
            v-if="selectedAlarm && selectedAlarm.status !== 'resolved'"
            type="success" 
            @click="handleResolve(selectedAlarm)"
            :loading="selectedAlarm?.resolving"
          >
            解决告警
          </el-button>
          <el-button @click="detailDialogVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, watch } from 'vue'
import { useAlarmStore } from '@/store/alarm'
import { useSystemStore } from '@/store/system'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const alarmStore = useAlarmStore()
const systemStore = useSystemStore()
const availableSystems = ref([])

// 告警详情弹窗
const detailDialogVisible = ref(false)
const selectedAlarm = ref(null)

const filters = reactive({
  system_id: null,
  severity: null,
  status: null,
  search: ''
})

const getSeverityType = (severity) => {
  const types = {
    critical: 'danger',
    high: 'warning', 
    medium: 'primary',
    low: 'success'
  }
  return types[severity] || 'info'
}

const getSeverityText = (severity) => {
  const texts = {
    critical: '严重',
    high: '高',
    medium: '中', 
    low: '低'
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
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const handleSearch = () => {
  alarmStore.setFilters(filters)
  alarmStore.fetchAlarms()
}

const handleReset = () => {
  Object.assign(filters, {
    system_id: null,
    severity: null,
    status: null,
    search: ''
  })
  alarmStore.clearFilters()
  alarmStore.fetchAlarms()
}

const handleStatusChange = (value) => {
  console.log('状态筛选值变化:', value)
  filters.status = value
  alarmStore.setFilters({ status: value })
  alarmStore.fetchAlarms()
}

const handleSeverityChange = (value) => {
  console.log('严重程度筛选值变化:', value)
  filters.severity = value
  alarmStore.setFilters({ severity: value })
  alarmStore.fetchAlarms()
}

const handleSearchInput = (value) => {
  // 防抖处理，避免频繁搜索
  if (filters.searchTimer) {
    clearTimeout(filters.searchTimer)
  }
  filters.searchTimer = setTimeout(() => {
    alarmStore.setFilters({ search: value })
    alarmStore.fetchAlarms()
  }, 500)
}

const refreshData = async () => {
  await Promise.all([
    alarmStore.fetchAlarms(),
    loadAvailableSystems()
  ])
}

const handleSizeChange = (val) => {
  alarmStore.setPageSize(val)
  alarmStore.fetchAlarms()
}

const handleCurrentChange = (val) => {
  alarmStore.setPage(val)
  alarmStore.fetchAlarms()
}

// 显示告警详情
const showAlarmDetail = (alarm) => {
  selectedAlarm.value = alarm
  detailDialogVisible.value = true
}

// 确认告警
const handleAcknowledge = async (alarm) => {
  try {
    alarm.acknowledging = true
    await alarmStore.acknowledgeAlarm(alarm.id)
    ElMessage.success('告警已确认')
    if (detailDialogVisible.value) {
      selectedAlarm.value.status = 'acknowledged'
      selectedAlarm.value.acknowledged_at = new Date().toISOString()
    }
  } catch (error) {
    ElMessage.error('确认告警失败: ' + error.message)
  } finally {
    alarm.acknowledging = false
  }
}

// 解决告警
const handleResolve = async (alarm) => {
  try {
    await ElMessageBox.confirm(
      '确定要解决这个告警吗？',
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    alarm.resolving = true
    await alarmStore.resolveAlarm(alarm.id)
    ElMessage.success('告警已解决')
    if (detailDialogVisible.value) {
      selectedAlarm.value.status = 'resolved'
      selectedAlarm.value.resolved_at = new Date().toISOString()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('解决告警失败: ' + error.message)
    }
  } finally {
    alarm.resolving = false
  }
}

// 加载可用系统列表
const loadAvailableSystems = async () => {
  try {
    const systems = await systemStore.fetchAllSystems(true)
    availableSystems.value = systems.filter(system => system.enabled)
    
    // 如果没有加载到系统，显示友好提示
    if (availableSystems.value.length === 0) {
      console.warn('未找到可用的系统，请先创建系统')
      ElMessage.info('未找到可用系统，请先在系统管理页面创建系统')
    } else {
      console.log(`成功加载 ${availableSystems.value.length} 个可用系统`)
    }
  } catch (error) {
    console.error('加载系统列表失败:', error)
    ElMessage.warning('加载系统列表失败，下拉选择可能无法正常工作')
    
    // 设置空数组避免组件报错
    availableSystems.value = []
  }
}

// 监听系统ID变化，实时搜索
watch(() => filters.system_id, (newVal) => {
  alarmStore.setFilters({ system_id: newVal })
  alarmStore.fetchAlarms()
})

onMounted(async () => {
  await loadAvailableSystems()
  alarmStore.fetchAlarms()
})
</script>

<style lang="scss" scoped>
.alarm-management {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    h3 {
      margin: 0;
    }
  }
  
  .filters {
    margin-bottom: 20px;
    padding: 20px;
    background-color: var(--el-bg-color-page);
    border-radius: 8px;
  }
  
  .pagination {
    margin-top: 20px;
    text-align: right;
  }
}

.alarm-detail {
  .alarm-description {
    padding: 12px;
    background-color: var(--el-bg-color-page);
    border-radius: 4px;
    font-family: monospace;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 200px;
    overflow-y: auto;
  }
  
  .alarm-tags {
    margin-top: 20px;
    
    h4 {
      margin-bottom: 12px;
      color: var(--el-text-color-primary);
    }
  }
  
  .alarm-metadata {
    margin-top: 20px;
    
    h4 {
      margin-bottom: 12px;
      color: var(--el-text-color-primary);
    }
    
    pre {
      background-color: var(--el-bg-color-page);
      padding: 12px;
      border-radius: 4px;
      font-size: 12px;
      line-height: 1.4;
      color: var(--el-text-color-regular);
      margin: 0;
    }
  }
}

.dialog-footer {
  text-align: right;
  
  .el-button {
    margin-left: 8px;
  }
}
</style>