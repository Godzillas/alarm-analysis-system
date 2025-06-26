<template>
  <div class="system-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <h3>系统管理</h3>
          <div class="header-actions">
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon>
              创建系统
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 筛选器 -->
      <div class="filters">
        <el-form :model="filters" inline class="filter-form">
          <el-form-item label="搜索">
            <el-input 
              v-model="filters.search" 
              placeholder="搜索系统名称、编码..."
              clearable
              class="el-input--search"
            />
          </el-form-item>
          
          <el-form-item label="状态">
            <el-select v-model="filters.enabled" placeholder="全部" clearable class="el-select--status">
              <el-option label="启用" :value="true" />
              <el-option label="禁用" :value="false" />
            </el-select>
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <!-- 系统表格 -->
      <el-table 
        :data="systemStore.systems" 
        :loading="systemStore.loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="name" label="系统名称" min-width="150" />
        <el-table-column prop="code" label="系统编码" width="120" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="owner" label="负责人" width="120" />
        
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'danger'">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="created_at" label="创建时间" width="150">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="viewSystem(row)">
              查看
            </el-button>
            <el-button type="success" size="small" @click="editSystem(row)">
              编辑
            </el-button>
            <el-button type="danger" size="small" @click="deleteSystem(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="systemStore.pagination.page"
          v-model:page-size="systemStore.pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="systemStore.pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 创建/编辑系统对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑系统' : '创建系统'"
      width="600px"
    >
      <el-form 
        ref="formRef"
        :model="formData" 
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="系统名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入系统名称" />
        </el-form-item>
        
        <el-form-item label="系统编码" prop="code">
          <el-input v-model="formData.code" placeholder="请输入系统编码" />
        </el-form-item>
        
        <el-form-item label="系统描述" prop="description">
          <el-input 
            v-model="formData.description" 
            type="textarea" 
            placeholder="请输入系统描述"
            :rows="3"
          />
        </el-form-item>
        
        <el-form-item label="负责人" prop="owner">
          <el-input v-model="formData.owner" placeholder="请输入负责人姓名" />
        </el-form-item>
        
        <el-form-item label="联系方式" prop="contact_info">
          <ContactInfoEditor v-model="formData.contact_info" />
        </el-form-item>
        
        <el-form-item label="启用状态" prop="enabled">
          <el-switch v-model="formData.enabled" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 系统详情对话框 -->
    <SystemDetailDialog 
      v-model="detailVisible"
      :system="currentSystem"
      @refresh="refreshData"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useSystemStore } from '@/store/system'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import ContactInfoEditor from './components/ContactInfoEditor.vue'
import SystemDetailDialog from './components/SystemDetailDialog.vue'

const systemStore = useSystemStore()

// 筛选器
const filters = reactive({
  search: '',
  enabled: null
})

// 对话框控制
const dialogVisible = ref(false)
const detailVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const currentSystem = ref(null)

// 表单相关
const formRef = ref()
const formData = reactive({
  name: '',
  code: '',
  description: '',
  owner: '',
  contact_info: {},
  enabled: true
})

const formRules = {
  name: [
    { required: true, message: '请输入系统名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入系统编码', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_-]+$/, message: '编码只能包含字母、数字、下划线和横线', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ]
}

// 格式化时间
const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}

// 显示创建对话框
const showCreateDialog = () => {
  isEdit.value = false
  dialogVisible.value = true
  resetForm()
}

// 编辑系统
const editSystem = (system) => {
  isEdit.value = true
  currentSystem.value = system
  dialogVisible.value = true
  
  // 填充表单数据
  Object.assign(formData, {
    name: system.name,
    code: system.code,
    description: system.description || '',
    owner: system.owner || '',
    contact_info: system.contact_info || {},
    enabled: system.enabled
  })
}

// 查看系统详情
const viewSystem = (system) => {
  currentSystem.value = system
  detailVisible.value = true
}

// 删除系统
const deleteSystem = async (system) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除系统 "${system.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await systemStore.deleteSystem(system.id)
    ElMessage.success('删除成功')
    refreshData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 提交表单
const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitting.value = true
    
    if (isEdit.value) {
      await systemStore.updateSystem(currentSystem.value.id, formData)
      ElMessage.success('更新成功')
    } else {
      await systemStore.createSystem(formData)
      ElMessage.success('创建成功')
    }
    
    dialogVisible.value = false
    refreshData()
  } catch (error) {
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    submitting.value = false
  }
}

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    name: '',
    code: '',
    description: '',
    owner: '',
    contact_info: {},
    enabled: true
  })
  
  if (formRef.value) {
    formRef.value.clearValidate()
  }
}

// 搜索
const handleSearch = () => {
  systemStore.setFilters(filters)
  systemStore.fetchSystems()
}

// 重置搜索
const handleReset = () => {
  Object.assign(filters, {
    search: '',
    enabled: null
  })
  systemStore.clearFilters()
  systemStore.fetchSystems()
}

// 刷新数据
const refreshData = () => {
  systemStore.fetchSystems()
}

// 分页处理
const handleSizeChange = (val) => {
  systemStore.setPageSize(val)
  systemStore.fetchSystems()
}

const handleCurrentChange = (val) => {
  systemStore.setPage(val)
  systemStore.fetchSystems()
}

// 监听对话框关闭
watch(dialogVisible, (val) => {
  if (!val) {
    resetForm()
  }
})

onMounted(() => {
  systemStore.fetchSystems()
})
</script>

<style lang="scss" scoped>
.system-management {
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
</style>