<template>
  <div class="webhook-config">
    <el-form-item label="Webhook URL" required>
      <el-input
        v-model="config.url"
        placeholder="https://your-webhook-endpoint.com/alerts"
      />
      <div class="form-tip">
        接收告警通知的HTTP端点URL
      </div>
    </el-form-item>

    <el-form-item label="HTTP方法">
      <el-select v-model="config.method" placeholder="选择HTTP方法">
        <el-option label="POST" value="POST" />
        <el-option label="PUT" value="PUT" />
        <el-option label="PATCH" value="PATCH" />
        <el-option label="GET" value="GET" />
      </el-select>
    </el-form-item>

    <el-form-item label="请求头">
      <div class="headers-config">
        <div
          v-for="(header, index) in headersList"
          :key="index"
          class="header-item"
        >
          <el-input
            v-model="header.key"
            placeholder="Header名称"
            style="width: 40%"
          />
          <el-input
            v-model="header.value"
            placeholder="Header值"
            style="width: 50%; margin-left: 10px"
          />
          <el-button
            type="danger"
            size="small"
            @click="removeHeader(index)"
            style="margin-left: 10px"
          >
            删除
          </el-button>
        </div>
        <el-button type="primary" size="small" @click="addHeader">
          添加请求头
        </el-button>
      </div>
      <div class="form-tip">
        添加自定义HTTP请求头，如认证信息等
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

    <!-- 载荷配置 -->
    <el-divider content-position="left">载荷配置</el-divider>

    <el-form-item label="载荷格式">
      <el-radio-group v-model="payloadFormat">
        <el-radio label="default">默认JSON格式</el-radio>
        <el-radio label="custom">自定义JSON模板</el-radio>
      </el-radio-group>
    </el-form-item>

    <el-form-item v-if="payloadFormat === 'custom'" label="自定义载荷模板">
      <el-input
        v-model="config.payload_template"
        type="textarea"
        :rows="8"
        placeholder="请输入JSON模板，支持变量替换如 {{title}}, {{severity}} 等"
      />
      <div class="form-tip">
        支持的变量: title, description, severity, source, host, service, environment, created_at 等
      </div>
    </el-form-item>

    <el-form-item label="额外字段">
      <div class="extra-fields-config">
        <div
          v-for="(field, index) in extraFieldsList"
          :key="index"
          class="field-item"
        >
          <el-input
            v-model="field.key"
            placeholder="字段名"
            style="width: 40%"
          />
          <el-input
            v-model="field.value"
            placeholder="字段值"
            style="width: 50%; margin-left: 10px"
          />
          <el-button
            type="danger"
            size="small"
            @click="removeExtraField(index)"
            style="margin-left: 10px"
          >
            删除
          </el-button>
        </div>
        <el-button type="primary" size="small" @click="addExtraField">
          添加字段
        </el-button>
      </div>
      <div class="form-tip">
        添加到载荷中的额外字段
      </div>
    </el-form-item>

    <!-- 测试区域 -->
    <el-divider content-position="left">测试</el-divider>
    
    <el-form-item label="测试载荷">
      <el-button type="success" @click="generateTestPayload">
        生成测试载荷
      </el-button>
    </el-form-item>

    <el-form-item v-if="testPayload" label="生成的载荷">
      <el-input
        v-model="testPayload"
        type="textarea"
        :rows="6"
        readonly
      />
    </el-form-item>
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

const payloadFormat = ref('default')
const testPayload = ref('')

const config = reactive({
  url: '',
  method: 'POST',
  headers: {},
  timeout: 30,
  payload_template: null,
  extra_fields: {},
  ...props.modelValue
})

// 将headers对象转换为数组形式便于编辑
const headersList = ref([])
const extraFieldsList = ref([])

// 初始化headers和extra_fields列表
const initLists = () => {
  headersList.value = Object.entries(config.headers || {}).map(([key, value]) => ({
    key, value
  }))
  
  extraFieldsList.value = Object.entries(config.extra_fields || {}).map(([key, value]) => ({
    key, value
  }))
}

const addHeader = () => {
  headersList.value.push({ key: '', value: '' })
}

const removeHeader = (index) => {
  headersList.value.splice(index, 1)
  updateHeaders()
}

const addExtraField = () => {
  extraFieldsList.value.push({ key: '', value: '' })
}

const removeExtraField = (index) => {
  extraFieldsList.value.splice(index, 1)
  updateExtraFields()
}

const updateHeaders = () => {
  config.headers = {}
  headersList.value.forEach(header => {
    if (header.key && header.value) {
      config.headers[header.key] = header.value
    }
  })
}

const updateExtraFields = () => {
  config.extra_fields = {}
  extraFieldsList.value.forEach(field => {
    if (field.key && field.value) {
      config.extra_fields[field.key] = field.value
    }
  })
}

const generateTestPayload = () => {
  const testData = {
    title: "测试告警",
    description: "这是一个测试告警消息",
    severity: "high",
    source: "test-system",
    host: "web-01.example.com",
    service: "nginx",
    environment: "production",
    created_at: new Date().toISOString(),
    is_test: true
  }

  let payload = { ...testData }

  // 添加额外字段
  if (config.extra_fields) {
    payload = { ...payload, ...config.extra_fields }
  }

  // 如果有自定义模板，应用模板
  if (payloadFormat.value === 'custom' && config.payload_template) {
    try {
      // 简单的模板替换
      let template = config.payload_template
      Object.keys(testData).forEach(key => {
        const regex = new RegExp(`{{\\s*${key}\\s*}}`, 'g')
        template = template.replace(regex, testData[key])
      })
      payload = JSON.parse(template)
    } catch (error) {
      testPayload.value = 'JSON模板格式错误: ' + error.message
      return
    }
  }

  testPayload.value = JSON.stringify(payload, null, 2)
}

// 监听headers列表变化
watch(headersList, updateHeaders, { deep: true })

// 监听extra fields列表变化
watch(extraFieldsList, updateExtraFields, { deep: true })

// 监听payloadFormat变化
watch(payloadFormat, (newFormat) => {
  if (newFormat === 'default') {
    config.payload_template = null
  } else if (newFormat === 'custom' && !config.payload_template) {
    config.payload_template = JSON.stringify({
      title: "{{title}}",
      description: "{{description}}",
      severity: "{{severity}}",
      source: "{{source}}",
      host: "{{host}}",
      timestamp: "{{created_at}}"
    }, null, 2)
  }
})

// 监听配置变化并传递给父组件
watch(config, (newConfig) => {
  emit('update:modelValue', { ...newConfig })
}, { deep: true })

// 监听父组件传入的值变化
watch(() => props.modelValue, (newValue) => {
  Object.assign(config, newValue)
  initLists()
}, { deep: true, immediate: true })
</script>

<style lang="scss" scoped>
.webhook-config {
  .form-tip {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 5px;
  }

  .headers-config,
  .extra-fields-config {
    .header-item,
    .field-item {
      display: flex;
      align-items: center;
      margin-bottom: 10px;
    }
  }
}
</style>