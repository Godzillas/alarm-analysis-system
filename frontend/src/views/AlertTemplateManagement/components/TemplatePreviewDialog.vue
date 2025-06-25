<template>
  <el-dialog
    v-model="visible"
    title="模板预览"
    width="900px"
    @opened="generatePreview"
  >
    <div v-loading="loading" class="template-preview">
      <!-- 模板信息 -->
      <div class="template-info">
        <el-row :gutter="20">
          <el-col :span="8">
            <div class="info-item">
              <span class="label">模板名称:</span>
              <span class="value">{{ template?.name }}</span>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="info-item">
              <span class="label">模板类型:</span>
              <el-tag :type="getTypeTagType(template?.template_type)">
                {{ getTypeLabel(template?.template_type) }}
              </el-tag>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="info-item">
              <span class="label">分类:</span>
              <el-tag type="info">{{ getCategoryLabel(template?.category) }}</el-tag>
            </div>
          </el-col>
        </el-row>
        <div class="info-item">
          <span class="label">描述:</span>
          <span class="value">{{ template?.description || '-' }}</span>
        </div>
      </div>

      <el-divider />

      <!-- 预览配置 -->
      <div class="preview-config">
        <h4>预览配置</h4>
        <el-row :gutter="20">
          <el-col :span="16">
            <el-form-item label="示例数据">
              <el-input
                v-model="sampleDataStr"
                type="textarea"
                :rows="8"
                placeholder="请输入JSON格式的示例数据..."
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <div class="sample-buttons">
              <el-button type="primary" @click="generatePreview">
                生成预览
              </el-button>
              <el-button @click="loadDefaultSampleData">
                默认示例
              </el-button>
              <el-button @click="loadCriticalSampleData">
                严重告警
              </el-button>
              <el-button @click="loadWarningSampleData">
                警告告警
              </el-button>
            </div>
          </el-col>
        </el-row>
      </div>

      <el-divider />

      <!-- 预览结果 -->
      <div v-if="previewResult" class="preview-result">
        <h4>预览结果</h4>
        
        <!-- 主题预览 -->
        <div class="subject-preview">
          <h5>主题</h5>
          <div class="subject-content">
            {{ previewResult.subject }}
          </div>
        </div>

        <!-- 内容预览 -->
        <div class="content-preview">
          <h5>内容</h5>
          <div class="content-wrapper">
            <!-- 根据模板类型显示不同的预览效果 -->
            <div v-if="template?.template_type === 'email'" class="email-preview">
              <div class="email-header">
                <div class="email-from">
                  <strong>发件人:</strong> 告警系统 &lt;noreply@alert-system.com&gt;
                </div>
                <div class="email-to">
                  <strong>收件人:</strong> admin@example.com
                </div>
                <div class="email-subject">
                  <strong>主题:</strong> {{ previewResult.subject }}
                </div>
              </div>
              <div class="email-body">
                <div v-html="formatEmailContent(previewResult.content)"></div>
              </div>
            </div>

            <div v-else-if="template?.template_type === 'webhook'" class="webhook-preview">
              <div class="webhook-header">
                <strong>HTTP请求载荷</strong>
              </div>
              <div class="webhook-payload">
                <pre>{{ formatWebhookPayload(previewResult) }}</pre>
              </div>
            </div>

            <div v-else-if="template?.template_type === 'feishu'" class="feishu-preview">
              <div class="feishu-card">
                <div class="card-header">
                  <span class="card-title">告警通知</span>
                </div>
                <div class="card-body">
                  <div class="card-subject">
                    <strong>{{ previewResult.subject }}</strong>
                  </div>
                  <div class="card-content" v-html="formatFeishuContent(previewResult.content)"></div>
                </div>
              </div>
            </div>

            <div v-else class="default-preview">
              <div class="preview-content" v-html="previewResult.content"></div>
            </div>
          </div>
        </div>

        <!-- 字段映射信息 -->
        <div v-if="template?.field_mapping && Object.keys(template.field_mapping).length > 0" class="field-mapping-info">
          <h5>字段映射</h5>
          <el-table :data="fieldMappingData" size="small">
            <el-table-column prop="source" label="源字段" />
            <el-table-column prop="target" label="目标字段" />
            <el-table-column prop="value" label="映射值" />
          </el-table>
        </div>
      </div>

      <!-- 错误信息 -->
      <div v-if="previewError" class="preview-error">
        <el-alert
          title="预览生成失败"
          type="error"
          :description="previewError"
          show-icon
          :closable="false"
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">关闭</el-button>
        <el-button type="primary" @click="exportPreview">
          导出预览
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
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
  }
})

