<template>
  <el-dialog
    v-model="visible"
    title="内置模板库"
    width="1000px"
    @opened="loadBuiltinTemplates"
  >
    <div v-loading="loading" class="builtin-templates">
      <div class="template-filter">
        <el-input
          v-model="searchQuery"
          placeholder="搜索模板"
          style="width: 300px; margin-right: 15px"
          @input="filterTemplates"
        >
          <template #prefix>
            <el-icon><search /></el-icon>
          </template>
        </el-input>
        <el-select
          v-model="filterType"
          placeholder="类型筛选"
          clearable
          style="width: 120px; margin-right: 15px"
          @change="filterTemplates"
        >
          <el-option
            v-for="type in templateTypes"
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
          @change="filterTemplates"
        >
          <el-option
            v-for="category in templateCategories"
            :key="category.value"
            :label="category.label"
            :value="category.value"
          />
        </el-select>
      </div>

      <div class="template-grid">
        <div
          v-for="template in filteredTemplates"
          :key="template.id"
          class="template-card"
          :class="{ selected: selectedTemplate?.id === template.id }"
          @click="selectTemplate(template)"
        >
          <div class="card-header">
            <div class="template-name">{{ template.name }}</div>
            <div class="template-tags">
              <el-tag :type="getTypeTagType(template.template_type)" size="small">
                {{ getTypeLabel(template.template_type) }}
              </el-tag>
              <el-tag type="info" size="small">
                {{ getCategoryLabel(template.category) }}
              </el-tag>
            </div>
          </div>
          <div class="card-body">
            <div class="template-description">
              {{ template.description }}
            </div>
            <div class="template-preview">
              <div class="preview-section">
                <span class="preview-label">主题模板:</span>
                <div class="preview-content">{{ template.subject_template }}</div>
              </div>
              <div class="preview-section">
                <span class="preview-label">内容模板:</span>
                <div class="preview-content">{{ truncateText(template.content_template, 100) }}</div>
              </div>
            </div>
          </div>
          <div class="card-footer">
            <el-button
              type="primary"
              size="small"
              @click.stop="handleUseTemplate(template)"
            >
              使用模板
            </el-button>
            <el-button
              size="small"
              @click.stop="handlePreviewTemplate(template)"
            >
              预览
            </el-button>
          </div>
        </div>
      </div>

      <div v-if="filteredTemplates.length === 0 && !loading" class="empty-state">
        <el-empty description="没有找到匹配的模板" />
      </div>
    </div>

    <!-- 模板详情预览 -->
    <template-preview-dialog
      v-model="previewVisible"
      :template="previewTemplate"
    />

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">关闭</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useAlertTemplateStore } from '@/store/alertTemplate'
import TemplatePreviewDialog from './TemplatePreviewDialog.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'template-selected'])

const alertTemplateStore = useAlertTemplateStore()

const loading = ref(false)
const builtinTemplates = ref([])
const selectedTemplate = ref(null)
const searchQuery = ref('')
const filterType = ref('')
const filterCategory = ref('')
const previewVisible = ref(false)
const previewTemplate = ref(null)

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const templateTypes = computed(() => alertTemplateStore.templateTypes)
const templateCategories = computed(() => alertTemplateStore.templateCategories)

const filteredTemplates = computed(() => {
  let filtered = builtinTemplates.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(template =>
      template.name.toLowerCase().includes(query) ||
      template.description.toLowerCase().includes(query)
    )
  }

  if (filterType.value) {
    filtered = filtered.filter(template => template.template_type === filterType.value)
  }

  if (filterCategory.value) {
    filtered = filtered.filter(template => template.category === filterCategory.value)
  }

  return filtered
})

const getTypeTagType = (type) => {
  const typeMap = {
    email: 'success',
    webhook: 'warning',
    feishu: 'info'
  }
  return typeMap[type] || 'primary'
}

const getTypeLabel = (type) => {
  return alertTemplateStore.getTemplateTypeLabel(type)
}

const getCategoryLabel = (category) => {
  return alertTemplateStore.getCategoryLabel(category)
}

const truncateText = (text, maxLength) => {
  if (!text) return ''
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
}

const selectTemplate = (template) => {
  selectedTemplate.value = template
}

const handleUseTemplate = (template) => {
  emit('template-selected', template)
}

const handlePreviewTemplate = (template) => {
  previewTemplate.value = template
  previewVisible.value = true
}

const filterTemplates = () => {
  // 触发计算属性重新计算
}

const loadBuiltinTemplates = async () => {
  loading.value = true
  try {
    const templates = await alertTemplateStore.getBuiltinTemplates()
    builtinTemplates.value = templates
  } catch (error) {
    ElMessage.error('加载内置模板失败')
    console.error('Failed to load builtin templates:', error)
  } finally {
    loading.value = false
  }
}

