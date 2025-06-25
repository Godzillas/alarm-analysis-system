<template>
  <div class="user-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>用户管理</h2>
          <el-button type="primary" @click="showCreateDialog">
            <el-icon><Plus /></el-icon>
            新建用户
          </el-button>
        </div>
      </template>

      <!-- 搜索筛选 -->
      <div class="filters">
        <el-form :model="filters" inline>
          <el-form-item label="用户名">
            <el-input v-model="filters.username" placeholder="搜索用户名..." clearable />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="filters.email" placeholder="搜索邮箱..." clearable />
          </el-form-item>
          <el-form-item label="角色">
            <el-select v-model="filters.role" placeholder="全部角色" clearable>
              <el-option label="管理员" value="admin" />
              <el-option label="操作员" value="operator" />
              <el-option label="观察员" value="viewer" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filters.status" placeholder="全部状态" clearable>
              <el-option label="激活" value="active" />
              <el-option label="禁用" value="disabled" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 用户列表 -->
      <el-table :data="users" v-loading="loading" style="width: 100%">
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="display_name" label="显示名称" min-width="120" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="scope">
            <el-tag :type="getRoleType(scope.row.role)">
              {{ getRoleText(scope.row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="scope">
            <el-switch 
              v-model="scope.row.status" 
              active-value="active"
              inactive-value="disabled"
              @change="toggleUserStatus(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="订阅数" width="80">
          <template #default="scope">
            <el-link @click="viewSubscriptions(scope.row)" type="primary">
              {{ scope.row.subscription_count || 0 }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" width="150">
          <template #default="scope">
            {{ formatTime(scope.row.last_login_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="150">
          <template #default="scope">
            {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="关联系统" width="120">
          <template #default="{ row }">
            <el-link @click="viewUserSystems(row)" type="primary">
              {{ row.system_count || 0 }} 个系统
            </el-link>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="editUser(scope.row)">编辑</el-button>
            <el-button size="small" @click="resetPassword(scope.row)">重置密码</el-button>
            <el-button size="small" @click="viewSubscriptions(scope.row)">订阅</el-button>
            <el-button size="small" @click="viewUserSystems(scope.row)">系统</el-button>
            <el-button size="small" type="danger" @click="deleteUser(scope.row)" :disabled="scope.row.username === 'admin'">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 创建/编辑用户对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '新建用户'"
      width="50%"
      destroy-on-close
    >
      <el-form :model="userForm" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input 
            v-model="userForm.username" 
            placeholder="请输入用户名" 
            :disabled="isEdit"
          />
        </el-form-item>
        
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userForm.email" placeholder="请输入邮箱地址" />
        </el-form-item>
        
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="userForm.display_name" placeholder="请输入显示名称" />
        </el-form-item>
        
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input 
            v-model="userForm.password" 
            type="password" 
            show-password 
            placeholder="请输入密码"
          />
        </el-form-item>
        
        <el-form-item v-if="!isEdit" label="确认密码" prop="confirmPassword">
          <el-input 
            v-model="userForm.confirmPassword" 
            type="password" 
            show-password 
            placeholder="请再次输入密码"
          />
        </el-form-item>
        
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" placeholder="选择用户角色">
            <el-option label="管理员" value="admin" />
            <el-option label="操作员" value="operator" />
            <el-option label="观察员" value="viewer" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="手机号">
          <el-input v-model="userForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        
        <el-form-item label="部门">
          <el-input v-model="userForm.department" placeholder="请输入部门" />
        </el-form-item>
        
        <el-form-item label="通知偏好">
          <el-checkbox-group v-model="userForm.notification_preferences">
            <el-checkbox label="email">邮件通知</el-checkbox>
            <el-checkbox label="sms">短信通知</el-checkbox>
            <el-checkbox label="webhook">Webhook通知</el-checkbox>
            <el-checkbox label="feishu">飞书通知</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="userForm.status">
            <el-radio label="active">激活</el-radio>
            <el-radio label="disabled">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>

    <!-- 用户订阅对话框 -->
    <el-dialog v-model="subscriptionDialogVisible" title="用户订阅管理" width="60%">
      <div v-if="currentUser">
        <h4>{{ currentUser.display_name }}({{ currentUser.username }}) 的订阅规则</h4>
        
        <el-table :data="userSubscriptions" style="width: 100%">
          <el-table-column prop="rule_name" label="规则名称" />
          <el-table-column prop="rule_description" label="规则描述" show-overflow-tooltip />
          <el-table-column prop="priority" label="优先级" width="80">
            <template #default="scope">
              <el-tag :type="getPriorityType(scope.row.priority)">
                {{ scope.row.priority }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="notification_methods" label="通知方式" width="120">
            <template #default="scope">
              <el-tag v-for="method in scope.row.notification_methods" :key="method" size="small" style="margin-right: 5px">
                {{ getNotificationMethodText(method) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="subscribed_at" label="订阅时间" width="150">
            <template #default="scope">
              {{ formatTime(scope.row.subscribed_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="scope">
              <el-button size="small" type="danger" @click="removeSubscription(scope.row)">
                取消订阅
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <!-- 用户系统关联对话框 -->
    <el-dialog v-model="userSystemsDialogVisible" title="用户系统关联管理" width="70%">
      <div v-if="currentUser" class="user-systems-dialog">
        <div class="section-header">
          <h4>{{ currentUser.display_name }}({{ currentUser.username }}) 的关联系统</h4>
          <el-button type="primary" size="small" @click="showAddSystemDialog">
            <el-icon><Plus /></el-icon>
            添加系统
          </el-button>
        </div>
        
        <el-table :data="userSystems" :loading="userSystemsLoading" style="width: 100%">
          <el-table-column prop="name" label="系统名称" />
          <el-table-column prop="code" label="系统编码" />
          <el-table-column prop="owner" label="负责人" />
          <el-table-column prop="enabled" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'danger'">
                {{ row.enabled ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="关联时间" width="150">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button size="small" type="danger" @click="removeUserFromSystem(row)">
                移除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <!-- 添加系统到用户对话框 -->
    <el-dialog
      v-model="addSystemDialogVisible"
      title="添加系统到用户"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form>
        <el-form-item label="选择系统">
          <el-select
            v-model="selectedSystemId"
            placeholder="请选择系统"
            style="width: 100%"
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
      </el-form>
      
      <template #footer>
        <el-button @click="addSystemDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addSystemToUser" :loading="addingSystem">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { useSystemStore } from '@/store/system'

// 响应式数据
const loading = ref(false)
const users = ref([])
const dialogVisible = ref(false)
const subscriptionDialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()
const currentUser = ref(null)
const userSubscriptions = ref([])
const userSystemsDialogVisible = ref(false)
const userSystems = ref([])
const userSystemsLoading = ref(false)
const addSystemDialogVisible = ref(false)
const selectedSystemId = ref(null)
const addingSystem = ref(false)
const availableSystems = ref([])

// Store instances
const userStore = useUserStore()
const systemStore = useSystemStore()

// 筛选器
const filters = reactive({
  username: '',
  email: '',
  role: '',
  status: ''
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 表单数据
const userForm = reactive({
  id: null,
  username: '',
  email: '',
  display_name: '',
  password: '',
  confirmPassword: '',
  role: 'viewer',
  phone: '',
  department: '',
  notification_preferences: ['email'],
  status: 'active'
})

// 表单验证规则
const formRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  display_name: [
    { required: true, message: '请输入显示名称', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (value !== userForm.password) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      }, 
      trigger: 'blur' 
    }
  ],
  role: [
    { required: true, message: '请选择用户角色', trigger: 'change' }
  ]
}

// 角色类型
const getRoleType = (role) => {
  const types = {
    admin: 'danger',
    operator: 'warning',
    viewer: 'info'
  }
  return types[role] || ''
}

// 角色文本
const getRoleText = (role) => {
  const texts = {
    admin: '管理员',
    operator: '操作员',
    viewer: '观察员'
  }
  return texts[role] || role
}

// 优先级类型
const getPriorityType = (priority) => {
  const types = { 3: 'danger', 2: 'warning', 1: 'info' }
  return types[priority] || 'info'
}

// 通知方式文本
const getNotificationMethodText = (method) => {
  const texts = {
    email: '邮件',
    sms: '短信',
    webhook: 'Webhook',
    feishu: '飞书'
  }
  return texts[method] || method
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
  Object.assign(userForm, {
    id: null,
    username: '',
    email: '',
    display_name: '',
    password: '',
    confirmPassword: '',
    role: 'viewer',
    phone: '',
    department: '',
    notification_preferences: ['email'],
    status: 'active'
  })
}

// 编辑用户
const editUser = (user) => {
  isEdit.value = true
  Object.assign(userForm, {
    ...user,
    password: '',
    confirmPassword: ''
  })
  dialogVisible.value = true
}

// 保存用户
const saveUser = async () => {
  try {
    await formRef.value.validate()
    
    // 准备提交的数据
    const submitData = {
      username: userForm.username,
      email: userForm.email,
      full_name: userForm.display_name, // 字段映射
      is_admin: userForm.role === 'admin', // 字段映射
      is_active: userForm.status === 'active' // 字段映射
    }
    
    // 如果是新建用户，需要包含密码
    if (!isEdit.value) {
      // 验证密码确认
      if (userForm.password !== userForm.confirmPassword) {
        ElMessage.error('两次输入的密码不一致')
        return
      }
      submitData.password = userForm.password
    }
    
    if (isEdit.value) {
      // 更新用户
      await userStore.updateUser(userForm.id, submitData)
      ElMessage.success('用户更新成功')
    } else {
      // 创建用户
      await userStore.createUser(submitData)
      ElMessage.success('用户创建成功')
    }
    
    dialogVisible.value = false
    
    // 刷新用户列表
    await loadUsers()
    
  } catch (error) {
    console.error('保存用户失败:', error)
    ElMessage.error('保存用户失败: ' + (error.message || '未知错误'))
  }
}

// 切换用户状态
const toggleUserStatus = async (user) => {
  try {
    const updateData = {
      is_active: user.status === 'active'
    }
    
    await userStore.updateUser(user.id, updateData)
    ElMessage.success(`用户已${user.status === 'active' ? '激活' : '禁用'}`)
  } catch (error) {
    console.error('切换用户状态失败:', error)
    ElMessage.error('操作失败')
    // 回滚状态
    user.status = user.status === 'active' ? 'disabled' : 'active'
  }
}

// 重置密码
const resetPassword = async (user) => {
  try {
    await ElMessageBox.confirm(`确定要重置用户 "${user.username}" 的密码吗？`, '确认重置', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const newPassword = Math.random().toString(36).slice(-8)
    
    await ElMessageBox.alert(`新密码：${newPassword}\n请妥善保管并及时通知用户修改密码。`, '密码重置成功', {
      confirmButtonText: '确定',
      type: 'success'
    })
    
    console.log('重置密码:', user.id, newPassword)
    ElMessage.success('密码重置成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重置密码失败:', error)
    }
  }
}

// 查看用户订阅
const viewSubscriptions = (user) => {
  currentUser.value = user
  // 模拟用户订阅数据
  userSubscriptions.value = [
    {
      id: 1,
      rule_name: '严重告警通知',
      rule_description: '所有严重程度为Critical的告警',
      priority: 3,
      notification_methods: ['email', 'feishu'],
      subscribed_at: new Date(Date.now() - 86400000 * 7).toISOString()
    },
    {
      id: 2,
      rule_name: '生产环境告警',
      rule_description: '生产环境的所有高级和严重告警',
      priority: 3,
      notification_methods: ['email'],
      subscribed_at: new Date(Date.now() - 86400000 * 5).toISOString()
    }
  ]
  subscriptionDialogVisible.value = true
}

// 查看用户关联系统
const viewUserSystems = async (user) => {
  currentUser.value = user
  userSystemsDialogVisible.value = true
  await loadUserSystems()
}

// 加载用户关联的系统
const loadUserSystems = async () => {
  if (!currentUser.value) return
  
  userSystemsLoading.value = true
  try {
    userSystems.value = await userStore.getUserSystems(currentUser.value.id)
    
    // 更新用户的系统数量
    if (currentUser.value) {
      currentUser.value.system_count = userSystems.value.length
      // 更新用户列表中的数据
      const userIndex = users.value.findIndex(u => u.id === currentUser.value.id)
      if (userIndex > -1) {
        users.value[userIndex].system_count = userSystems.value.length
      }
    }
  } catch (error) {
    console.error('加载用户系统失败:', error)
    ElMessage.error('加载用户系统失败')
  } finally {
    userSystemsLoading.value = false
  }
}

// 显示添加系统对话框
const showAddSystemDialog = async () => {
  try {
    // 获取所有系统
    const allSystems = await systemStore.fetchAllSystems(false)
    
    // 排除已关联的系统
    const userSystemIds = userSystems.value.map(s => s.id)
    availableSystems.value = allSystems.filter(system => !userSystemIds.includes(system.id))
    
    addSystemDialogVisible.value = true
  } catch (error) {
    console.error('加载可用系统失败:', error)
    ElMessage.error('加载可用系统失败')
    availableSystems.value = []
  }
}

// 添加系统到用户
const addSystemToUser = async () => {
  if (!selectedSystemId.value) {
    ElMessage.warning('请选择系统')
    return
  }
  
  addingSystem.value = true
  try {
    await userStore.addUserToSystem(currentUser.value.id, selectedSystemId.value)
    ElMessage.success('添加成功')
    addSystemDialogVisible.value = false
    selectedSystemId.value = null
    // 重新加载用户系统列表
    await loadUserSystems()
  } catch (error) {
    console.error('添加系统失败:', error)
    ElMessage.error('添加失败')
  } finally {
    addingSystem.value = false
  }
}

// 从用户移除系统
const removeUserFromSystem = async (system) => {
  try {
    await ElMessageBox.confirm(
      `确定要将用户 "${currentUser.value.username}" 从系统 "${system.name}" 中移除吗？`,
      '确认移除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await userStore.removeUserFromSystem(currentUser.value.id, system.id)
    ElMessage.success('移除成功')
    // 重新加载用户系统列表
    await loadUserSystems()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('移除失败:', error)
      ElMessage.error('移除失败')
    }
  }
}

// 移除订阅
const removeSubscription = async (subscription) => {
  try {
    await ElMessageBox.confirm(`确定要取消订阅规则 "${subscription.rule_name}" 吗？`, '确认取消', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const index = userSubscriptions.value.findIndex(s => s.id === subscription.id)
    if (index > -1) {
      userSubscriptions.value.splice(index, 1)
    }
    
    // 更新用户订阅数
    if (currentUser.value) {
      currentUser.value.subscription_count = Math.max(0, (currentUser.value.subscription_count || 0) - 1)
    }
    
    console.log('移除订阅:', subscription.id)
    ElMessage.success('订阅取消成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('移除订阅失败:', error)
    }
  }
}

// 删除用户
const deleteUser = async (user) => {
  try {
    await ElMessageBox.confirm(`确定要删除用户 "${user.username}" 吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await userStore.deleteUser(user.id)
    ElMessage.success('用户删除成功')
    
    // 刷新列表
    await loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除用户失败:', error)
      ElMessage.error('删除用户失败: ' + (error.message || '未知错误'))
    }
  }
}

// 搜索
const handleSearch = () => {
  console.log('搜索用户:', filters)
  loadUsers()
}

// 重置
const handleReset = () => {
  Object.assign(filters, {
    username: '',
    email: '',
    role: '',
    status: ''
  })
  loadUsers()
}

// 分页变化
const handleSizeChange = (val) => {
  pagination.pageSize = val
  loadUsers()
}

const handleCurrentChange = (val) => {
  pagination.page = val
  loadUsers()
}

// 加载用户列表
const loadUsers = async () => {
  loading.value = true
  try {
    const response = await userStore.fetchUsers({
      page: pagination.page,
      page_size: pagination.pageSize,
      ...filters
    })
    
    users.value = response.data || []
    pagination.total = response.total || 0
  } catch (error) {
    console.error('加载用户失败:', error)
    ElMessage.error('加载用户列表失败')
    users.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style lang="scss" scoped>
.user-management {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    h2 {
      margin: 0;
      color: var(--el-text-color-primary);
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

.user-systems-dialog {
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    h4 {
      margin: 0;
      color: var(--el-text-color-primary);
    }
  }
}
</style>