const emit = defineEmits(['update:modelValue'])

const alertTemplateStore = useAlertTemplateStore()

const loading = ref(false)
const sampleDataStr = ref('')
const previewResult = ref(null)
const previewError = ref('')

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const fieldMappingData = computed(() => {
  if (!props.template?.field_mapping) return []
  
  return Object.entries(props.template.field_mapping).map(([source, target]) => ({
    source,
    target,
    value: getSampleValue(source)
  }))
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

const getSampleValue = (field) => {
  try {
    const sampleData = JSON.parse(sampleDataStr.value)
    return sampleData[field] || '-'
  } catch {
    return '-'
  }
}

const loadDefaultSampleData = () => {
  const sampleData = {
    title: "服务响应异常",
    description: "API服务响应时间超过阈值，当前响应时间: 5.2秒",
    severity: "warning",
    source: "api-monitor",
    host: "api-server-01.example.com",
    service: "user-api",
    environment: "production",
    created_at: new Date().toISOString(),
    tags: ["api", "performance", "timeout"],
    labels: {
      region: "us-east-1",
      cluster: "prod-api-cluster",
      version: "v1.2.3"
    }
  }
  sampleDataStr.value = JSON.stringify(sampleData, null, 2)
}

const loadCriticalSampleData = () => {
  const sampleData = {
    title: "数据库服务不可用",
    description: "主数据库连接池耗尽，所有数据库连接均不可用，影响核心业务功能",
    severity: "critical",
    source: "database-monitor",
    host: "db-primary-01.example.com",
    service: "postgresql",
    environment: "production",
    created_at: new Date().toISOString(),
    tags: ["database", "critical", "outage"],
    labels: {
      region: "us-west-2",
      cluster: "prod-db-cluster",
      replica: "primary"
    }
  }
  sampleDataStr.value = JSON.stringify(sampleData, null, 2)
}

const loadWarningSampleData = () => {
  const sampleData = {
    title: "磁盘空间不足",
    description: "服务器磁盘使用率已达到85%，建议及时清理或扩容",
    severity: "warning",
    source: "system-monitor",
    host: "web-server-03.example.com",
    service: "nginx",
    environment: "production",
    created_at: new Date().toISOString(),
    tags: ["disk", "storage", "capacity"],
    labels: {
      region: "ap-south-1",
      cluster: "web-cluster",
      disk: "/dev/sda1"
    }
  }
  sampleDataStr.value = JSON.stringify(sampleData, null, 2)
}

const generatePreview = async () => {
  if (!props.template) return
  
  if (!sampleDataStr.value.trim()) {
    loadDefaultSampleData()
  }

  loading.value = true
  previewError.value = ''
  
  try {
    const sampleData = JSON.parse(sampleDataStr.value)
    const result = await alertTemplateStore.previewTemplate(props.template, sampleData)
    previewResult.value = result
  } catch (error) {
    previewError.value = error.message || '预览生成失败'
    previewResult.value = null
  } finally {
    loading.value = false
  }
}

const formatEmailContent = (content) => {
  return content.replace(/\n/g, '<br>')
}

const formatWebhookPayload = (result) => {
  const payload = {
    subject: result.subject,
    content: result.content,
    timestamp: new Date().toISOString(),
    source: "alert-system"
  }
  return JSON.stringify(payload, null, 2)
}

const formatFeishuContent = (content) => {
  return content.replace(/\n/g, '<br>')
}

const exportPreview = () => {
  if (!previewResult.value) {
    ElMessage.warning('请先生成预览')
    return
  }

  const exportData = {
    template: props.template,
    preview: previewResult.value,
    sample_data: JSON.parse(sampleDataStr.value),
    generated_at: new Date().toISOString()
  }

  const dataStr = JSON.stringify(exportData, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${props.template.name}-preview.json`
  link.click()
  URL.revokeObjectURL(url)
}

// 监听模板变化
watch(() => props.template, () => {
  previewResult.value = null
  previewError.value = ''
  if (props.template && visible.value) {
    generatePreview()
  }
})
</script>

<style lang="scss" scoped>
.template-preview {
  .template-info {
    background-color: var(--el-bg-color-page);
    padding: 15px;
    border-radius: 6px;
    margin-bottom: 20px;

    .info-item {
      display: flex;
      align-items: center;
      margin-bottom: 10px;

      &:last-child {
        margin-bottom: 0;
      }

      .label {
        font-weight: 500;
        color: var(--el-text-color-regular);
        margin-right: 10px;
        min-width: 80px;
      }

      .value {
        color: var(--el-text-color-primary);
      }
    }
  }

  .preview-config {
    h4 {
      margin: 0 0 15px 0;
      color: var(--el-text-color-primary);
    }

    .sample-buttons {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
  }

  .preview-result {
    h4, h5 {
      margin: 0 0 15px 0;
      color: var(--el-text-color-primary);
    }

    .subject-preview {
      margin-bottom: 25px;

      .subject-content {
        background: var(--el-bg-color-page);
        padding: 12px;
        border-radius: 6px;
        font-weight: 500;
        font-size: 16px;
        border-left: 4px solid var(--el-color-primary);
      }
    }

    .content-preview {
      margin-bottom: 25px;

      .content-wrapper {
        border: 1px solid var(--el-border-color);
        border-radius: 6px;
        overflow: hidden;
      }

      .email-preview {
        .email-header {
          background: var(--el-bg-color-page);
          padding: 15px;
          border-bottom: 1px solid var(--el-border-color-lighter);

          div {
            margin-bottom: 5px;
            
            &:last-child {
              margin-bottom: 0;
            }
          }
        }

        .email-body {
          padding: 20px;
          background: white;
          line-height: 1.6;
        }
      }

      .webhook-preview {
        .webhook-header {
          background: var(--el-color-warning-light-9);
          color: var(--el-color-warning);
          padding: 12px 15px;
          font-weight: 500;
        }

        .webhook-payload {
          padding: 15px;
          background: var(--el-fill-color-light);

          pre {
            margin: 0;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            line-height: 1.4;
            color: var(--el-text-color-primary);
            white-space: pre-wrap;
          }
        }
      }

      .feishu-preview {
        padding: 15px;
        background: var(--el-bg-color-page);

        .feishu-card {
          background: white;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);

          .card-header {
            background: var(--el-color-info);
            color: white;
            padding: 12px 15px;

            .card-title {
              font-weight: 500;
            }
          }

          .card-body {
            padding: 15px;

            .card-subject {
              font-size: 16px;
              margin-bottom: 10px;
              color: var(--el-text-color-primary);
            }

            .card-content {
              line-height: 1.6;
              color: var(--el-text-color-regular);
            }
          }
        }
      }

      .default-preview {
        padding: 20px;
        
        .preview-content {
          white-space: pre-wrap;
          line-height: 1.6;
        }
      }
    }

    .field-mapping-info {
      h5 {
        margin-bottom: 10px;
      }
    }
  }

  .preview-error {
    margin-top: 20px;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>