// 内置模板数据（如果API不可用时的备用数据）
const defaultBuiltinTemplates = [
  {
    id: 'builtin-email-system-1',
    name: '系统告警邮件模板',
    template_type: 'email',
    category: 'system',
    description: '适用于系统级别告警的邮件通知模板',
    subject_template: '[{{severity|upper}}] {{title}} - {{host}}',
    content_template: `告警详情:
标题: {{title}}
级别: {{severity|upper}}
主机: {{host}}
描述: {{description}}
时间: {{created_at}}

请及时处理！`,
    is_builtin: true,
    enabled: true
  },
  {
    id: 'builtin-webhook-api-1',
    name: 'API告警Webhook模板',
    template_type: 'webhook',
    category: 'application',
    description: '适用于API服务告警的Webhook通知模板',
    subject_template: 'API Alert: {{title}}',
    content_template: `{
  "alert_type": "api_alert",
  "title": "{{title}}",
  "severity": "{{severity}}",
  "service": "{{service}}",
  "host": "{{host}}",
  "description": "{{description}}",
  "timestamp": "{{created_at}}",
  "environment": "{{environment}}"
}`,
    is_builtin: true,
    enabled: true
  },
  {
    id: 'builtin-feishu-business-1',
    name: '业务告警飞书模板',
    template_type: 'feishu',
    category: 'business',
    description: '适用于业务告警的飞书通知模板',
    subject_template: '【业务告警】{{title}}',
    content_template: `**告警级别**: {{severity|upper}}
**告警标题**: {{title}}
**告警描述**: {{description}}
**影响服务**: {{service}}
**告警主机**: {{host}}
**告警时间**: {{created_at}}

请相关同事及时关注处理！`,
    is_builtin: true,
    enabled: true
  },
  {
    id: 'builtin-email-infrastructure-1',
    name: '基础设施告警邮件模板',
    template_type: 'email',
    category: 'infrastructure',
    description: '适用于基础设施监控告警的邮件模板',
    subject_template: '[基础设施告警] {{title}} - {{host}}',
    content_template: `基础设施告警通知:

告警信息:
- 标题: {{title}}
- 级别: {{severity|upper}}
- 主机: {{host}}
- 服务: {{service}}
- 环境: {{environment}}

告警描述:
{{description}}

告警时间: {{created_at}}

请运维团队及时处理！`,
    is_builtin: true,
    enabled: true
  },
  {
    id: 'builtin-webhook-critical-1',
    name: '严重告警Webhook模板',
    template_type: 'webhook',
    category: 'system',
    description: '用于严重级别告警的Webhook通知模板',
    subject_template: 'CRITICAL ALERT: {{title}}',
    content_template: `{
  "alert_level": "critical",
  "alert_id": "{{alert_id}}",
  "title": "{{title}}",
  "description": "{{description}}",
  "severity": "{{severity}}",
  "source": "{{source}}",
  "host": "{{host}}",
  "service": "{{service}}",
  "environment": "{{environment}}",
  "created_at": "{{created_at}}",
  "tags": {{tags|tojson}},
  "require_immediate_action": true
}`,
    is_builtin: true,
    enabled: true
  },
  {
    id: 'builtin-feishu-custom-1',
    name: '自定义飞书卡片模板',
    template_type: 'feishu',
    category: 'custom',
    description: '支持富文本格式的飞书卡片告警模板',
    subject_template: '告警通知 - {{title}}',
    content_template: `📢 **告警通知**

🔴 **告警级别**: <font color="red">{{severity|upper}}</font>
📋 **告警标题**: {{title}}
📝 **告警描述**: {{description}}
🖥️ **告警主机**: {{host}}
⚙️ **相关服务**: {{service}}
🌍 **运行环境**: {{environment}}
⏰ **告警时间**: {{created_at}}

{% if tags %}
🏷️ **告警标签**: {% for tag in tags %}#{{tag}} {% endfor %}
{% endif %}

请相关负责人及时关注并处理！`,
    is_builtin: true,
    enabled: true
  }
]

// 如果API加载失败，使用默认模板
const loadDefaultTemplates = () => {
  builtinTemplates.value = defaultBuiltinTemplates
}
</script>

<style lang="scss" scoped>
.builtin-templates {
  .template-filter {
    display: flex;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }

  .template-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
    gap: 20px;
    max-height: 600px;
    overflow-y: auto;

    .template-card {
      border: 1px solid var(--el-border-color);
      border-radius: 8px;
      overflow: hidden;
      cursor: pointer;
      transition: all 0.3s ease;

      &:hover {
        border-color: var(--el-color-primary);
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      }

      &.selected {
        border-color: var(--el-color-primary);
        box-shadow: 0 0 0 2px var(--el-color-primary-light-8);
      }

      .card-header {
        padding: 15px;
        background: var(--el-bg-color-page);
        border-bottom: 1px solid var(--el-border-color-lighter);

        .template-name {
          font-size: 16px;
          font-weight: 600;
          color: var(--el-text-color-primary);
          margin-bottom: 8px;
        }

        .template-tags {
          display: flex;
          gap: 5px;
        }
      }

      .card-body {
        padding: 15px;

        .template-description {
          color: var(--el-text-color-regular);
          margin-bottom: 15px;
          line-height: 1.5;
        }

        .template-preview {
          .preview-section {
            margin-bottom: 10px;

            &:last-child {
              margin-bottom: 0;
            }

            .preview-label {
              font-size: 12px;
              font-weight: 500;
              color: var(--el-text-color-secondary);
              display: block;
              margin-bottom: 4px;
            }

            .preview-content {
              background: var(--el-fill-color-light);
              padding: 8px;
              border-radius: 4px;
              font-size: 12px;
              font-family: monospace;
              color: var(--el-text-color-regular);
              white-space: pre-wrap;
              word-break: break-all;
            }
          }
        }
      }

      .card-footer {
        padding: 15px;
        background: var(--el-bg-color-page);
        border-top: 1px solid var(--el-border-color-lighter);
        display: flex;
        justify-content: space-between;
      }
    }
  }

  .empty-state {
    text-align: center;
    padding: 40px;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style>