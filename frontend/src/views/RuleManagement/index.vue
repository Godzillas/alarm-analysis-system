<template>
  <div class="rule-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>订阅规则管理</h2>
          <el-button type="primary" @click="showCreateDialog">
            <el-icon><Plus /></el-icon>
            新建规则
          </el-button>
        </div>
      </template>

      <!-- 规则列表 -->
      <el-table :data="rules" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="规则名称" min-width="150" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="条件" min-width="200">
          <template #default="scope">
            <el-tag v-for="condition in scope.row.conditions.slice(0, 2)" :key="condition.field" size="small" style="margin-right: 5px">
              {{ condition.field }} {{ condition.operator }} {{ condition.value }}
            </el-tag>
            <span v-if="scope.row.conditions.length > 2">...</span>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80">
          <template #default="scope">
            <el-tag :type="getPriorityType(scope.row.priority)">
              {{ scope.row.priority }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="scope">
            <el-switch 
              v-model="scope.row.enabled" 
              @change="toggleRule(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="订阅用户数" width="100">
          <template #default="scope">
            {{ scope.row.subscribers || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="editRule(scope.row)">编辑</el-button>
            <el-button size="small" @click="viewSubscribers(scope.row)">订阅者</el-button>
            <el-button size="small" type="danger" @click="deleteRule(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑规则对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑规则' : '新建规则'"
      width="60%"
      destroy-on-close
    >
      <el-form :model="ruleForm" :rules="formRules" ref="formRef" label-width="120px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="ruleForm.name" placeholder="请输入规则名称" />
        </el-form-item>
        
        <el-form-item label="描述" prop="description">
          <el-input type="textarea" v-model="ruleForm.description" placeholder="请输入规则描述" />
        </el-form-item>
        
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="ruleForm.priority" placeholder="选择优先级">
            <el-option label="高" :value="3" />
            <el-option label="中" :value="2" />
            <el-option label="低" :value="1" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="条件逻辑" prop="logic">
          <el-radio-group v-model="ruleForm.logic">
            <el-radio label="and">所有条件都满足(AND)</el-radio>
            <el-radio label="or">任一条件满足(OR)</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="匹配条件">
          <div class="conditions-section">
            <div v-for="(condition, index) in ruleForm.conditions" :key="index" class="condition-item">
              <el-row :gutter="10">
                <el-col :span="5">
                  <el-select v-model="condition.field" placeholder="字段">
                    <el-option label="严重程度" value="severity" />
                    <el-option label="状态" value="status" />
                    <el-option label="来源" value="source" />
                    <el-option label="主机" value="host" />
                    <el-option label="服务" value="service" />
                    <el-option label="环境" value="environment" />
                    <el-option label="标题" value="title" />
                  </el-select>
                </el-col>
                <el-col :span="4">
                  <el-select v-model="condition.operator" placeholder="操作符">
                    <el-option label="等于" value="equals" />
                    <el-option label="不等于" value="not_equals" />
                    <el-option label="包含" value="contains" />
                    <el-option label="不包含" value="not_contains" />
                    <el-option label="属于" value="in" />
                    <el-option label="不属于" value="not_in" />
                  </el-select>
                </el-col>
                <el-col :span="6">
                  <el-input 
                    v-if="condition.operator !== 'in' && condition.operator !== 'not_in'"
                    v-model="condition.value" 
                    placeholder="值" 
                  />
                  <el-select 
                    v-else
                    v-model="condition.values" 
                    multiple 
                    placeholder="选择多个值"
                    allow-create
                    filterable
                  >
                    <el-option v-if="condition.field === 'severity'" label="critical" value="critical" />
                    <el-option v-if="condition.field === 'severity'" label="high" value="high" />
                    <el-option v-if="condition.field === 'severity'" label="medium" value="medium" />
                    <el-option v-if="condition.field === 'severity'" label="low" value="low" />
                    <el-option v-if="condition.field === 'status'" label="active" value="active" />
                    <el-option v-if="condition.field === 'status'" label="resolved" value="resolved" />
                    <el-option v-if="condition.field === 'status'" label="acknowledged" value="acknowledged" />
                  </el-select>
                </el-col>
                <el-col :span="3">
                  <el-button @click="removeCondition(index)" type="danger" size="small">删除</el-button>
                </el-col>
              </el-row>
            </div>
            <el-button @click="addCondition" type="primary" size="small" style="margin-top: 10px">
              添加条件
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="时间限制">
          <el-checkbox v-model="enableTimeRestriction" @change="onTimeRestrictionChange">
            启用时间限制
          </el-checkbox>
          <div v-if="enableTimeRestriction" style="margin-top: 10px">
            <el-row :gutter="10">
              <el-col :span="12">
                <el-select v-model="ruleForm.time_restrictions.weekdays" multiple placeholder="工作日限制">
                  <el-option label="周一" :value="0" />
                  <el-option label="周二" :value="1" />
                  <el-option label="周三" :value="2" />
                  <el-option label="周四" :value="3" />
                  <el-option label="周五" :value="4" />
                  <el-option label="周六" :value="5" />
                  <el-option label="周日" :value="6" />
                </el-select>
              </el-col>
              <el-col :span="6">
                <el-time-picker 
                  v-model="timeRange[0]" 
                  format="HH:mm" 
                  placeholder="开始时间"
                  @change="updateTimeRange"
                />
              </el-col>
              <el-col :span="6">
                <el-time-picker 
                  v-model="timeRange[1]" 
                  format="HH:mm" 
                  placeholder="结束时间"
                  @change="updateTimeRange"
                />
              </el-col>
            </el-row>
          </div>
        </el-form-item>

        <el-form-item label="启用状态" prop="enabled">
          <el-switch v-model="ruleForm.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>

    <!-- 订阅者对话框 -->
    <el-dialog v-model="subscribersDialogVisible" title="规则订阅者" width="50%">
      <el-table :data="subscribers" style="width: 100%">
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="subscribed_at" label="订阅时间">
          <template #default="scope">
            {{ formatTime(scope.row.subscribed_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="scope">
            <el-button size="small" type="danger" @click="removeSubscriber(scope.row)">
              移除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

// 响应式数据
const loading = ref(false)
const rules = ref([])
const dialogVisible = ref(false)
const subscribersDialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()
const enableTimeRestriction = ref(false)
const timeRange = ref([])
const subscribers = ref([])

// 表单数据
const ruleForm = reactive({
  rule_id: '',
  name: '',
  description: '',
  priority: 2,
  logic: 'and',
  enabled: true,
  conditions: [],
  time_restrictions: {}
})

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入规则名称', trigger: 'blur' }
  ],
  priority: [
    { required: true, message: '请选择优先级', trigger: 'change' }
  ]
}

// 优先级类型
const getPriorityType = (priority) => {
  const types = { 3: 'danger', 2: 'warning', 1: 'info' }
  return types[priority] || 'info'
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString('zh-CN')
}

// 显示创建对话框
const showCreateDialog = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  Object.assign(ruleForm, {
    rule_id: '',
    name: '',
    description: '',
    priority: 2,
    logic: 'and',
    enabled: true,
    conditions: [],
    time_restrictions: {}
  })
  enableTimeRestriction.value = false
  timeRange.value = []
}

// 添加条件
const addCondition = () => {
  ruleForm.conditions.push({
    field: '',
    operator: 'equals',
    value: '',
    values: []
  })
}

// 移除条件
const removeCondition = (index) => {
  ruleForm.conditions.splice(index, 1)
}

// 时间限制变化
const onTimeRestrictionChange = (enabled) => {
  if (!enabled) {
    ruleForm.time_restrictions = {}
    timeRange.value = []
  } else {
    ruleForm.time_restrictions = {
      weekdays: [],
      time_range: {}
    }
  }
}

// 更新时间范围
const updateTimeRange = () => {
  if (timeRange.value[0] && timeRange.value[1]) {
    const startTime = new Date(timeRange.value[0]).toTimeString().substring(0, 5)
    const endTime = new Date(timeRange.value[1]).toTimeString().substring(0, 5)
    ruleForm.time_restrictions.time_range = {
      start: startTime,
      end: endTime
    }
  }
}

// 编辑规则
const editRule = (rule) => {
  isEdit.value = true
  Object.assign(ruleForm, { ...rule })
  
  // 处理时间限制
  if (rule.time_restrictions && Object.keys(rule.time_restrictions).length > 0) {
    enableTimeRestriction.value = true
    if (rule.time_restrictions.time_range) {
      const today = new Date().toDateString()
      timeRange.value = [
        new Date(`${today} ${rule.time_restrictions.time_range.start}`),
        new Date(`${today} ${rule.time_restrictions.time_range.end}`)
      ]
    }
  }
  
  dialogVisible.value = true
}

// 保存规则
const saveRule = async () => {
  try {
    await formRef.value.validate()
    
    // 构建规则数据
    const ruleData = {
      ...ruleForm,
      conditions: ruleForm.conditions.filter(c => c.field && c.operator)
    }
    
    if (isEdit.value) {
      // 更新规则
      console.log('更新规则:', ruleData)
      ElMessage.success('规则更新成功')
    } else {
      // 创建规则
      ruleData.rule_id = `rule_${Date.now()}`
      console.log('创建规则:', ruleData)
      ElMessage.success('规则创建成功')
    }
    
    dialogVisible.value = false
    await loadRules()
  } catch (error) {
    console.error('保存规则失败:', error)
  }
}

// 切换规则状态
const toggleRule = async (rule) => {
  try {
    console.log('切换规则状态:', rule.rule_id, rule.enabled)
    ElMessage.success(`规则已${rule.enabled ? '启用' : '禁用'}`)
  } catch (error) {
    console.error('切换规则状态失败:', error)
    rule.enabled = !rule.enabled // 回滚状态
  }
}

// 删除规则
const deleteRule = async (rule) => {
  try {
    await ElMessageBox.confirm(`确定要删除规则 "${rule.name}" 吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    console.log('删除规则:', rule.rule_id)
    ElMessage.success('规则删除成功')
    await loadRules()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除规则失败:', error)
    }
  }
}

// 查看订阅者
const viewSubscribers = (rule) => {
  // 模拟订阅者数据
  subscribers.value = [
    {
      id: 1,
      username: 'admin',
      email: 'admin@example.com',
      subscribed_at: new Date().toISOString()
    },
    {
      id: 2,
      username: 'user1',
      email: 'user1@example.com',
      subscribed_at: new Date(Date.now() - 86400000).toISOString()
    }
  ]
  subscribersDialogVisible.value = true
}

// 移除订阅者
const removeSubscriber = async (subscriber) => {
  try {
    await ElMessageBox.confirm(`确定要移除订阅者 "${subscriber.username}" 吗？`, '确认移除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    console.log('移除订阅者:', subscriber.id)
    ElMessage.success('订阅者移除成功')
    // 重新加载订阅者列表
  } catch (error) {
    if (error !== 'cancel') {
      console.error('移除订阅者失败:', error)
    }
  }
}

// 加载规则列表
const loadRules = async () => {
  loading.value = true
  try {
    // 模拟规则数据
    rules.value = [
      {
        rule_id: 'rule_critical',
        name: '严重告警通知',
        description: '所有严重程度为Critical的告警',
        priority: 3,
        logic: 'and',
        enabled: true,
        conditions: [
          { field: 'severity', operator: 'equals', value: 'critical' }
        ],
        time_restrictions: {},
        subscribers: 5
      },
      {
        rule_id: 'rule_production',
        name: '生产环境告警',
        description: '生产环境的所有高级和严重告警',
        priority: 3,
        logic: 'and',
        enabled: true,
        conditions: [
          { field: 'environment', operator: 'equals', value: 'production' },
          { field: 'severity', operator: 'in', values: ['critical', 'high'] }
        ],
        time_restrictions: {
          weekdays: [0, 1, 2, 3, 4],
          time_range: { start: '09:00', end: '18:00' }
        },
        subscribers: 8
      },
      {
        rule_id: 'rule_service_down',
        name: '服务下线告警',
        description: '包含"down"关键词的告警',
        priority: 2,
        logic: 'or',
        enabled: false,
        conditions: [
          { field: 'title', operator: 'contains', value: 'down' },
          { field: 'title', operator: 'contains', value: 'offline' }
        ],
        time_restrictions: {},
        subscribers: 3
      }
    ]
  } catch (error) {
    console.error('加载规则失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadRules()
})
</script>

<style lang="scss" scoped>
.rule-management {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    h2 {
      margin: 0;
      color: var(--el-text-color-primary);
    }
  }
  
  .conditions-section {
    border: 1px solid var(--el-border-color);
    border-radius: 4px;
    padding: 15px;
    background-color: var(--el-fill-color-lighter);
    
    .condition-item {
      margin-bottom: 10px;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
  }
}
</style>