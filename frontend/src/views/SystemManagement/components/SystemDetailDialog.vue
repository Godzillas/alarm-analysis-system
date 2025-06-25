<template>
  <el-dialog 
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="系统详情"
    width="800px"
    :close-on-click-modal="false"
  >
    <div v-if="system" class="system-detail">
      <el-tabs v-model="activeTab">
        <!-- 基本信息 -->
        <el-tab-pane label="基本信息" name="basic">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="系统名称">
              {{ system.name }}
            </el-descriptions-item>
            <el-descriptions-item label="系统编码">
              {{ system.code }}
            </el-descriptions-item>
            <el-descriptions-item label="负责人">
              {{ system.owner || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="system.enabled ? 'success' : 'danger'">
                {{ system.enabled ? '启用' : '禁用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="创建时间" :span="2">
              {{ formatTime(system.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="更新时间" :span="2">
              {{ formatTime(system.updated_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">
              {{ system.description || '-' }}
            </el-descriptions-item>
          </el-descriptions>
          
          <div v-if="system.contact_info && Object.keys(system.contact_info).length" class="contact-info">
            <h4>联系方式</h4>
            <el-descriptions :column="2" border>
              <el-descriptions-item v-if="system.contact_info.email" label="邮箱">
                {{ system.contact_info.email }}
              </el-descriptions-item>
              <el-descriptions-item v-if="system.contact_info.phone" label="电话">
                {{ system.contact_info.phone }}
              </el-descriptions-item>
              <el-descriptions-item v-if="system.contact_info.wechat" label="微信">
                {{ system.contact_info.wechat }}
              </el-descriptions-item>
              <el-descriptions-item v-if="system.contact_info.note" label="备注" :span="2">
                {{ system.contact_info.note }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-tab-pane>
        
        <!-- 统计信息 -->
        <el-tab-pane label="统计信息" name="stats">
          <div v-loading="statsLoading" class="stats-grid">
            <el-card class="stats-card">
              <div class="stats-item">
                <div class="stats-label">总告警数</div>
                <div class="stats-value">{{ stats.total_alarms || 0 }}</div>
              </div>
            </el-card>
            
            <el-card class="stats-card">
              <div class="stats-item">
                <div class="stats-label">活跃告警</div>
                <div class="stats-value critical">{{ stats.active_alarms || 0 }}</div>
              </div>
            </el-card>
            
            <el-card class="stats-card">
              <div class="stats-item">
                <div class="stats-label">严重告警</div>
                <div class="stats-value danger">{{ stats.critical_alarms || 0 }}</div>
              </div>
            </el-card>
            
            <el-card class="stats-card">
              <div class="stats-item">
                <div class="stats-label">接入点数</div>
                <div class="stats-value">{{ stats.total_endpoints || 0 }}</div>
              </div>
            </el-card>
            
            <el-card class="stats-card">
              <div class="stats-item">
                <div class="stats-label">活跃接入点</div>
                <div class="stats-value success">{{ stats.active_endpoints || 0 }}</div>
              </div>
            </el-card>
            
            <el-card class="stats-card">
              <div class="stats-item">
                <div class="stats-label">关联用户</div>
                <div class="stats-value">{{ stats.user_count || 0 }}</div>
              </div>
            </el-card>
          </div>
        </el-tab-pane>
        
        <!-- 关联用户 -->
        <el-tab-pane label="关联用户" name="users">
          <div class="users-section">
            <div class="section-header">
              <h4>关联用户管理</h4>
              <el-button type="primary" size="small" @click="showAddUserDialog">
                <el-icon><Plus /></el-icon>
                添加用户
              </el-button>
            </div>
            
            <el-table 
              :data="systemUsers" 
              :loading="usersLoading"
              stripe
              style="width: 100%"
            >
              <el-table-column prop="username" label="用户名" />
              <el-table-column prop="full_name" label="姓名" />
              <el-table-column prop="email" label="邮箱" />
              <el-table-column prop="is_active" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.is_active ? 'success' : 'danger'">
                    {{ row.is_active ? '正常' : '禁用' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button 
                    type="danger" 
                    size="small" 
                    @click="removeUser(row)"
                  >
                    移除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
    
    <!-- 添加用户对话框 -->
    <el-dialog
      v-model="addUserVisible"
      title="添加用户到系统"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form>
        <el-form-item label="选择用户">
          <el-select
            v-model="selectedUserId"
            placeholder="请选择用户"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="user in availableUsers"
              :key="user.id"
              :label="`${user.username} (${user.full_name || user.email})`"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="addUserVisible = false">取消</el-button>
        <el-button type="primary" @click="addUser" :loading="addingUser">
          确定
        </el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useSystemStore } from '@/store/system'
import { useUserStore } from '@/store/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const props = defineProps({
  modelValue: Boolean,
  system: Object
})

const emit = defineEmits(['update:modelValue', 'refresh'])

const systemStore = useSystemStore()
const userStore = useUserStore()

// 状态
const activeTab = ref('basic')
const stats = ref({})
const statsLoading = ref(false)
const systemUsers = ref([])
const usersLoading = ref(false)
const addUserVisible = ref(false)
const selectedUserId = ref(null)
const addingUser = ref(false)
const availableUsers = ref([])

// 格式化时间
const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

// 加载统计信息
const loadStats = async () => {
  if (!props.system) return
  
  statsLoading.value = true
  try {
    stats.value = await systemStore.getSystemStats(props.system.id)
  } catch (error) {
    ElMessage.error('加载统计信息失败')
  } finally {
    statsLoading.value = false
  }
}

// 加载系统用户
const loadSystemUsers = async () => {
  if (!props.system) return
  
  usersLoading.value = true
  try {
    systemUsers.value = await systemStore.getSystemUsers(props.system.id)
  } catch (error) {
    ElMessage.error('加载用户列表失败')
  } finally {
    usersLoading.value = false
  }
}

// 加载可用用户
const loadAvailableUsers = async () => {
  try {
    const response = await userStore.fetchUsers({ page: 1, page_size: 1000 })
    const systemUserIds = systemUsers.value.map(u => u.id)
    availableUsers.value = response.data.filter(user => !systemUserIds.includes(user.id))
  } catch (error) {
    ElMessage.error('加载用户列表失败')
  }
}

// 显示添加用户对话框
const showAddUserDialog = async () => {
  await loadAvailableUsers()
  addUserVisible.value = true
}

// 添加用户
const addUser = async () => {
  if (!selectedUserId.value) {
    ElMessage.warning('请选择用户')
    return
  }
  
  addingUser.value = true
  try {
    await systemStore.addUserToSystem(props.system.id, selectedUserId.value)
    ElMessage.success('添加成功')
    addUserVisible.value = false
    selectedUserId.value = null
    await loadSystemUsers()
    emit('refresh')
  } catch (error) {
    ElMessage.error('添加失败')
  } finally {
    addingUser.value = false
  }
}

// 移除用户
const removeUser = async (user) => {
  try {
    await ElMessageBox.confirm(
      `确定要将用户 "${user.username}" 从系统中移除吗？`,
      '确认移除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await systemStore.removeUserFromSystem(props.system.id, user.id)
    ElMessage.success('移除成功')
    await loadSystemUsers()
    emit('refresh')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('移除失败')
    }
  }
}

// 监听系统变化
watch(() => props.system, (newSystem) => {
  if (newSystem) {
    loadStats()
    loadSystemUsers()
  }
}, { immediate: true })

// 监听tab变化
watch(activeTab, (newTab) => {
  if (newTab === 'stats' && props.system) {
    loadStats()
  } else if (newTab === 'users' && props.system) {
    loadSystemUsers()
  }
})

onMounted(() => {
  // 确保用户store已初始化
  if (!userStore.users.length) {
    userStore.fetchUsers({ page: 1, page_size: 1000 })
  }
})
</script>

<style lang="scss" scoped>
.system-detail {
  .contact-info {
    margin-top: 20px;
    
    h4 {
      margin: 0 0 16px 0;
      color: var(--el-text-color-primary);
    }
  }
  
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    
    .stats-card {
      .stats-item {
        text-align: center;
        
        .stats-label {
          font-size: 14px;
          color: var(--el-text-color-regular);
          margin-bottom: 8px;
        }
        
        .stats-value {
          font-size: 24px;
          font-weight: 600;
          color: var(--el-text-color-primary);
          
          &.success {
            color: #67c23a;
          }
          
          &.critical {
            color: #e6a23c;
          }
          
          &.danger {
            color: #f56c6c;
          }
        }
      }
    }
  }
  
  .users-section {
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
}
</style>