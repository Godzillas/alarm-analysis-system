<template>
  <div class="contact-point-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <h3>联络点管理</h3>
          <div class="header-actions">
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon>
              新建联络点
            </el-button>
            <el-button @click="refreshData">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选器 -->
      <div class="filters">
        <el-form :model="filters" inline class="filter-form">
          <el-form-item label="所属系统">
            <el-select v-model="filters.system_id" placeholder="全部系统" clearable filterable class="el-select--system">
              <el-option
                v-for="system in availableSystems"
                :key="system.id"
                :label="system.name"
                :value="system.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="联络点类型">
            <el-select v-model="filters.contact_type" placeholder="全部类型" clearable class="el-select--type">
              <el-option
                v-for="type in contactPointStore.contactPointTypes"
                :key="type.value"
                :label="type.label"
                :value="type.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="状态">
            <el-select v-model="filters.enabled" placeholder="全部状态" clearable class="el-select--status">
              <el-option label="启用" :value="true" />
              <el-option label="禁用" :value="false" />
            </el-select>
          </el-form-item>

          <el-form-item label="搜索">
            <el-input 
              v-model="filters.search" 
              placeholder="搜索联络点名称..."
              clearable
              class="el-input--search"
              @keyup.enter="handleSearch"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 联络点表格 -->
      <el-table 
        :data="contactPointStore.contactPoints" 
        :loading="contactPointStore.loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="name" label="名称" min-width="150" />
        
        <el-table-column prop="contact_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.contact_type)">
              {{ contactPointStore.getTypeLabel(row.contact_type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="system_id" label="所属系统" width="120">
          <template #default="{ row }">
            <span v-if="row.system_id">
              {{ getSystemName(row.system_id) }}
            </span>
            <span v-else class="text-gray-400">全局</span>
          </template>
        </el-table-column>

        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'danger'">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="统计信息" width="200">
          <template #default="{ row }">
            <div class="stats-info">
              <div>总发送: {{ row.total_sent }}</div>
              <div>
                成功率: 
                <span :class="getSuccessRateClass(row)">
                  {{ getSuccessRate(row) }}%
                </span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="last_used" label="最近使用" width="150">
          <template #default="{ row }">
            <span v-if="row.last_used">
              {{ formatTime(row.last_used) }}
            </span>
            <span v-else class="text-gray-400">未使用</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="testContactPoint(row)">
              <el-icon><Operation /></el-icon>
              测试
            </el-button>
            <el-button size="small" @click="showEditDialog(row)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button size="small" @click="viewStats(row)">
              <el-icon><DataAnalysis /></el-icon>
              统计
            </el-button>
            <el-button size="small" type="danger" @click="deleteContactPoint(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="contactPointStore.pagination.page"
          v-model:page-size="contactPointStore.pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="contactPointStore.pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <ContactPointDialog
      v-model="dialogVisible"
      :contact-point="currentContactPoint"
      :is-edit="isEdit"
      @success="handleDialogSuccess"
    />

    <!-- 统计对话框 -->
    <ContactPointStatsDialog
      v-model="statsDialogVisible"
      :contact-point="currentContactPoint"
    />
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Edit, Delete, Operation, DataAnalysis } from '@element-plus/icons-vue'
import { useContactPointStore } from '@/store/contactPoint'
import { useSystemStore } from '@/store/system'
import ContactPointDialog from './components/ContactPointDialog.vue'
import ContactPointStatsDialog from './components/ContactPointStatsDialog.vue'
import dayjs from 'dayjs'

const contactPointStore = useContactPointStore()
const systemStore = useSystemStore()

const availableSystems = ref([])
const dialogVisible = ref(false)
const statsDialogVisible = ref(false)
const currentContactPoint = ref(null)
const isEdit = ref(false)

const filters = reactive({
  system_id: null,
  contact_type: '',
  enabled: null,
  search: ''
})

const getTypeTagType = (type) => {
  const typeMap = {
    email: 'primary',
    webhook: 'success',
    feishu: 'warning',
    slack: 'info',
    teams: 'primary',
    dingtalk: 'warning',
    sms: 'danger',
    wechat: 'success'
  }
  return typeMap[type] || 'info'
}

const getSystemName = (systemId) => {
  const system = availableSystems.value.find(s => s.id === systemId)
  return system ? system.name : `系统${systemId}`
}

const getSuccessRate = (row) => {
  if (row.total_sent === 0) return 0
  return Math.round((row.success_count / row.total_sent) * 100)
}

const getSuccessRateClass = (row) => {
  const rate = getSuccessRate(row)
  if (rate >= 95) return 'text-green-600'
  if (rate >= 80) return 'text-yellow-600'
  return 'text-red-600'
}

const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const showCreateDialog = () => {
  currentContactPoint.value = null
  isEdit.value = false
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  currentContactPoint.value = { ...row }
  isEdit.value = true
  dialogVisible.value = true
}

const viewStats = (row) => {
  currentContactPoint.value = row
  statsDialogVisible.value = true
}

const testContactPoint = async (row) => {
  try {
    ElMessage.info('正在测试联络点...')
    const result = await contactPointStore.testContactPoint(row.id)
    
    if (result.success) {
      ElMessage.success('联络点测试成功')
    } else {
      ElMessage.error(`联络点测试失败: ${result.error}`)
    }
  } catch (error) {
    ElMessage.error('测试联络点失败')
  }
}

const deleteContactPoint = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除联络点 "${row.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await contactPointStore.deleteContactPoint(row.id)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleSearch = () => {
  contactPointStore.setFilters(filters)
  contactPointStore.fetchContactPoints()
}

const handleReset = () => {
  Object.assign(filters, {
    system_id: null,
    contact_type: '',
    enabled: null,
    search: ''
  })
  contactPointStore.clearFilters()
  contactPointStore.fetchContactPoints()
}

const refreshData = () => {
  contactPointStore.fetchContactPoints()
}

const handleSizeChange = (val) => {
  contactPointStore.setPageSize(val)
  contactPointStore.fetchContactPoints()
}

const handleCurrentChange = (val) => {
  contactPointStore.setPage(val)
  contactPointStore.fetchContactPoints()
}

const handleDialogSuccess = () => {
  dialogVisible.value = false
  refreshData()
}

// 加载可用系统列表
const loadAvailableSystems = async () => {
  try {
    const systems = await systemStore.fetchAllSystems(true)
    availableSystems.value = systems.filter(system => system.enabled)
  } catch (error) {
    console.error('加载系统列表失败:', error)
    ElMessage.warning('加载系统列表失败')
    availableSystems.value = []
  }
}

// 监听筛选器变化
watch(() => filters.contact_type, () => {
  handleSearch()
})

watch(() => filters.enabled, () => {
  handleSearch()
})

watch(() => filters.system_id, () => {
  handleSearch()
})

onMounted(async () => {
  await Promise.all([
    loadAvailableSystems(),
    contactPointStore.fetchContactPointTypes(),
    contactPointStore.fetchContactPoints()
  ])
})
</script>

<style lang="scss" scoped>
.contact-point-management {
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
  
  .stats-info {
    font-size: 12px;
    line-height: 1.4;
  }
  
  .pagination {
    margin-top: 20px;
    text-align: right;
  }
  
  .text-gray-400 {
    color: #9ca3af;
  }
  
  .text-green-600 {
    color: #059669;
    font-weight: 600;
  }
  
  .text-yellow-600 {
    color: #d97706;
    font-weight: 600;
  }
  
  .text-red-600 {
    color: #dc2626;
    font-weight: 600;
  }
}
</style>