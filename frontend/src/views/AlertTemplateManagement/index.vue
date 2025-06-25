<template>
  <div class="alert-template-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>告警模板管理</h2>
      <p>管理和配置告警通知模板，支持邮件、Webhook和飞书等多种类型</p>
    </div>

    <!-- 操作栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          新建模板
        </el-button>
        <el-button @click="handleShowBuiltinTemplates">
          <el-icon><Collection /></el-icon>
          内置模板库
        </el-button>
        <el-button @click="handleRefresh">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
      <div class="toolbar-right">
        <el-input
          v-model="searchQuery"
          placeholder="搜索模板名称或描述"
          style="width: 300px; margin-right: 10px"
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select
          v-model="filterType"
          placeholder="类型筛选"
          clearable
          style="width: 120px; margin-right: 10px"
          @change="handleFilter"
        >
          <el-option
            v-for="type in alertTemplateStore.templateTypes"
            :key="type.value"
            :label="type.label"
            :value="type.value"
          />
        </el-select>
        <el-select
          v-model="filterCategory"
          placeholder="分类筛选"
          clearable
          style="width: 120px"
          @change="handleFilter"
        >
          <el-option
            v-for="category in alertTemplateStore.templateCategories"
            :key="category.value"
            :label="category.label"
            :value="category.value"
          />
        </el-select>
      </div>
    </div>

    <!-- 模板列表 -->
    <el-card class="template-list">
      <el-table
        :data="alertTemplateStore.alertTemplates"
        :loading="alertTemplateStore.loading"
        stripe
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="name" label="模板名称" width="200">
          <template #default="{ row }">
            <div class="template-name">
              <span class="name">{{ row.name }}</span>
              <el-tag v-if="row.is_builtin" type="info" size="small">内置</el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="template_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.template_type)">
              {{ alertTemplateStore.getTemplateTypeLabel(row.template_type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="category" label="分类" width="120">
          <template #default="{ row }">
            <el-tag type="info">
              {{ alertTemplateStore.getCategoryLabel(row.category) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="描述" show-overflow-tooltip />

        <el-table-column prop="enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              @change="handleToggleEnabled(row)"
            />
          </template>
        </el-table-column>

        <el-table-column prop="usage_count" label="使用次数" width="100" />

        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="handlePreview(row)"
            >
              预览
            </el-button>
            <el-button
              type="info"
              size="small"
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-button
              type="success"
              size="small"
              @click="handleCopy(row)"
            >
              复制
            </el-button>
            <el-button
              v-if="!row.is_builtin"
              type="danger"
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
            <el-dropdown @command="handleCommand">
              <el-button size="small">
                更多<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :command="`stats:${row.id}`">统计信息</el-dropdown-item>
                  <el-dropdown-item :command="`export:${row.id}`">导出模板</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 创建/编辑模板对话框 -->
    <template-editor-dialog
      v-model="editorVisible"
      :template="selectedTemplate"
      :mode="editorMode"
      @saved="handleTemplateSaved"
    />

    <!-- 模板预览对话框 -->
    <template-preview-dialog
      v-model="previewVisible"
      :template="selectedTemplate"
    />

    <!-- 内置模板库对话框 -->
    <builtin-templates-dialog
      v-model="builtinVisible"
      @template-selected="handleBuiltinTemplateSelected"
    />

    <!-- 统计信息对话框 -->
    <template-stats-dialog
      v-model="statsVisible"
      :template="selectedTemplate"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search, Collection, ArrowDown } from '@element-plus/icons-vue'
import { useAlertTemplateStore } from '@/store/alertTemplate'
import TemplateEditorDialog from './components/TemplateEditorDialog.vue'
import TemplatePreviewDialog from './components/TemplatePreviewDialog.vue'
import BuiltinTemplatesDialog from './components/BuiltinTemplatesDialog.vue'
import TemplateStatsDialog from './components/TemplateStatsDialog.vue'
import dayjs from 'dayjs'

const alertTemplateStore = useAlertTemplateStore()

// 数据状态
const selectedTemplates = ref([])
const selectedTemplate = ref(null)
const searchQuery = ref('')
const filterType = ref('')
const filterCategory = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 对话框状态
const editorVisible = ref(false)
const previewVisible = ref(false)
const builtinVisible = ref(false)
const statsVisible = ref(false)
const editorMode = ref('create') // 'create' | 'edit' | 'copy'

// 工具函数
const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const getTypeTagType = (type) => {
  const typeMap = {
    email: 'success',
    webhook: 'warning',
    feishu: 'info'
  }
  return typeMap[type] || 'primary'
}

// 事件处理
const handleSelectionChange = (selection) => {
  selectedTemplates.value = selection
}

const handleCreate = () => {
  selectedTemplate.value = null
  editorMode.value = 'create'
  editorVisible.value = true
}

const handleEdit = (template) => {
  selectedTemplate.value = template
  editorMode.value = 'edit'
  editorVisible.value = true
}

const handleCopy = (template) => {
  selectedTemplate.value = { ...template }
  editorMode.value = 'copy'
  editorVisible.value = true
}

const handlePreview = (template) => {
  selectedTemplate.value = template
  previewVisible.value = true
}

const handleDelete = async (template) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除模板 "${template.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await alertTemplateStore.deleteAlertTemplate(template.id)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleToggleEnabled = async (template) => {
  try {
    await alertTemplateStore.updateAlertTemplate(template.id, {
      enabled: template.enabled
    })
    ElMessage.success(template.enabled ? '已启用' : '已禁用')
  } catch (error) {
    template.enabled = !template.enabled // 回滚状态
    ElMessage.error('状态更新失败')
  }
}

const handleCommand = (command) => {
  const [action, id] = command.split(':')
  const template = alertTemplateStore.alertTemplates.find(t => t.id == id)
  
  if (action === 'stats') {
    selectedTemplate.value = template
    statsVisible.value = true
  } else if (action === 'export') {
    handleExportTemplate(template)
  }
}

const handleExportTemplate = (template) => {
  const dataStr = JSON.stringify(template, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${template.name}.json`
  link.click()
  URL.revokeObjectURL(url)
}

const handleShowBuiltinTemplates = () => {
  builtinVisible.value = true
}

const handleBuiltinTemplateSelected = (template) => {
  selectedTemplate.value = template
  editorMode.value = 'copy'
  editorVisible.value = true
  builtinVisible.value = false
}

const handleTemplateSaved = () => {
  editorVisible.value = false
  loadTemplates()
}

const handleSearch = () => {
  loadTemplates()
}

const handleFilter = () => {
  loadTemplates()
}

const handleRefresh = () => {
  loadTemplates()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  loadTemplates()
}

const handleCurrentChange = (page) => {
  currentPage.value = page
  loadTemplates()
}

// 数据加载
const loadTemplates = async () => {
  try {
    const params = {
      page: currentPage.value,
      size: pageSize.value,
      search: searchQuery.value || undefined,
      template_type: filterType.value || undefined,
      category: filterCategory.value || undefined
    }

    const result = await alertTemplateStore.fetchAlertTemplates(params)
    total.value = result.total || 0
  } catch (error) {
    ElMessage.error('加载模板列表失败')
  }
}

// 生命周期
onMounted(() => {
  loadTemplates()
})
</script>

<style lang="scss" scoped>
.alert-template-management {
  padding: 20px;

  .page-header {
    margin-bottom: 20px;
    
    h2 {
      margin: 0 0 8px 0;
      color: var(--el-text-color-primary);
    }
    
    p {
      margin: 0;
      color: var(--el-text-color-secondary);
      font-size: 14px;
    }
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    .toolbar-left {
      display: flex;
      gap: 10px;
    }
    
    .toolbar-right {
      display: flex;
      align-items: center;
    }
  }

  .template-list {
    .template-name {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .name {
        font-weight: 500;
      }
    }

    .pagination {
      display: flex;
      justify-content: center;
      margin-top: 20px;
    }
  }
}
</style>