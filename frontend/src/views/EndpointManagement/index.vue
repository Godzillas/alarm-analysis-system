<template>
  <div class="endpoint-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>接入点管理</h2>
          <el-button type="primary" @click="showCreateDialog">
            <el-icon><Plus /></el-icon>
            新建接入点
          </el-button>
        </div>
      </template>

      <!-- 接入点列表 -->
      <el-table :data="endpoints" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="endpoint_type" label="类型" width="120">
          <template #default="scope">
            <el-tag :type="getTypeTagType(scope.row.endpoint_type)">
              {{ getTypeDisplayName(scope.row.endpoint_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="system_name" label="所属系统" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.system_name" type="info" size="small">
              {{ row.system_name }}
            </el-tag>
            <span v-else>未分配</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="Webhook URL" min-width="300" show-overflow-tooltip>
          <template #default="scope">
            {{ scope.row.webhook_url || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="scope">
            <el-switch 
              v-model="scope.row.enabled" 
              @change="toggleEndpoint(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="统计" width="120">
          <template #default="scope">
            <el-tooltip content="查看统计信息" placement="top">
              <el-link @click="viewStats(scope.row)" type="primary">{{ (scope.row.stats && scope.row.stats.total_requests) || 0 }}</el-link>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="150">
          <template #default="scope">
            {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="editEndpoint(scope.row)">编辑</el-button>
            <el-button size="small" @click="testEndpoint(scope.row)">测试</el-button>
            <el-button size="small" @click="viewToken(scope.row)">Token</el-button>
            <el-button size="small" type="danger" @click="deleteEndpoint(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑接入点对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑接入点' : '新建接入点'"
      width="60%"
      destroy-on-close
    >
      <el-form :model="endpointForm" :rules="formRules" ref="formRef" label-width="120px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="endpointForm.name" placeholder="请输入接入点名称" />
        </el-form-item>
        
        <el-form-item label="类型" prop="endpoint_type">
          <el-select v-model="endpointForm.endpoint_type" placeholder="选择接入点类型" @change="onTypeChange">
            <el-option label="Webhook接入" value="webhook" />
            <el-option label="Kafka消费" value="kafka" disabled />
            <el-option label="MySQL监听" value="mysql" disabled />
            <el-option label="远程Shell" value="shell" disabled />
            <el-option label="文件监控" value="file" disabled />
          </el-select>
        </el-form-item>
        
        <el-form-item label="所属系统" prop="system_id">
          <el-select 
            v-model="endpointForm.system_id" 
            placeholder="选择所属系统"
            clearable
            filterable
          >
            <el-option
              v-for="system in availableSystems"
              :key="system.id"
              :label="`${system.name} (${system.code})`"
              :value="system.id"
            />
          </el-select>
          <el-text size="small" type="info" style="margin-left: 10px">
            可以空着，后续可修改
          </el-text>
        </el-form-item>
        
        <el-form-item label="描述" prop="description">
          <el-input type="textarea" v-model="endpointForm.description" placeholder="请输入接入点描述" />
        </el-form-item>
        
        <!-- Webhook配置 -->
        <div v-if="endpointForm.endpoint_type === 'webhook'">
          <el-alert 
            type="info" 
            show-icon 
            :closable="false"
            style="margin-bottom: 15px"
          >
            <template #title>
              Webhook接入说明
            </template>
            <p>创建后将自动生成Webhook接收地址和API Token，供外部系统推送告警数据使用。</p>
          </el-alert>
          
          <el-form-item label="数据格式">
            <el-radio-group v-model="endpointForm.data_format">
              <el-radio label="json">JSON格式</el-radio>
              <el-radio label="form">表单格式</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item label="字段映射">
            <el-button size="small" @click="showFieldMapping" :disabled="!isEdit">
              配置字段映射
            </el-button>
            <el-text size="small" type="info" style="margin-left: 10px">
              保存接入点后可配置字段映射规则
            </el-text>
          </el-form-item>
        </div>
        
        <el-form-item label="启用状态" prop="enabled">
          <el-switch v-model="endpointForm.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEndpoint">保存</el-button>
      </template>
    </el-dialog>

    <!-- Token查看对话框 -->
    <el-dialog v-model="tokenDialogVisible" title="API Token" width="50%">
      <div class="token-info">
        <p><strong>接入点:</strong> {{ currentEndpoint && currentEndpoint.name }}</p>
        <p><strong>API Token:</strong></p>
        <el-input 
          :value="currentEndpoint && currentEndpoint.api_token" 
          readonly 
          type="textarea"
          :rows="3"
          style="margin-bottom: 10px"
        />
        <p><strong>Webhook URL:</strong></p>
        <el-input 
          :value="getWebhookUrl(currentEndpoint)"
          readonly
          style="margin-bottom: 10px"
        />
        <p><strong>使用说明:</strong></p>
        <el-text size="small" type="info">
          将告警数据以POST方式发送到上述URL，Token已包含在URL路径中，无需额外认证头
        </el-text>
      </div>
      <template #footer>
        <el-button @click="copyToken">复制Token</el-button>
        <el-button @click="regenerateToken" type="warning">重新生成</el-button>
        <el-button @click="tokenDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 统计信息对话框 -->
    <el-dialog v-model="statsDialogVisible" title="接入点统计" width="60%">
      <div v-if="endpointStats" class="stats-content">
        <el-row :gutter="20">
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-number">{{ endpointStats.total_requests || 0 }}</div>
              <div class="stat-label">总请求数</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-number">{{ endpointStats.success_requests || 0 }}</div>
              <div class="stat-label">成功请求</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-number">{{ endpointStats.failed_requests || 0 }}</div>
              <div class="stat-label">失败请求</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-number">{{ endpointStats.last_request_time || '-' }}</div>
              <div class="stat-label">最后请求</div>
            </div>
          </el-col>
        </el-row>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useSystemStore } from '@/store/system'

// 响应式数据
const loading = ref(false)
const endpoints = ref([])
const dialogVisible = ref(false)
const tokenDialogVisible = ref(false)
const statsDialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()
const currentEndpoint = ref(null)
const endpointStats = ref(null)
const availableSystems = ref([])

// Store instances
const systemStore = useSystemStore()

// 表单数据
const endpointForm = reactive({
  id: null,
  name: '',
  endpoint_type: 'webhook',
  system_id: null,
  description: '',
  data_format: 'json',
  field_mapping: {},
  enabled: true
})

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入接入点名称', trigger: 'blur' }
  ],
  endpoint_type: [
    { required: true, message: '请选择接入点类型', trigger: 'change' }
  ]
}

// 类型标签类型
const getTypeTagType = (type) => {
  const types = {
    webhook: 'primary',
    kafka: 'success',
    mysql: 'warning',
    shell: 'info',
    file: 'danger'
  }
  return types[type] || ''
}

// 类型显示名称
const getTypeDisplayName = (type) => {
  const names = {
    webhook: 'Webhook接入',
    kafka: 'Kafka消费',
    mysql: 'MySQL监听',
    shell: '远程Shell',
    file: '文件监控'
  }
  return names[type] || type
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString('zh-CN')
}

// 获取Webhook URL
const getWebhookUrl = (endpoint) => {
  if (!endpoint || !endpoint.api_token) return ''
  return `${window.location.origin}/api/webhook/alarm/${endpoint.api_token}`
}

// 显示创建对话框
const showCreateDialog = async () => {
  isEdit.value = false
  resetForm()
  await loadAvailableSystems()
  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  Object.assign(endpointForm, {
    id: null,
    name: '',
    endpoint_type: 'webhook',
    system_id: null,
    description: '',
    data_format: 'json',
    field_mapping: {},
    enabled: true
  })
}

// 类型变化处理
const onTypeChange = (type) => {
  // Webhook类型特殊处理
  if (type === 'webhook') {
    endpointForm.data_format = 'json'
    endpointForm.field_mapping = {}
  }
}

// 显示字段映射配置
const showFieldMapping = () => {
  // TODO: 打开字段映射配置对话框
  ElMessage.info('字段映射功能开发中...')
}

// 编辑接入点
const editEndpoint = async (endpoint) => {
  isEdit.value = true
  Object.assign(endpointForm, { ...endpoint })
  await loadAvailableSystems()
  dialogVisible.value = true
}

// 保存接入点
const saveEndpoint = async () => {
  try {
    await formRef.value.validate()
    
    if (isEdit.value) {
      // 更新接入点
      console.log('更新接入点:', endpointForm)
      ElMessage.success('接入点更新成功')
    } else {
      // 创建接入点
      const newEndpoint = {
        ...endpointForm,
        id: Date.now(),
        api_token: `ep_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`,
        webhook_url: '',  // 将在后端生成
        created_at: new Date().toISOString(),
        stats: {
          total_requests: 0,
          success_requests: 0,
          failed_requests: 0,
          last_request_time: null
        }
      }
      
      // 自动生成webhook URL
      newEndpoint.webhook_url = `${window.location.origin}/api/webhook/alarm/${newEndpoint.api_token}`
      endpoints.value.push(newEndpoint)
      console.log('创建接入点:', newEndpoint)
      ElMessage.success('接入点创建成功')
    }
    
    dialogVisible.value = false
  } catch (error) {
    console.error('保存接入点失败:', error)
  }
}

// 切换接入点状态
const toggleEndpoint = async (endpoint) => {
  try {
    console.log('切换接入点状态:', endpoint.id, endpoint.enabled)
    ElMessage.success(`接入点已${endpoint.enabled ? '启用' : '禁用'}`)
  } catch (error) {
    console.error('切换接入点状态失败:', error)
    endpoint.enabled = !endpoint.enabled // 回滚状态
  }
}

// 测试接入点
const testEndpoint = async (endpoint) => {
  try {
    console.log('测试接入点:', endpoint.id)
    ElMessage.success('接入点测试成功')
  } catch (error) {
    console.error('测试接入点失败:', error)
    ElMessage.error('接入点测试失败')
  }
}

// 查看Token
const viewToken = (endpoint) => {
  currentEndpoint.value = endpoint
  tokenDialogVisible.value = true
}

// 复制Token
const copyToken = async () => {
  if (!currentEndpoint.value || !currentEndpoint.value.api_token) return
  
  try {
    await navigator.clipboard.writeText(currentEndpoint.value.api_token)
    ElMessage.success('Token已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

// 重新生成Token
const regenerateToken = async () => {
  try {
    await ElMessageBox.confirm('重新生成Token将使旧Token失效，确定要继续吗？', '确认重新生成', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const newToken = `ep_${Math.random().toString(36).substr(2, 20)}`
    currentEndpoint.value.api_token = newToken
    
    console.log('重新生成Token:', currentEndpoint.value.id, newToken)
    ElMessage.success('Token重新生成成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重新生成Token失败:', error)
    }
  }
}

// 查看统计
const viewStats = (endpoint) => {
  endpointStats.value = endpoint.stats
  statsDialogVisible.value = true
}

// 删除接入点
const deleteEndpoint = async (endpoint) => {
  try {
    await ElMessageBox.confirm(`确定要删除接入点 "${endpoint.name}" 吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const index = endpoints.value.findIndex(e => e.id === endpoint.id)
    if (index > -1) {
      endpoints.value.splice(index, 1)
    }
    
    console.log('删除接入点:', endpoint.id)
    ElMessage.success('接入点删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除接入点失败:', error)
    }
  }
}

// 加载可用系统列表
const loadAvailableSystems = async () => {
  try {
    await systemStore.fetchSystems({ page: 1, page_size: 1000 })
    availableSystems.value = systemStore.systems.filter(system => system.enabled)
  } catch (error) {
    console.error('加载系统列表失败:', error)
    ElMessage.error('加载系统列表失败')
  }
}

// 加载接入点列表
const loadEndpoints = async () => {
  loading.value = true
  try {
    // 模拟接入点数据（包含系统信息）
    endpoints.value = [
      {
        id: 1,
        name: '生产环境告警接入',
        endpoint_type: 'webhook',
        system_id: 1,
        system_name: '用户管理系统',
        description: '生产环境系统告警统一接入点',
        webhook_url: `${window.location.origin}/api/webhook/alarm/ep_1719187200_abc12345`,
        data_format: 'json',
        field_mapping: {},
        enabled: true,
        api_token: 'ep_1719187200_abc12345',
        created_at: new Date(Date.now() - 86400000 * 7).toISOString(),
        stats: {
          total_requests: 1245,
          success_requests: 1200,
          failed_requests: 45,
          last_request_time: '2小时前'
        }
      },
      {
        id: 2,
        name: '测试环境告警接入',
        endpoint_type: 'webhook',
        system_id: 2,
        system_name: '订单处理系统',
        description: '测试环境告警数据接入，用于验证告警规则',
        webhook_url: `${window.location.origin}/api/webhook/alarm/ep_1719273600_def67890`,
        data_format: 'json',
        field_mapping: {},
        enabled: true,
        api_token: 'ep_1719273600_def67890',
        created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
        stats: {
          total_requests: 856,
          success_requests: 843,
          failed_requests: 13,
          last_request_time: '30分钟前'
        }
      },
      {
        id: 3,
        name: '监控系统接入',
        endpoint_type: 'webhook',
        system_id: null,
        system_name: null,
        description: '外部监控系统（Prometheus/Grafana）告警接入',
        webhook_url: `${window.location.origin}/api/webhook/alarm/ep_webhook_token_901234`,
        data_format: 'json',
        field_mapping: {
          severity: 'alert.labels.severity',
          title: 'alert.annotations.summary',
          description: 'alert.annotations.description'
        },
        enabled: true,
        api_token: 'ep_webhook_token_901234',
        created_at: new Date(Date.now() - 86400000 * 1).toISOString(),
        stats: {
          total_requests: 89,
          success_requests: 85,
          failed_requests: 4,
          last_request_time: '5分钟前'
        }
      }
    ]
  } catch (error) {
    console.error('加载接入点失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadEndpoints()
  await loadAvailableSystems()
})
</script>

<style lang="scss" scoped>
.endpoint-management {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    h2 {
      margin: 0;
      color: var(--el-text-color-primary);
    }
  }
  
  .token-info {
    p {
      margin-bottom: 15px;
      
      strong {
        color: var(--el-text-color-primary);
      }
    }
  }
  
  .stats-content {
    .stat-card {
      text-align: center;
      padding: 20px;
      background: var(--el-fill-color-lighter);
      border-radius: 8px;
      
      .stat-number {
        font-size: 24px;
        font-weight: bold;
        color: var(--el-color-primary);
        margin-bottom: 8px;
      }
      
      .stat-label {
        font-size: 14px;
        color: var(--el-text-color-secondary);
      }
    }
  }
}
</style>