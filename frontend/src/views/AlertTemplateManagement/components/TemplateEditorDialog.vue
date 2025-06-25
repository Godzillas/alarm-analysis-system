<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="1200px"
    :close-on-click-modal="false"
    @opened="onDialogOpened"
    @close="onDialogClose"
  >
    <div v-loading="loading" class="template-editor">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="模板名称" prop="name">
              <el-input
                v-model="formData.name"
                placeholder="请输入模板名称"
                :disabled="formData.is_builtin"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="模板类型" prop="template_type">
              <el-select
                v-model="formData.template_type"
                placeholder="选择模板类型"
                :disabled="mode === 'edit'"
                @change="handleTypeChange"
              >
                <el-option
                  v-for="type in alertTemplateStore.templateTypes"
                  :key="type.value"
                  :label="type.label"
                  :value="type.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="分类" prop="category">
              <el-select
                v-model="formData.category"
                placeholder="选择分类"
              >
                <el-option
                  v-for="category in alertTemplateStore.templateCategories"
                  :key="category.value"
                  :label="category.label"
                  :value="category.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用状态">
              <el-switch v-model="formData.enabled" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="2"
            placeholder="请输入模板描述"
          />
        </el-form-item>

        <!-- 字段映射配置 -->
        <el-divider content-position="left">字段映射</el-divider>
        
        <el-form-item label="字段映射">
          <div class="field-mapping">
            <div class="mapping-header">
              <span>源字段</span>
              <span>目标字段</span>
              <span>操作</span>
            </div>
            <div
              v-for="(mapping, index) in fieldMappings"
              :key="index"
              class="mapping-item"
            >
              <el-select
                v-model="mapping.source_field"
                placeholder="选择源字段"
                filterable
                allow-create
              >
                <el-option
                  v-for="field in availableFields"
                  :key="field"
                  :label="field"
                  :value="field"
                />
              </el-select>
              <el-input
                v-model="mapping.target_field"
                placeholder="目标字段名"
              />
              <el-button
                type="danger"
                size="small"
                @click="removeMapping(index)"
              >
                删除
              </el-button>
            </div>
            <el-button type="primary" size="small" @click="addMapping">
              添加映射
            </el-button>
          </div>
        </el-form-item>

        <!-- 模板内容编辑 -->
        <el-divider content-position="left">模板内容</el-divider>

        <el-tabs v-model="activeTab" type="border-card">
          <!-- 主题模板 -->
          <el-tab-pane label="主题模板" name="subject">
            <div class="template-content">
              <div class="editor-toolbar">
                <el-button-group>
                  <el-button size="small" @click="insertVariable('subject', '{{title}}')">
                    插入标题
                  </el-button>
                  <el-button size="small" @click="insertVariable('subject', '{{severity}}')">
                    插入级别
                  </el-button>
                  <el-button size="small" @click="insertVariable('subject', '{{source}}')">
                    插入来源
                  </el-button>
                </el-button-group>
                <el-button type="success" size="small" @click="validateTemplate('subject')">
                  验证模板
                </el-button>
              </div>
              <el-input
                v-model="formData.subject_template"
                type="textarea"
                :rows="3"
                placeholder="请输入主题模板..."
              />
              <div class="template-help">
                支持变量: {{title}}, {{severity}}, {{source}}, {{host}}, {{description}} 等
              </div>
            </div>
          </el-tab-pane>

          <!-- 内容模板 -->
          <el-tab-pane label="内容模板" name="content">
            <div class="template-content">
              <div class="editor-toolbar">
                <el-button-group>
                  <el-button size="small" @click="insertVariable('content', '{{title}}')">
                    标题
                  </el-button>
                  <el-button size="small" @click="insertVariable('content', '{{description}}')">
                    描述
                  </el-button>
                  <el-button size="small" @click="insertVariable('content', '{{severity}}')">
                    级别
                  </el-button>
                  <el-button size="small" @click="insertVariable('content', '{{host}}')">
                    主机
                  </el-button>
                  <el-button size="small" @click="insertVariable('content', '{{created_at}}')">
                    时间
                  </el-button>
                </el-button-group>
                <el-button type="success" size="small" @click="validateTemplate('content')">
                  验证模板
                </el-button>
              </div>
              <el-input
                v-model="formData.content_template"
                type="textarea"
                :rows="10"
                placeholder="请输入内容模板..."
              />
              <div class="template-help">
                支持Jinja2语法，如条件判断、循环等
              </div>
            </div>
          </el-tab-pane>

          <!-- 实时预览 -->
          <el-tab-pane label="实时预览" name="preview">
            <div class="template-preview">
              <div class="preview-toolbar">
                <el-button type="primary" @click="generatePreview">
                  生成预览
                </el-button>
                <el-button @click="loadSampleData">
                  加载示例数据
                </el-button>
              </div>
              
              <div class="sample-data">
                <h4>示例数据</h4>
                <el-input
                  v-model="sampleDataStr"
                  type="textarea"
                  :rows="6"
                  placeholder="请输入JSON格式的示例数据..."
                />
              </div>

              <div v-if="previewResult" class="preview-result">
                <h4>预览结果</h4>
                <div class="preview-subject">
                  <strong>主题:</strong>
                  <div class="subject-content">{{ previewResult.subject }}</div>
                </div>
                <div class="preview-content">
                  <strong>内容:</strong>
                  <div class="content-preview" v-html="previewResult.content"></div>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-form>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">
          {{ mode === 'create' ? '创建' : '保存' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { useAlertTemplateStore } from '@/store/alertTemplate'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  template: {
    type: Object,
    default: null
  },
  mode: {
    type: String,
    default: 'create' // 'create' | 'edit' | 'copy'
  }
})

