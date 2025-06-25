<template>
  <div class="feishu-config">
    <el-form-item label="飞书Webhook URL" required>
      <el-input
        v-model="config.webhook_url"
        placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx"
      />
      <div class="form-tip">
        在飞书群聊中添加机器人时获得的Webhook URL
      </div>
    </el-form-item>

    <el-form-item label="消息类型">
      <el-select v-model="config.msg_type" placeholder="选择消息类型">
        <el-option label="纯文本" value="text" />
        <el-option label="富文本" value="rich_text" />
        <el-option label="交互式卡片" value="interactive" />
      </el-select>
      <div class="form-tip">
        不同类型支持不同的格式和样式
      </div>
    </el-form-item>

    <el-form-item label="请求超时(秒)">
      <el-input-number
        v-model="config.timeout"
        :min="5"
        :max="300"
        placeholder="请求超时时间"
      />
    </el-form-item>

    <!-- 消息预览 -->
    <el-divider content-position="left">消息预览</el-divider>

    <el-form-item label="预览消息">
      <el-button type="success" @click="generatePreview">
        生成预览
      </el-button>
    </el-form-item>

    <el-form-item v-if="previewMessage" label="消息效果">
      <div class="message-preview">
        <div v-if="config.msg_type === 'text'" class="text-preview">
          <div class="preview-header">纯文本消息</div>
          <div class="preview-content">{{ previewMessage }}</div>
        </div>

        <div v-else-if="config.msg_type === 'rich_text'" class="rich-text-preview">
          <div class="preview-header">富文本消息</div>
          <div class="preview-content rich-content">
            <div class="severity-badge" :class="severityClass">【HIGH】</div>
            <div class="title">测试告警标题</div>
            <div class="content">这是一个测试告警的详细描述信息</div>
            <div class="timestamp">时间: {{ new Date().toLocaleString() }}</div>
          </div>
        </div>

        <div v-else-if="config.msg_type === 'interactive'" class="card-preview">
          <div class="preview-header">交互式卡片</div>
          <div class="card-content">
            <div class="card-header">
              <span class="card-title">告警通知</span>
            </div>
            <div class="card-body">
              <div class="card-field">
                <strong>【HIGH】测试告警标题</strong>
              </div>
              <div class="card-field">
                这是一个测试告警的详细描述信息
              </div>
              <div class="card-field text-muted">
                时间: {{ new Date().toLocaleString() }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-form-item>

    <!-- 飞书机器人设置说明 -->
    <el-divider content-position="left">设置说明</el-divider>

    <el-alert
      title="如何获取飞书Webhook URL"
      type="info"
      :closable="false"
    >
      <ol>
        <li>在飞书群聊中，点击右上角设置图标</li>
        <li>选择"群机器人" → "添加机器人"</li>
        <li>选择"自定义机器人"</li>
        <li>配置机器人名称和描述</li>
        <li>复制生成的Webhook URL</li>
        <li>将URL粘贴到上方输入框中</li>
      </ol>
    </el-alert>

    <el-alert
      title="安全设置"
      type="warning"
      style="margin-top: 10px"
      :closable="false"
    >
      建议在飞书机器人设置中启用IP白名单或关键词验证，提高安全性。
    </el-alert>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue'])

const previewMessage = ref('')

const config = reactive({
  webhook_url: '',
  msg_type: 'rich_text',
  timeout: 30,
  ...props.modelValue
})

const severityClass = computed(() => {
  return 'severity-high' // 示例中使用high级别
})

const generatePreview = () => {
  const testData = {
    title: "测试告警标题",
    description: "这是一个测试告警的详细描述信息",
    severity: "high",
    source: "test-system",
    host: "web-01.example.com",
    timestamp: new Date().toLocaleString()
  }

  if (config.msg_type === 'text') {
    previewMessage.value = `【${testData.severity.toUpperCase()}】${testData.title}\n\n${testData.description}\n\n主机: ${testData.host}\n时间: ${testData.timestamp}`
  } else {
    previewMessage.value = '请查看右侧预览效果'
  }
}

// 监听配置变化并传递给父组件
watch(config, (newConfig) => {
  emit('update:modelValue', { ...newConfig })
}, { deep: true })

// 监听父组件传入的值变化
watch(() => props.modelValue, (newValue) => {
  Object.assign(config, newValue)
}, { deep: true })
</script>

<style lang="scss" scoped>
.feishu-config {
  .form-tip {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 5px;
  }

  .message-preview {
    border: 1px solid var(--el-border-color);
    border-radius: 6px;
    padding: 15px;
    background-color: var(--el-bg-color-page);

    .preview-header {
      font-weight: 600;
      margin-bottom: 10px;
      color: var(--el-text-color-primary);
    }

    .text-preview {
      .preview-content {
        background: white;
        padding: 10px;
        border-radius: 4px;
        white-space: pre-line;
        font-family: monospace;
      }
    }

    .rich-text-preview {
      .preview-content {
        background: white;
        padding: 15px;
        border-radius: 4px;

        .severity-badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 4px;
          font-weight: bold;
          margin-right: 8px;

          &.severity-high {
            background-color: #f56c6c;
            color: white;
          }
        }

        .title {
          font-weight: bold;
          font-size: 16px;
          margin: 5px 0;
        }

        .content {
          margin: 10px 0;
          line-height: 1.5;
        }

        .timestamp {
          font-size: 12px;
          color: #999;
          margin-top: 10px;
        }
      }
    }

    .card-preview {
      .card-content {
        background: white;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);

        .card-header {
          background: #f56c6c;
          color: white;
          padding: 12px 15px;

          .card-title {
            font-weight: bold;
          }
        }

        .card-body {
          padding: 15px;

          .card-field {
            margin-bottom: 8px;

            &.text-muted {
              color: #999;
              font-size: 12px;
            }
          }
        }
      }
    }
  }

  :deep(.el-alert) {
    ol {
      margin: 10px 0;
      padding-left: 20px;
      
      li {
        margin-bottom: 5px;
      }
    }
  }
}
</style>