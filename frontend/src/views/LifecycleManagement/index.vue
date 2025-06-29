<template>
  <div class="lifecycle-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>告警生命周期管理</h2>
          <el-button type="primary" @click="showCreateRuleDialog">
            <el-icon><Plus /></el-icon>
            新建规则
          </el-button>
        </div>
      </template>

      <!-- 统计信息 -->
      <el-row :gutter="16" style="margin-bottom: 20px;">
        <el-col :span="6">
          <el-statistic title="活跃规则" :value="activeRulesCount">
            <template #suffix>
              <el-icon style="vertical-align: -0.125em">
                <CircleCheck />
              </el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="升级策略" :value="escalationPoliciesCount">
            <template #suffix>
              <el-icon style="vertical-align: -0.125em">
                <TrendCharts />
              </el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="自动操作" :value="automationStats.total_actions || 0">
            <template #suffix>
              <el-icon style="vertical-align: -0.125em">
                <Setting />
              </el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="SLA违约率" :value="slaStats.breach_rate" :precision="1" suffix="%">
            <template #suffix>%</template>
          </el-statistic>
        </el-col>
      </el-row>

      <!-- 标签页 -->
      <el-tabs v-model="activeTab" type="card">
        <!-- 生命周期规则 -->
        <el-tab-pane label="生命周期规则" name="rules">
          <el-table :data="rules" v-loading="rulesLoading" style="width: 100%">
            <el-table-column prop="name" label="规则名称" min-width="150" />
            <el-table-column label="条件" min-width="200">
              <template #default="scope">
                <el-tag v-for="(value, key) in scope.row.condition" :key="key" size="small" style="margin-right: 5px;">
                  {{ key }}: {{ Array.isArray(value) ? value.join(',') : value }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="动作" min-width="150">
              <template #default="scope">
                <el-tag :type="getActionTagType(scope.row.action.type)">
                  {{ getActionDisplayName(scope.row.action.type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="priority" label="优先级" width="80" />
            <el-table-column prop="enabled" label="状态" width="80">
              <template #default="scope">
                <el-switch 
                  v-model="scope.row.enabled" 
                  @change="toggleRule(scope.row)"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="scope">
                <el-button size="small" @click="editRule(scope.row)">编辑</el-button>
                <el-button size="small" type="danger" @click="deleteRule(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 升级策略 -->
        <el-tab-pane label="升级策略" name="policies">
          <div style="margin-bottom: 20px;">
            <el-button type="primary" @click="showCreatePolicyDialog">
              <el-icon><Plus /></el-icon>
              新建升级策略
            </el-button>
          </div>
          
          <el-table :data="escalationPolicies" v-loading="policiesLoading" style="width: 100%">
            <el-table-column prop="policy_name" label="策略名称" min-width="150" />
            <el-table-column label="升级级别" min-width="200">
              <template #default="scope">
                <el-tag v-for="level in scope.row.levels" :key="level.level" size="small" style="margin-right: 5px;">
                  L{{ level.level }}: {{ level.delay_minutes }}分钟
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="通知渠道" min-width="150">
              <template #default="scope">
                <span v-if="scope.row.levels.length > 0">
                  {{ scope.row.levels[0].notification_channels.join(', ') }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="scope">
                <el-button size="small" @click="editPolicy(scope.row)">编辑</el-button>
                <el-button size="small" type="danger" @click="deletePolicy(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 统计信息 -->
        <el-tab-pane label="统计信息" name="statistics">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-card class="box-card">
                <template #header>
                  <div class="card-header">
                    <span>自动化操作统计</span>
                  </div>
                </template>
                <div v-for="(count, action) in automationStats" :key="action" class="stat-item">
                  <span class="stat-label">{{ getActionDisplayName(action) }}:</span>
                  <span class="stat-value">{{ count }}</span>
                </div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card class="box-card">
                <template #header>
                  <div class="card-header">
                    <span>SLA统计</span>
                  </div>
                </template>
                <div class="stat-item">
                  <span class="stat-label">总数:</span>
                  <span class="stat-value">{{ slaStats.total || 0 }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">违约数:</span>
                  <span class="stat-value">{{ slaStats.breached || 0 }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">违约率:</span>
                  <span class="stat-value">{{ (slaStats.breach_rate || 0).toFixed(1) }}%</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">平均SLA时长:</span>
                  <span class="stat-value">{{ (slaStats.avg_sla_hours || 0).toFixed(1) }}小时</span>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 创建/编辑规则对话框 -->
    <el-dialog
      v-model="ruleDialogVisible"
      :title="isEditRule ? '编辑规则' : '新建规则'"
      width="60%"
      destroy-on-close
    >
      <el-form :model="ruleForm" :rules="ruleFormRules" ref="ruleFormRef" label-width="120px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="ruleForm.name" placeholder="请输入规则名称" />
        </el-form-item>
        
        <el-form-item label="优先级" prop="priority">
          <el-input-number v-model="ruleForm.priority" :min="1" :max="1000" />
        </el-form-item>
        
        <el-form-item label="启用状态">
          <el-switch v-model="ruleForm.enabled" />
        </el-form-item>
        
        <el-form-item label="规则模板">
          <el-select v-model="selectedTemplate" placeholder="选择规则模板" @change="applyTemplate" clearable>
            <el-option 
              v-for="template in ruleTemplates" 
              :key="template.name" 
              :label="template.name" 
              :value="template.name"
            >
              <span style="float: left">{{ template.name }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">{{ template.description }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        
        <el-form-item label="条件配置" prop="condition">
          <el-input 
            v-model="conditionJson" 
            type="textarea" 
            :rows="8"
            placeholder="请输入JSON格式的条件配置"
          />
        </el-form-item>
        
        <el-form-item label="动作配置" prop="action">
          <el-input 
            v-model="actionJson" 
            type="textarea" 
            :rows="6"
            placeholder="请输入JSON格式的动作配置"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="ruleDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveRule">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 创建/编辑升级策略对话框 -->
    <el-dialog
      v-model="policyDialogVisible"
      :title="isEditPolicy ? '编辑升级策略' : '新建升级策略'"
      width="60%"
      destroy-on-close
    >
      <el-form :model="policyForm" :rules="policyFormRules" ref="policyFormRef" label-width="120px">
        <el-form-item label="策略名称" prop="policy_name">
          <el-input v-model="policyForm.policy_name" placeholder="请输入策略名称" />
        </el-form-item>
        
        <el-form-item label="升级级别">
          <div v-for="(level, index) in policyForm.levels" :key="index" style="margin-bottom: 15px; border: 1px solid #ddd; padding: 15px; border-radius: 4px;">
            <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 10px;">
              <span style="font-weight: bold;">级别 {{ level.level }}</span>
              <el-button size="small" type="danger" @click="removeLevel(index)" v-if="policyForm.levels.length > 1">删除</el-button>
            </div>
            
            <el-row :gutter="10">
              <el-col :span="6">
                <el-form-item label="延迟时间(分钟)">
                  <el-input-number v-model="level.delay_minutes" :min="1" :max="1440" />
                </el-form-item>
              </el-col>
              <el-col :span="10">
                <el-form-item label="通知渠道">
                  <el-select v-model="level.notification_channels" multiple placeholder="选择通知渠道">
                    <el-option label="邮件" value="email" />
                    <el-option label="短信" value="sms" />
                    <el-option label="电话" value="phone" />
                    <el-option label="Slack" value="slack" />
                    <el-option label="微信" value="wechat" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="自动分配">
                  <el-switch v-model="level.auto_assign" />
                </el-form-item>
              </el-col>
            </el-row>
          </div>
          
          <el-button @click="addLevel" type="primary" plain>添加级别</el-button>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="policyDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="savePolicy">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, CircleCheck, TrendCharts, Setting } from '@element-plus/icons-vue'
import axios from 'axios'

// 响应式数据
const activeTab = ref('rules')
const rulesLoading = ref(false)
const policiesLoading = ref(false)
const rules = ref([])
const escalationPolicies = ref([])
const ruleTemplates = ref([])
const statistics = ref({})

// 规则对话框
const ruleDialogVisible = ref(false)
const isEditRule = ref(false)
const selectedTemplate = ref('')
const conditionJson = ref('')
const actionJson = ref('')
const currentEditingRule = ref(null)

const ruleForm = reactive({
  name: '',
  priority: 100,
  enabled: true,
  condition: {},
  action: {}
})

const ruleFormRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  priority: [{ required: true, message: '请输入优先级', trigger: 'blur' }]
}

// 升级策略对话框
const policyDialogVisible = ref(false)
const isEditPolicy = ref(false)
const currentEditingPolicy = ref(null)

const policyForm = reactive({
  policy_name: '',
  levels: [
    {
      level: 1,
      delay_minutes: 15,
      targets: [],
      notification_channels: ['email'],
      auto_assign: true
    }
  ]
})

const policyFormRules = {
  policy_name: [{ required: true, message: '请输入策略名称', trigger: 'blur' }]
}

// 计算属性
const activeRulesCount = computed(() => rules.value.filter(rule => rule.enabled).length)
const escalationPoliciesCount = computed(() => escalationPolicies.value.length)
const automationStats = computed(() => statistics.value.automation_stats || {})
const slaStats = computed(() => statistics.value.sla_stats || {})

// 表单引用
const ruleFormRef = ref()
const policyFormRef = ref()

// 获取数据
const fetchRules = async () => {
  rulesLoading.value = true
  try {
    const response = await axios.get('/api/lifecycle/rules')
    rules.value = response.data.data || []
  } catch (error) {
    console.error('获取规则列表失败:', error)
    ElMessage.error('获取规则列表失败')
  } finally {
    rulesLoading.value = false
  }
}

const fetchPolicies = async () => {
  policiesLoading.value = true
  try {
    const response = await axios.get('/api/lifecycle/escalation-policies')
    escalationPolicies.value = response.data.data || []
  } catch (error) {
    console.error('获取升级策略失败:', error)
    ElMessage.error('获取升级策略失败')
  } finally {
    policiesLoading.value = false
  }
}

const fetchTemplates = async () => {
  try {
    const response = await axios.get('/api/lifecycle/rule-templates')
    ruleTemplates.value = response.data.data || []
  } catch (error) {
    console.error('获取规则模板失败:', error)
  }
}

const fetchStatistics = async () => {
  try {
    const response = await axios.get('/api/lifecycle/statistics')
    statistics.value = response.data.data || {}
  } catch (error) {
    console.error('获取统计信息失败:', error)
  }
}

// 规则操作
const showCreateRuleDialog = () => {
  isEditRule.value = false
  currentEditingRule.value = null
  resetRuleForm()
  ruleDialogVisible.value = true
}

const editRule = (rule) => {
  isEditRule.value = true
  currentEditingRule.value = rule
  Object.assign(ruleForm, rule)
  conditionJson.value = JSON.stringify(rule.condition, null, 2)
  actionJson.value = JSON.stringify(rule.action, null, 2)
  ruleDialogVisible.value = true
}

const resetRuleForm = () => {
  ruleForm.name = ''
  ruleForm.priority = 100
  ruleForm.enabled = true
  ruleForm.condition = {}
  ruleForm.action = {}
  conditionJson.value = ''
  actionJson.value = ''
  selectedTemplate.value = ''
}

const applyTemplate = () => {
  const template = ruleTemplates.value.find(t => t.name === selectedTemplate.value)
  if (template) {
    ruleForm.name = template.name
    ruleForm.priority = template.priority
    ruleForm.condition = template.condition
    ruleForm.action = template.action
    conditionJson.value = JSON.stringify(template.condition, null, 2)
    actionJson.value = JSON.stringify(template.action, null, 2)
  }
}

const saveRule = async () => {
  if (!ruleFormRef.value) return
  
  try {
    await ruleFormRef.value.validate()
    
    // 解析JSON
    try {
      ruleForm.condition = JSON.parse(conditionJson.value)
      ruleForm.action = JSON.parse(actionJson.value)
    } catch (error) {
      ElMessage.error('JSON格式错误')
      return
    }
    
    if (isEditRule.value) {
      await axios.put(`/api/lifecycle/rules/${currentEditingRule.value.name}`, ruleForm)
      ElMessage.success('规则更新成功')
    } else {
      await axios.post('/api/lifecycle/rules', ruleForm)
      ElMessage.success('规则创建成功')
    }
    
    ruleDialogVisible.value = false
    await fetchRules()
  } catch (error) {
    console.error('保存规则失败:', error)
    ElMessage.error('保存规则失败')
  }
}

const deleteRule = async (rule) => {
  try {
    await ElMessageBox.confirm('确定要删除这个规则吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await axios.delete(`/api/lifecycle/rules/${rule.name}`)
    ElMessage.success('规则删除成功')
    await fetchRules()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除规则失败:', error)
      ElMessage.error('删除规则失败')
    }
  }
}

const toggleRule = async (rule) => {
  try {
    await axios.put(`/api/lifecycle/rules/${rule.name}`, rule)
    ElMessage.success(`规则已${rule.enabled ? '启用' : '禁用'}`)
  } catch (error) {
    console.error('切换规则状态失败:', error)
    ElMessage.error('切换规则状态失败')
    // 回滚状态
    rule.enabled = !rule.enabled
  }
}

// 升级策略操作
const showCreatePolicyDialog = () => {
  isEditPolicy.value = false
  currentEditingPolicy.value = null
  resetPolicyForm()
  policyDialogVisible.value = true
}

const editPolicy = (policy) => {
  isEditPolicy.value = true
  currentEditingPolicy.value = policy
  Object.assign(policyForm, policy)
  policyDialogVisible.value = true
}

const resetPolicyForm = () => {
  policyForm.policy_name = ''
  policyForm.levels = [
    {
      level: 1,
      delay_minutes: 15,
      targets: [],
      notification_channels: ['email'],
      auto_assign: true
    }
  ]
}

const addLevel = () => {
  const newLevel = policyForm.levels.length + 1
  policyForm.levels.push({
    level: newLevel,
    delay_minutes: 30,
    targets: [],
    notification_channels: ['email'],
    auto_assign: true
  })
}

const removeLevel = (index) => {
  policyForm.levels.splice(index, 1)
  // 重新编号
  policyForm.levels.forEach((level, i) => {
    level.level = i + 1
  })
}

const savePolicy = async () => {
  if (!policyFormRef.value) return
  
  try {
    await policyFormRef.value.validate()
    
    if (isEditPolicy.value) {
      await axios.put(`/api/lifecycle/escalation-policies/${currentEditingPolicy.value.policy_name}`, policyForm)
      ElMessage.success('升级策略更新成功')
    } else {
      await axios.post('/api/lifecycle/escalation-policies', policyForm)
      ElMessage.success('升级策略创建成功')
    }
    
    policyDialogVisible.value = false
    await fetchPolicies()
  } catch (error) {
    console.error('保存升级策略失败:', error)
    ElMessage.error('保存升级策略失败')
  }
}

const deletePolicy = async (policy) => {
  try {
    await ElMessageBox.confirm('确定要删除这个升级策略吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await axios.delete(`/api/lifecycle/escalation-policies/${policy.policy_name}`)
    ElMessage.success('升级策略删除成功')
    await fetchPolicies()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除升级策略失败:', error)
      ElMessage.error('删除升级策略失败')
    }
  }
}

// 工具函数
const getActionTagType = (actionType) => {
  const typeMap = {
    acknowledge: 'success',
    escalate: 'warning',
    sla_warning: 'warning',
    close: 'info',
    assign: 'primary'
  }
  return typeMap[actionType] || 'default'
}

const getActionDisplayName = (actionType) => {
  const nameMap = {
    acknowledge: '自动确认',
    escalate: '自动升级',
    sla_warning: 'SLA预警',
    close: '自动关闭',
    assign: '自动分配'
  }
  return nameMap[actionType] || actionType
}

const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString('zh-CN')
}

// 组件挂载
onMounted(async () => {
  await Promise.all([
    fetchRules(),
    fetchPolicies(),
    fetchTemplates(),
    fetchStatistics()
  ])
})
</script>

<style scoped>
.lifecycle-management {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  font-weight: 500;
}

.stat-value {
  font-weight: bold;
  color: #409eff;
}

.dialog-footer {
  text-align: right;
}

.box-card {
  margin-bottom: 20px;
}
</style>