const emit = defineEmits(['update:modelValue', 'saved'])

const alertTemplateStore = useAlertTemplateStore()

const formRef = ref()
const loading = ref(false)
const saving = ref(false)
const activeTab = ref('subject')
const previewResult = ref(null)
const sampleDataStr = ref('')

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const dialogTitle = computed(() => {
  const titleMap = {
    create: '新建告警模板',
    edit: '编辑告警模板',
    copy: '复制告警模板'
  }
  return titleMap[props.mode] || '告警模板'
})

const formData = reactive({
  name: '',
  template_type: 'email',
  category: 'system',
  description: '',
  enabled: true,
  subject_template: '',
  content_template: '',
  field_mapping: {},
  is_builtin: false
})

const fieldMappings = ref([])
const availableFields = ref([
  'title', 'description', 'severity', 'source', 'host', 'service',
  'environment', 'created_at', 'updated_at', 'tags', 'labels'
])

const formRules = {
  name: [
    { required: true, message: '请输入模板名称', trigger: 'blur' },
    { min: 2, max: 100, message: '名称长度在 2 到 100 个字符', trigger: 'blur' }
  ],
  template_type: [
    { required: true, message: '请选择模板类型', trigger: 'change' }
  ],
  category: [
    { required: true, message: '请选择分类', trigger: 'change' }
  ]
}

const addMapping = () => {
  fieldMappings.value.push({
    source_field: '',
    target_field: ''
  })
}

const removeMapping = (index) => {
  fieldMappings.value.splice(index, 1)
  updateFieldMapping()
}

const updateFieldMapping = () => {
  formData.field_mapping = {}
  fieldMappings.value.forEach(mapping => {
    if (mapping.source_field && mapping.target_field) {
      formData.field_mapping[mapping.source_field] = mapping.target_field
    }
  })
}

const handleTypeChange = async (type) => {
  try {
    const fields = await alertTemplateStore.getTemplateFields(type)
    availableFields.value = fields
  } catch (error) {
    console.error('Failed to load template fields:', error)
  }
}

const insertVariable = (target, variable) => {
  const textarea = document.querySelector(`textarea[v-model="formData.${target}_template"]`)
  if (textarea) {
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const text = formData[`${target}_template`]
    formData[`${target}_template`] = text.substring(0, start) + variable + text.substring(end)
    
    nextTick(() => {
      textarea.focus()
      textarea.setSelectionRange(start + variable.length, start + variable.length)
    })
  }
}

const validateTemplate = async (target) => {
  try {
    const templateData = {
      template_type: formData.template_type,
      subject_template: target === 'subject' ? formData.subject_template : 'Test Subject',
      content_template: target === 'content' ? formData.content_template : 'Test Content'
    }
    
    await alertTemplateStore.validateTemplate(templateData)
    ElMessage.success('模板验证通过')
  } catch (error) {
    ElMessage.error(`模板验证失败: ${error.message}`)
  }
}

