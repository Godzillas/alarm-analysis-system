<template>
  <div class="endpoint-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1>告警接入点管理</h1>
        <p class="header-desc">配置外部系统的告警接入，支持Webhook、Grafana、Prometheus等多种方式</p>
      </div>
      <el-button type="primary" @click="showCreateDialog" size="large">
        <el-icon><Plus /></el-icon>
        创建接入点
      </el-button>
    </div>

    <!-- 接入点列表 -->
    <div class="endpoints-grid">
      <div 
        v-for="endpoint in endpoints" 
        :key="endpoint.id"
        class="endpoint-card"
        :class="{ 'disabled': !endpoint.enabled }"
      >
        <!-- 卡片头部 -->
        <div class="card-header">
          <div class="endpoint-info">
            <h3>{{ endpoint.name }}</h3>
            <el-tag :type="getTypeTagType(endpoint.endpoint_type)" size="small">
              {{ getTypeDisplayName(endpoint.endpoint_type) }}
            </el-tag>
          </div>
          <div class="card-actions">
            <el-switch 
              v-model="endpoint.enabled" 
              @change="toggleEndpoint(endpoint)"
              size="small"
            />
            <el-dropdown @command="handleCardAction">
              <el-button link size="small">
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :command="{action: 'edit', endpoint}">编辑</el-dropdown-item>
                  <el-dropdown-item :command="{action: 'copy', endpoint}">复制地址</el-dropdown-item>
                  <el-dropdown-item :command="{action: 'stats', endpoint}">查看统计</el-dropdown-item>
                  <el-dropdown-item :command="{action: 'delete', endpoint}" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <!-- 卡片内容 -->
        <div class="card-content">
          <div class="endpoint-url">
            <label>接入地址:</label>
            <div class="url-display">
              <code>{{ getWebhookUrl(endpoint) }}</code>
              <el-button 
                link 
                size="small" 
                @click="copyWebhookUrl(endpoint)"
                title="复制地址"
              >
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </div>
          </div>
          
          <div class="endpoint-meta">
            <div class="meta-item" v-if="endpoint.system_name">
              <span class="label">所属系统:</span>
              <el-tag size="small" type="info">{{ endpoint.system_name }}</el-tag>
            </div>
            <div class="meta-item">
              <span class="label">创建时间:</span>
              <span>{{ formatTime(endpoint.created_at) }}</span>
            </div>
            <div class="meta-item" v-if="endpoint.total_requests !== undefined">
              <span class="label">请求统计:</span>
              <span class="stats-text">
                总计 {{ endpoint.total_requests || 0 }}
                <span v-if="endpoint.last_used">，最后使用 {{ formatRelativeTime(endpoint.last_used) }}</span>
              </span>
            </div>
          </div>

          <div class="endpoint-desc" v-if="endpoint.description">
            {{ endpoint.description }}
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!endpoints.length && !loading" class="empty-state">
        <el-empty description="暂无接入点">
          <el-button type="primary" @click="showCreateDialog">创建第一个接入点</el-button>
        </el-empty>
      </div>
    </div>

    <!-- 创建/编辑接入点对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑接入点' : '创建接入点'"
      width="800px"
      destroy-on-close
      class="endpoint-dialog"
    >
      <!-- 步骤指示器 -->
      <el-steps :active="currentStep" align-center class="setup-steps">
        <el-step title="基本信息" description="设置接入点名称和类型" />
        <el-step title="配置参数" description="配置接入点具体参数" />
        <el-step title="测试验证" description="测试接入点是否正常工作" />
      </el-steps>

      <!-- 步骤内容 -->
      <div class="step-content">
        <!-- 步骤1: 基本信息 -->
        <div v-show="currentStep === 0" class="step-panel">
          <el-form :model="endpointForm" :rules="basicRules" ref="basicFormRef" label-width="100px">
            <el-form-item label="接入点名称" prop="name">
              <el-input 
                v-model="endpointForm.name" 
                placeholder="请输入接入点名称，如：生产环境告警接入"
                maxlength="50"
                show-word-limit
              />
            </el-form-item>
            
            <el-form-item label="接入点类型" prop="endpoint_type">
              <el-radio-group v-model="endpointForm.endpoint_type" @change="onTypeChange" class="type-radio-group">
                <el-radio label="grafana" class="type-radio">
                  <div class="radio-content">
                    <strong>Grafana告警</strong>
                    <span>支持Grafana 8+统一告警和传统告警</span>
                  </div>
                </el-radio>
                <el-radio label="prometheus" class="type-radio">
                  <div class="radio-content">
                    <strong>Prometheus告警</strong>
                    <span>接收Prometheus AlertManager标准格式</span>
                  </div>
                </el-radio>
                <el-radio label="webhook" class="type-radio">
                  <div class="radio-content">
                    <strong>通用Webhook</strong>
                    <span>接收任意JSON/表单格式的告警数据</span>
                  </div>
                </el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="所属系统">
              <el-select 
                v-model="endpointForm.system_id" 
                placeholder="选择所属系统（可选）"
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
            </el-form-item>
            
            <el-form-item label="描述">
              <el-input 
                type="textarea" 
                v-model="endpointForm.description" 
                placeholder="请简要描述这个接入点的用途"
                :rows="3"
                maxlength="200"
                show-word-limit
              />
            </el-form-item>
          </el-form>
        </div>

        <!-- 步骤2: 配置参数 -->
        <div v-show="currentStep === 1" class="step-panel">
          <!-- Grafana配置 -->
          <div v-if="endpointForm.endpoint_type === 'grafana'">
            <div class="config-section">
              <h4>Grafana告警配置</h4>
              <el-alert type="info" :closable="false" class="section-alert">
                <template #title>配置指南</template>
                <ol>
                  <li>在Grafana中打开告警规则设置</li>
                  <li>添加Webhook通知渠道</li>
                  <li>将下方生成的地址填入Webhook URL</li>
                  <li>设置HTTP方法为POST</li>
                </ol>
              </el-alert>

              <el-form :model="endpointForm" label-width="120px">
                <el-form-item label="Grafana版本">
                  <el-radio-group v-model="endpointForm.grafana_version">
                    <el-radio label="auto">自动检测</el-radio>
                    <el-radio label="unified">Grafana 8+ 统一告警</el-radio>
                    <el-radio label="legacy">Grafana 7- 传统告警</el-radio>
                  </el-radio-group>
                </el-form-item>

                <el-form-item label="接入地址" v-if="previewUrl">
                  <div class="url-preview">
                    <el-input :value="previewUrl" readonly>
                      <template #append>
                        <el-button @click="copyPreviewUrl">复制</el-button>
                      </template>
                    </el-input>
                    <el-text size="small" type="info">
                      创建后此地址将可用于接收Grafana告警
                    </el-text>
                  </div>
                </el-form-item>
              </el-form>
            </div>
          </div>

          <!-- Prometheus配置 -->
          <div v-if="endpointForm.endpoint_type === 'prometheus'">
            <div class="config-section">
              <h4>Prometheus告警配置</h4>
              <el-alert type="warning" :closable="false" class="section-alert">
                <template #title>配置指南</template>
                <ol>
                  <li>在AlertManager配置文件中添加webhook receiver</li>
                  <li>设置url为下方生成的地址</li>
                  <li>重新加载AlertManager配置</li>
                  <li>测试告警规则触发</li>
                </ol>
              </el-alert>

              <el-form :model="endpointForm" label-width="120px">
                <el-form-item label="AlertManager版本">
                  <el-radio-group v-model="endpointForm.alertmanager_version">
                    <el-radio label="v0.25+">v0.25+</el-radio>
                    <el-radio label="v0.20+">v0.20+</el-radio>
                    <el-radio label="legacy">旧版本</el-radio>
                  </el-radio-group>
                </el-form-item>

                <el-form-item label="接入地址" v-if="previewUrl">
                  <div class="url-preview">
                    <el-input :value="previewUrl" readonly>
                      <template #append>
                        <el-button @click="copyPreviewUrl">复制</el-button>
                      </template>
                    </el-input>
                  </div>
                </el-form-item>
              </el-form>
            </div>
          </div>

          <!-- Webhook配置 -->
          <div v-if="endpointForm.endpoint_type === 'webhook'">
            <div class="config-section">
              <h4>Webhook接入配置</h4>
              <el-alert type="success" :closable="false" class="section-alert">
                <template #title>配置指南</template>
                <ol>
                  <li>选择外部系统发送的数据格式</li>
                  <li>配置字段映射规则</li>
                  <li>获取接入地址并配置到外部系统</li>
                  <li>发送测试数据验证接入</li>
                </ol>
              </el-alert>

              <el-form :model="endpointForm" label-width="120px">
                <el-form-item label="数据格式">
                  <el-radio-group v-model="endpointForm.data_format">
                    <el-radio label="json">JSON格式</el-radio>
                    <el-radio label="form">表单格式</el-radio>
                  </el-radio-group>
                </el-form-item>

                <el-form-item label="字段映射">
                  <div class="field-mapping-config">
                    <el-button @click="showFieldMappingDialog" type="primary" plain>
                      <el-icon><Setting /></el-icon>
                      配置字段映射
                    </el-button>
                    <el-tag v-if="hasFieldMapping" type="success" size="small" style="margin-left: 10px">
                      已配置 {{ Object.keys(endpointForm.field_mapping || {}).length }} 个映射
                    </el-tag>
                    <el-tag v-else type="warning" size="small" style="margin-left: 10px">
                      未配置
                    </el-tag>
                  </div>
                </el-form-item>

                <el-form-item label="接入地址" v-if="previewUrl">
                  <div class="url-preview">
                    <el-input :value="previewUrl" readonly>
                      <template #append>
                        <el-button @click="copyPreviewUrl">复制</el-button>
                      </template>
                    </el-input>
                  </div>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </div>

        <!-- 步骤3: 测试验证 -->
        <div v-show="currentStep === 2" class="step-panel">
          <div class="test-section">
            <h4>接入点测试</h4>
            
            <!-- 监听状态 -->
            <div v-if="!isEdit" class="listening-section">
              <el-alert 
                :type="listeningStatus.type" 
                :title="listeningStatus.title"
                :closable="false"
                class="listening-alert"
              >
                <div v-if="isListening">
                  <p>{{ listeningStatus.message }}</p>
                  <div class="listening-actions">
                    <el-button @click="stopListening" size="small">停止监听</el-button>
                    <el-button @click="showTestExample" type="info" size="small">查看示例</el-button>
                  </div>
                </div>
                <div v-else>
                  <p>{{ listeningStatus.message }}</p>
                  <el-button @click="startListening" type="primary" size="small">开始监听</el-button>
                </div>
              </el-alert>
            </div>

            <!-- 接收到的数据 -->
            <div v-if="receivedTestData.length > 0" class="received-data-section">
              <h5>接收到的测试数据</h5>
              <div class="data-list">
                <div 
                  v-for="(data, index) in receivedTestData" 
                  :key="index"
                  class="data-item"
                  :class="{ 'success': data.status === 'success', 'error': data.status === 'error' }"
                >
                  <div class="data-header">
                    <span class="data-time">{{ formatTime(data.timestamp) }}</span>
                    <el-tag :type="data.status === 'success' ? 'success' : 'danger'" size="small">
                      {{ data.status === 'success' ? '成功' : '失败' }}
                    </el-tag>
                  </div>
                  <div class="data-preview">{{ data.preview }}</div>
                  <div class="data-actions">
                    <el-button size="small" @click="viewTestData(data)">查看详情</el-button>
                    <el-button 
                      v-if="data.status === 'success' && endpointForm.endpoint_type === 'webhook'" 
                      size="small" 
                      type="primary"
                      @click="useForFieldMapping(data)"
                    >
                      用于字段映射
                    </el-button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 测试指导 -->
            <div class="test-guidance">
              <h5>测试步骤</h5>
              <el-steps direction="vertical" :active="testStepActive">
                <el-step 
                  v-for="(step, index) in getTestSteps()" 
                  :key="index"
                  :title="step.title" 
                  :description="step.description" 
                />
              </el-steps>
            </div>
          </div>
        </div>
      </div>

      <!-- 对话框底部 -->
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button v-if="currentStep > 0" @click="prevStep">上一步</el-button>
          <el-button v-if="currentStep < 2" type="primary" @click="nextStep">下一步</el-button>
          <el-button v-if="currentStep === 2" type="primary" @click="saveEndpoint">
            {{ isEdit ? '保存' : '创建接入点' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 字段映射配置对话框 -->
    <el-dialog v-model="fieldMappingDialogVisible" title="字段映射配置" width="60%">
      <div class="field-mapping-content">
        <el-alert type="info" :closable="false" style="margin-bottom: 20px">
          <template #title>字段映射说明</template>
          <p>配置外部数据字段到系统标准字段的映射关系，支持嵌套字段路径，如: labels.severity</p>
        </el-alert>

        <el-table :data="fieldMappings" style="width: 100%">
          <el-table-column prop="system_field" label="系统字段" width="150">
            <template #default="{ row }">
              <el-tag size="small">{{ row.system_field }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="external_field" label="外部字段路径" min-width="200">
            <template #default="{ row, $index }">
              <el-input 
                v-model="row.external_field" 
                placeholder="如: title 或 labels.severity"
                size="small"
              />
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="150" />
          <el-table-column label="操作" width="100">
            <template #default="{ $index }">
              <el-button 
                size="small" 
                type="danger" 
                link
                @click="removeFieldMapping($index)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div style="margin-top: 15px;">
          <el-button @click="addFieldMapping" type="primary" plain size="small">
            <el-icon><Plus /></el-icon>
            添加映射
          </el-button>
        </div>
      </div>

      <template #footer>
        <el-button @click="fieldMappingDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveFieldMapping">保存映射</el-button>
      </template>
    </el-dialog>

    <!-- 统计信息对话框 -->
    <el-dialog v-model="statsDialogVisible" title="接入点统计" width="60%">
      <div v-if="currentEndpoint" class="stats-content">
        <div class="stats-header">
          <h3>{{ currentEndpoint.name }}</h3>
          <el-tag :type="getTypeTagType(currentEndpoint.endpoint_type)">
            {{ getTypeDisplayName(currentEndpoint.endpoint_type) }}
          </el-tag>
        </div>
        
        <el-row :gutter="20" style="margin-top: 20px;">
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-number">{{ currentEndpoint.total_requests || 0 }}</div>
              <div class="stat-label">总请求数</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-number">{{ currentEndpoint.enabled ? '启用' : '禁用' }}</div>
              <div class="stat-label">状态</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-number">{{ formatRelativeTime(currentEndpoint.last_used) }}</div>
              <div class="stat-label">最后使用</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-number">{{ formatRelativeTime(currentEndpoint.created_at) }}</div>
              <div class="stat-label">创建时间</div>
            </div>
          </el-col>
        </el-row>
        
        <div class="stats-details" style="margin-top: 30px;">
          <h4>接入配置</h4>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="接入地址">
              <code style="font-size: 12px;">{{ getWebhookUrl(currentEndpoint) }}</code>
            </el-descriptions-item>
            <el-descriptions-item label="系统归属">
              {{ currentEndpoint.system_name || '未分配' }}
            </el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">
              {{ currentEndpoint.description || '无' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, CopyDocument, Setting, MoreFilled } from '@element-plus/icons-vue'
import { useSystemStore } from '@/store/system'
import * as endpointApi from '@/api/endpoint'

// 响应式数据
const loading = ref(false)
const endpoints = ref([])
const dialogVisible = ref(false)
const statsDialogVisible = ref(false)
const fieldMappingDialogVisible = ref(false)
const isEdit = ref(false)
const basicFormRef = ref()
const currentEndpoint = ref(null)
const endpointStats = ref(null)
const availableSystems = ref([])

// 新增的步骤相关状态
const currentStep = ref(0)
const isListening = ref(false)
const receivedTestData = ref([])
const testStepActive = ref(0)

// Store instances
const systemStore = useSystemStore()

// 表单数据
const endpointForm = reactive({
  id: null,
  name: '',
  endpoint_type: 'grafana',
  system_id: null,
  description: '',
  data_format: 'json',
  field_mapping: {},
  grafana_version: 'auto',
  alertmanager_version: 'v0.25+',
  enabled: true
})

// 字段映射配置
const fieldMappings = ref([
  { system_field: 'title', external_field: '', description: '告警标题' },
  { system_field: 'description', external_field: '', description: '告警描述' },
  { system_field: 'severity', external_field: '', description: '严重程度' },
  { system_field: 'source', external_field: '', description: '告警来源' },
  { system_field: 'host', external_field: '', description: '主机名' }
])

// 表单验证规则
const basicRules = {
  name: [
    { required: true, message: '请输入接入点名称', trigger: 'blur' }
  ],
  endpoint_type: [
    { required: true, message: '请选择接入点类型', trigger: 'change' }
  ]
}

// 计算属性
const previewUrl = computed(() => {
  if (!endpointForm.endpoint_type) return ''
  
  // 在开发模式下使用后端API地址，生产模式下使用当前域名
  const isDev = process.env.NODE_ENV === 'development'
  const baseUrl = isDev ? 'http://localhost:8000' : window.location.origin
  const token = 'YOUR_TOKEN_HERE'
  
  switch (endpointForm.endpoint_type) {
    case 'grafana':
      return `${baseUrl}/api/grafana/webhook/${token}`
    case 'prometheus':
      return `${baseUrl}/api/prometheus/webhook/${token}`
    case 'webhook':
    default:
      return `${baseUrl}/api/webhook/alarm/${token}`
  }
})

const hasFieldMapping = computed(() => {
  return fieldMappings.value.some(mapping => mapping.external_field)
})

const listeningStatus = computed(() => {
  if (isListening.value) {
    return {
      type: 'success',
      title: '正在监听测试数据',
      message: '请从外部系统发送测试数据到上述地址，系统将自动捕获并显示接收结果。'
    }
  } else {
    return {
      type: 'info',
      title: '准备开始测试',
      message: '点击"开始监听"按钮，然后从外部系统发送测试数据来验证接入点配置。'
    }
  }
})

// 监听endpoint_type变化，重置字段映射
watch(() => endpointForm.endpoint_type, (newType) => {
  if (newType === 'webhook') {
    // Webhook类型需要字段映射
    resetFieldMappings()
  } else {
    // Grafana和Prometheus使用固定格式，不需要字段映射
    endpointForm.field_mapping = {}
  }
})

// 方法定义
const getTypeTagType = (type) => {
  const types = {
    webhook: 'primary',
    grafana: 'success',
    prometheus: 'warning'
  }
  return types[type] || ''
}

const getTypeDisplayName = (type) => {
  const names = {
    webhook: 'Webhook接入',
    grafana: 'Grafana告警',
    prometheus: 'Prometheus告警'
  }
  return names[type] || type
}

const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString('zh-CN')
}

const formatRelativeTime = (timeStr) => {
  if (!timeStr) return '-'
  
  const now = new Date()
  const time = new Date(timeStr)
  const diffMs = now - time
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays < 30) return `${diffDays}天前`
  
  return formatTime(timeStr)
}

const getWebhookUrl = (endpoint) => {
  if (!endpoint || !endpoint.api_token) return ''
  
  const baseUrl = window.location.origin
  const token = endpoint.api_token
  
  switch (endpoint.endpoint_type) {
    case 'grafana':
      return `${baseUrl}/api/grafana/webhook/${token}`
    case 'prometheus':
      return `${baseUrl}/api/prometheus/webhook/${token}`
    case 'webhook':
    default:
      return `${baseUrl}/api/webhook/alarm/${token}`
  }
}

const getTestSteps = () => {
  const baseSteps = [
    {
      title: '配置外部系统',
      description: `将接入地址配置到${getTypeDisplayName(endpointForm.endpoint_type)}中`
    },
    {
      title: '开始监听测试',
      description: '点击"开始监听"按钮，系统将等待接收测试数据'
    },
    {
      title: '发送测试数据',
      description: '从外部系统触发一个测试告警，验证数据是否正确接收'
    }
  ]

  if (endpointForm.endpoint_type === 'webhook') {
    baseSteps.push({
      title: '配置字段映射',
      description: '根据接收到的数据格式，配置字段映射规则'
    })
  }

  return baseSteps
}

// 对话框和步骤控制
const showCreateDialog = async () => {
  isEdit.value = false
  currentStep.value = 0
  resetForm()
  await loadAvailableSystems()
  dialogVisible.value = true
}

const resetForm = () => {
  Object.assign(endpointForm, {
    id: null,
    name: '',
    endpoint_type: 'grafana',
    system_id: null,
    description: '',
    data_format: 'json',
    field_mapping: {},
    grafana_version: 'auto',
    alertmanager_version: 'v0.25+',
    enabled: true
  })
  
  isListening.value = false
  receivedTestData.value = []
  testStepActive.value = 0
  resetFieldMappings()
}

const resetFieldMappings = () => {
  fieldMappings.value = [
    { system_field: 'title', external_field: '', description: '告警标题' },
    { system_field: 'description', external_field: '', description: '告警描述' },
    { system_field: 'severity', external_field: '', description: '严重程度' },
    { system_field: 'source', external_field: '', description: '告警来源' },
    { system_field: 'host', external_field: '', description: '主机名' }
  ]
}

const nextStep = async () => {
  if (currentStep.value === 0) {
    try {
      await basicFormRef.value.validate()
      currentStep.value++
    } catch (error) {
      ElMessage.error('请完善基本信息')
    }
  } else if (currentStep.value === 1) {
    currentStep.value++
    if (!isEdit.value) {
      // 新建时自动开始监听
      startListening()
    }
  }
}

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const onTypeChange = (type) => {
  resetFieldMappings()
}

// 监听相关方法
const startListening = () => {
  isListening.value = true
  testStepActive.value = 1
  ElMessage.success('开始监听测试数据，现在发送测试告警...')
  
  // 立即发送测试数据
  sendTestAlarm()
}

const stopListening = () => {
  isListening.value = false
  ElMessage.info('已停止监听测试数据')
}

// 发送测试告警数据
const sendTestAlarm = async () => {
  try {
    // 在创建模式下使用测试端点，编辑模式下使用真实端点
    let testUrl
    if (isEdit.value && currentEndpoint.value && currentEndpoint.value.api_token) {
      // 编辑模式：使用真实的token
      testUrl = previewUrl.value.replace('YOUR_TOKEN_HERE', currentEndpoint.value.api_token)
    } else {
      // 创建模式：使用测试端点
      const isDev = process.env.NODE_ENV === 'development'
      const baseUrl = isDev ? 'http://localhost:8000' : window.location.origin
      testUrl = `${baseUrl}/api/webhook/test-endpoint`
    }
    
    let testData = {}
    
    // 根据接入点类型构造不同的测试数据
    switch (endpointForm.endpoint_type) {
      case 'grafana':
        testData = {
          receiver: 'test-receiver',
          status: 'firing',
          alerts: [{
            status: 'firing',
            labels: {
              alertname: '测试告警',
              instance: 'test-server-01',
              severity: 'warning',
              service: 'test-service'
            },
            annotations: {
              summary: 'Grafana测试告警',
              description: '这是一个来自Grafana的测试告警消息'
            },
            startsAt: new Date().toISOString(),
            endsAt: '',
            generatorURL: 'http://grafana.example.com/graph'
          }],
          groupLabels: {
            alertname: '测试告警'
          },
          commonLabels: {
            alertname: '测试告警',
            severity: 'warning'
          },
          commonAnnotations: {},
          externalURL: 'http://grafana.example.com'
        }
        break
        
      case 'prometheus':
        testData = {
          receiver: 'test-webhook',
          status: 'firing',
          alerts: [{
            status: 'firing',
            labels: {
              alertname: '测试告警',
              instance: 'test-server-01:9090',
              job: 'prometheus',
              severity: 'warning'
            },
            annotations: {
              description: '这是一个来自Prometheus的测试告警',
              summary: 'Prometheus测试告警'
            },
            startsAt: new Date().toISOString(),
            endsAt: '',
            generatorURL: 'http://prometheus.example.com/graph'
          }],
          groupLabels: {
            alertname: '测试告警'
          },
          commonLabels: {
            alertname: '测试告警'
          },
          commonAnnotations: {},
          externalURL: 'http://alertmanager.example.com'
        }
        break
        
      case 'webhook':
      default:
        testData = {
          title: '测试告警',
          description: '这是一个通用Webhook测试告警',
          severity: 'warning',
          status: 'active',
          source: 'test-system',
          host: 'test-server-01',
          timestamp: new Date().toISOString(),
          labels: {
            environment: 'test',
            service: 'test-service'
          }
        }
        break
    }
    
    // 发送测试数据到本地接入点
    const response = await fetch(testUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(testData)
    })
    
    if (response.ok) {
      const result = await response.json()
      addReceivedTestData({
        timestamp: new Date().toISOString(),
        status: 'success',
        preview: `${endpointForm.endpoint_type}测试告警数据`,
        data: testData,
        response: result
      })
      testStepActive.value = 2
      ElMessage.success('测试告警发送成功！')
    } else {
      const errorText = await response.text()
      addReceivedTestData({
        timestamp: new Date().toISOString(),
        status: 'error',
        preview: `发送失败: ${response.status}`,
        error: errorText
      })
      ElMessage.error(`测试失败: ${response.status} ${response.statusText}`)
    }
  } catch (error) {
    console.error('创建测试数据失败:', error)
    ElMessage.error('创建测试数据失败: ' + error.message)
  }
}

// 添加接收到的测试数据
const addReceivedTestData = (data) => {
  receivedTestData.value.unshift(data)
  // 限制最多显示10条
  if (receivedTestData.value.length > 10) {
    receivedTestData.value = receivedTestData.value.slice(0, 10)
  }
}


// 字段映射相关方法
const showFieldMappingDialog = () => {
  fieldMappingDialogVisible.value = true
}

const addFieldMapping = () => {
  fieldMappings.value.push({
    system_field: '',
    external_field: '',
    description: ''
  })
}

const removeFieldMapping = (index) => {
  fieldMappings.value.splice(index, 1)
}

const saveFieldMapping = () => {
  const mapping = {}
  fieldMappings.value.forEach(item => {
    if (item.system_field && item.external_field && 
        typeof item.system_field === 'string' && 
        typeof item.external_field === 'string') {
      mapping[item.system_field] = item.external_field
    }
  })
  endpointForm.field_mapping = mapping
  fieldMappingDialogVisible.value = false
  ElMessage.success('字段映射保存成功')
}

const useForFieldMapping = (data) => {
  // 根据接收到的数据自动填充字段映射
  const sampleData = data.data
  fieldMappings.value.forEach(mapping => {
    if (mapping.system_field === 'title' && sampleData.title) {
      mapping.external_field = 'title'
    } else if (mapping.system_field === 'severity' && sampleData.severity) {
      mapping.external_field = 'severity'
    } else if (mapping.system_field === 'source' && sampleData.source) {
      mapping.external_field = 'source'
    }
  })
  showFieldMappingDialog()
}

// 卡片操作处理
const handleCardAction = (command) => {
  const { action, endpoint } = command
  
  switch (action) {
    case 'edit':
      editEndpoint(endpoint)
      break
    case 'copy':
      copyWebhookUrl(endpoint)
      break
    case 'stats':
      viewStats(endpoint)
      break
    case 'delete':
      deleteEndpoint(endpoint)
      break
  }
}

// URL复制相关方法
const copyWebhookUrl = async (endpoint) => {
  const url = getWebhookUrl(endpoint)
  if (!url) return
  
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success('接入地址已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const copyPreviewUrl = async () => {
  try {
    await navigator.clipboard.writeText(previewUrl.value)
    ElMessage.success('地址已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

// CRUD操作
const editEndpoint = async (endpoint) => {
  isEdit.value = true
  currentStep.value = 0
  Object.assign(endpointForm, { ...endpoint })
  
  // 加载字段映射
  if (endpoint.field_mapping && typeof endpoint.field_mapping === 'object') {
    fieldMappings.value = Object.entries(endpoint.field_mapping)
      .filter(([key, value]) => typeof key === 'string' && key.length > 0)
      .map(([key, value]) => ({
        system_field: String(key),
        external_field: String(value || ''),
        description: getFieldDescription(key)
      }))
  }
  
  await loadAvailableSystems()
  dialogVisible.value = true
}

const getFieldDescription = (field) => {
  const descriptions = {
    title: '告警标题',
    description: '告警描述',
    severity: '严重程度',
    source: '告警来源',
    host: '主机名'
  }
  return descriptions[field] || ''
}

const saveEndpoint = async () => {
  try {
    // 清理并验证表单数据
    const cleanedForm = {
      ...endpointForm,
      // 确保所有字符串字段都是有效的字符串
      name: String(endpointForm.name || ''),
      endpoint_type: String(endpointForm.endpoint_type || 'webhook'),
      description: String(endpointForm.description || ''),
      data_format: String(endpointForm.data_format || 'json'),
      // 确保field_mapping是有效的对象
      field_mapping: endpointForm.field_mapping && typeof endpointForm.field_mapping === 'object' 
        ? endpointForm.field_mapping 
        : {}
    }
    
    if (isEdit.value) {
      const response = await endpointApi.updateEndpoint(cleanedForm.id, cleanedForm)
      const updatedEndpoint = response.data.data
      
      const index = endpoints.value.findIndex(e => e.id === cleanedForm.id)
      if (index > -1) {
        if (cleanedForm.system_id) {
          const selectedSystem = availableSystems.value.find(s => s.id === cleanedForm.system_id)
          if (selectedSystem) {
            updatedEndpoint.system_name = selectedSystem.name
          }
        } else {
          updatedEndpoint.system_name = null
        }
        
        endpoints.value[index] = updatedEndpoint
      }
      ElMessage.success('接入点更新成功')
    } else {
      const response = await endpointApi.createEndpoint(cleanedForm)
      const newEndpoint = response.data.data
      
      if (cleanedForm.system_id) {
        const selectedSystem = availableSystems.value.find(s => s.id === cleanedForm.system_id)
        if (selectedSystem) {
          newEndpoint.system_name = selectedSystem.name
        }
      } else {
        newEndpoint.system_name = null
      }
      
      endpoints.value.push(newEndpoint)
      ElMessage.success('接入点创建成功')
    }
    
    dialogVisible.value = false
  } catch (error) {
    console.error('保存接入点失败:', error)
    const errorMessage = error.response?.data?.detail || error.message || '未知错误'
    ElMessage.error('操作失败: ' + errorMessage)
  }
}

const toggleEndpoint = async (endpoint) => {
  try {
    await endpointApi.updateEndpoint(endpoint.id, {
      enabled: endpoint.enabled
    })
    ElMessage.success(`接入点已${endpoint.enabled ? '启用' : '禁用'}`)
  } catch (error) {
    console.error('切换接入点状态失败:', error)
    endpoint.enabled = !endpoint.enabled
    ElMessage.error('切换状态失败: ' + (error.response?.data?.detail || error.message))
  }
}

const deleteEndpoint = async (endpoint) => {
  try {
    await ElMessageBox.confirm(`确定要删除接入点 "${endpoint.name}" 吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await endpointApi.deleteEndpoint(endpoint.id)
    
    const index = endpoints.value.findIndex(e => e.id === endpoint.id)
    if (index > -1) {
      endpoints.value.splice(index, 1)
    }
    
    ElMessage.success('接入点删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除接入点失败:', error)
      ElMessage.error('删除接入点失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const viewStats = (endpoint) => {
  currentEndpoint.value = endpoint
  statsDialogVisible.value = true
}

const viewTestData = (data) => {
  // 显示测试数据详情
  ElMessage.info('查看数据详情功能开发中...')
}

const showTestExample = () => {
  // 显示测试示例
  ElMessage.info('查看测试示例功能开发中...')
}

// 数据加载
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

const loadEndpoints = async () => {
  loading.value = true
  try {
    const response = await endpointApi.getEndpoints()
    endpoints.value = response.data.data || []
    
  } catch (error) {
    console.error('加载接入点失败:', error)
    ElMessage.error('加载接入点失败: ' + (error.response?.data?.detail || error.message))
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
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding: 24px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);

    .header-content {
      h1 {
        margin: 0 0 8px 0;
        font-size: 28px;
        font-weight: 600;
        color: #1f2937;
      }

      .header-desc {
        margin: 0;
        color: #6b7280;
        font-size: 16px;
      }
    }
  }

  .endpoints-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 20px;

    .endpoint-card {
      background: white;
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
      transition: all 0.3s ease;

      &:hover {
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        transform: translateY(-2px);
      }

      &.disabled {
        opacity: 0.6;
      }

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 16px;

        .endpoint-info {
          flex: 1;

          h3 {
            margin: 0 0 8px 0;
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
          }
        }

        .card-actions {
          display: flex;
          align-items: center;
          gap: 8px;
        }
      }

      .card-content {
        .endpoint-url {
          margin-bottom: 16px;

          label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #374151;
          }

          .url-display {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 12px;
            background: #f9fafb;
            border-radius: 8px;
            border: 1px solid #e5e7eb;

            code {
              flex: 1;
              font-family: 'Monaco', 'Consolas', monospace;
              font-size: 14px;
              color: #059669;
              word-break: break-all;
            }
          }
        }

        .endpoint-meta {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-bottom: 12px;

          .meta-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;

            .label {
              color: #6b7280;
              font-weight: 500;
            }

            .stats-text {
              color: #059669;
            }
          }
        }

        .endpoint-desc {
          padding: 12px;
          background: #f0f9ff;
          border-radius: 8px;
          font-size: 14px;
          color: #1e40af;
          line-height: 1.5;
        }
      }
    }

    .empty-state {
      grid-column: 1 / -1;
      text-align: center;
      padding: 60px 20px;
    }
  }
}

.endpoint-dialog {
  :deep(.el-dialog) {
    margin: 20px auto;
    max-width: 90vw;
  }

  .setup-steps {
    margin-bottom: 32px;
  }

  :deep(.el-dialog__body) {
    padding: 20px 30px;
    max-height: 70vh;
    overflow-y: auto;
  }

  .step-content {
    min-height: 400px;
    padding: 0 16px;

    .step-panel {
      width: 100%;
      
      .config-section {
        margin-bottom: 24px;

        h4 {
          margin: 0 0 16px 0;
          font-size: 18px;
          font-weight: 600;
          color: #1f2937;
        }

        .section-alert {
          margin-bottom: 20px;

          ol {
            margin: 0;
            padding-left: 20px;

            li {
              margin-bottom: 4px;
            }
          }
        }

        .url-preview {
          .el-input {
            margin-bottom: 8px;
          }
        }

        .field-mapping-config {
          display: flex;
          align-items: center;
        }
      }

      .type-radio-group {
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .type-radio {
        display: block !important;
        width: 100% !important;
        margin-bottom: 0 !important;
        margin-right: 0 !important;
        padding: 16px;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        transition: all 0.3s;
        height: auto;

        &:hover {
          border-color: #3b82f6;
          background: #eff6ff;
        }

        &.is-checked {
          border-color: #409eff;
          background: #ecf5ff;
        }

        :deep(.el-radio__input) {
          margin-top: 2px;
        }

        :deep(.el-radio__label) {
          padding-left: 8px;
          font-size: 14px;
          line-height: 1.4;
        }

        .radio-content {
          display: block;

          strong {
            display: block;
            margin-bottom: 4px;
            color: #1f2937;
            font-weight: 600;
            font-size: 16px;
          }

          span {
            display: block;
            color: #6b7280;
            font-size: 14px;
            line-height: 1.4;
          }
        }
      }

      .test-section {
        .listening-section {
          margin-bottom: 24px;

          .listening-alert {
            .listening-actions {
              margin-top: 12px;
              display: flex;
              gap: 8px;
            }
          }
        }

        .received-data-section {
          margin-bottom: 24px;

          h5 {
            margin: 0 0 16px 0;
            font-size: 16px;
            font-weight: 600;
          }

          .data-list {
            .data-item {
              padding: 16px;
              border: 1px solid #e5e7eb;
              border-radius: 8px;
              margin-bottom: 12px;

              &.success {
                border-color: #10b981;
                background: #f0fff4;
              }

              &.error {
                border-color: #ef4444;
                background: #fef2f2;
              }

              .data-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;

                .data-time {
                  font-size: 14px;
                  color: #6b7280;
                }
              }

              .data-preview {
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 14px;
                color: #374151;
                margin-bottom: 12px;
              }

              .data-actions {
                display: flex;
                gap: 8px;
              }
            }
          }
        }

        .test-guidance {
          h5 {
            margin: 0 0 16px 0;
            font-size: 16px;
            font-weight: 600;
          }
        }
      }
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

.field-mapping-content {
  .el-table {
    margin-bottom: 16px;
  }
}

.stats-content {
  .stats-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--el-border-color);

    h3 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
    }
  }

  .stats-details {
    h4 {
      margin: 0 0 15px 0;
      font-size: 16px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
  }

  .stat-card {
    text-align: center;
    padding: 20px;
    background: var(--el-fill-color-lighter);
    border-radius: 8px;
    border: 1px solid var(--el-border-color);

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
</style>