const loadSampleData = () => {
  const sampleData = {
    title: "数据库连接异常",
    description: "无法连接到主数据库，请检查网络连接和数据库状态",
    severity: "critical",
    source: "mysql-monitor",
    host: "db-primary-01.example.com",
    service: "mysql",
    environment: "production",
    created_at: new Date().toISOString(),
    tags: ["database", "connection", "critical"],
    labels: {
      region: "us-west-2",
      cluster: "prod-db-cluster"
    }
  }
  sampleDataStr.value = JSON.stringify(sampleData, null, 2)
}

const generatePreview = async () => {
  if (!sampleDataStr.value.trim()) {
    loadSampleData()
  }

  try {
    const sampleData = JSON.parse(sampleDataStr.value)
    const templateData = {
      template_type: formData.template_type,
      subject_template: formData.subject_template,
      content_template: formData.content_template,
      field_mapping: formData.field_mapping
    }

    const result = await alertTemplateStore.previewTemplate(templateData, sampleData)
    previewResult.value = result
  } catch (error) {
    if (error.name === 'SyntaxError') {
      ElMessage.error('示例数据格式错误，请检查JSON格式')
    } else {
      ElMessage.error(`预览生成失败: ${error.message}`)
    }
  }
}

const resetForm = () => {
  Object.assign(formData, {
    name: '',
    template_type: 'email',
    category: 'system',
    description: '',
    enabled: true,
    subject_template: '',
    content_template: '',
    field_mapping: {},
    is_builtin: false
  })
  fieldMappings.value = []
  previewResult.value = null
  sampleDataStr.value = ''
  activeTab.value = 'subject'
}

const loadTemplate = (template) => {
  if (template) {
    Object.assign(formData, {
      ...template,
      name: props.mode === 'copy' ? `${template.name} - 副本` : template.name
    })
    
    // 加载字段映射
    fieldMappings.value = Object.entries(template.field_mapping || {}).map(([source, target]) => ({
      source_field: source,
      target_field: target
    }))
  }
}

const handleSave = async () => {
  try {
    await formRef.value.validate()
    
    updateFieldMapping()
    saving.value = true

    const templateData = { ...formData }
    delete templateData.id
    delete templateData.created_at
    delete templateData.updated_at
    delete templateData.usage_count
    
    if (props.mode === 'create' || props.mode === 'copy') {
      await alertTemplateStore.createAlertTemplate(templateData)
      ElMessage.success('模板创建成功')
    } else {
      await alertTemplateStore.updateAlertTemplate(props.template.id, templateData)
      ElMessage.success('模板更新成功')
    }
    
    emit('saved')
  } catch (error) {
    if (error?.message) {
      ElMessage.error(`保存失败: ${error.message}`)
    }
  } finally {
    saving.value = false
  }
}

const onDialogOpened = () => {
  if (props.template) {
    loadTemplate(props.template)
  }
}

const onDialogClose = () => {
  resetForm()
  formRef.value?.clearValidate()
}

// 监听字段映射变化
watch(fieldMappings, updateFieldMapping, { deep: true })
</script>

<style lang="scss" scoped>
.template-editor {
  .field-mapping {
    border: 1px solid var(--el-border-color);
    border-radius: 4px;
    padding: 15px;
    background-color: var(--el-bg-color-page);

    .mapping-header {
      display: grid;
      grid-template-columns: 1fr 1fr 80px;
      gap: 10px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--el-border-color-lighter);
      margin-bottom: 10px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }

    .mapping-item {
      display: grid;
      grid-template-columns: 1fr 1fr 80px;
      gap: 10px;
      margin-bottom: 10px;
      align-items: center;
    }
  }

  .template-content {
    .editor-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }

    .template-help {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-top: 5px;
    }
  }

  .template-preview {
    .preview-toolbar {
      margin-bottom: 20px;
    }

    .sample-data {
      margin-bottom: 20px;
      
      h4 {
        margin: 0 0 10px 0;
        color: var(--el-text-color-primary);
      }
    }

    .preview-result {
      h4 {
        margin: 0 0 10px 0;
        color: var(--el-text-color-primary);
      }

      .preview-subject {
        margin-bottom: 15px;
        
        .subject-content {
          background: var(--el-bg-color-page);
          padding: 10px;
          border-radius: 4px;
          margin-top: 5px;
          font-weight: 500;
        }
      }

      .preview-content {
        .content-preview {
          background: var(--el-bg-color-page);
          padding: 15px;
          border-radius: 4px;
          margin-top: 5px;
          white-space: pre-wrap;
          line-height: 1.6;
        }
      }
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>