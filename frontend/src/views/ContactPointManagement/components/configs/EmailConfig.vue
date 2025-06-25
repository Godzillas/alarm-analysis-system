<template>
  <div class="email-config">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-form-item label="SMTP服务器" required>
          <el-input v-model="config.smtp_server" placeholder="如: smtp.gmail.com" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item label="SMTP端口" required>
          <el-input-number
            v-model="config.smtp_port"
            :min="1"
            :max="65535"
            placeholder="如: 587"
            style="width: 100%"
          />
        </el-form-item>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="12">
        <el-form-item label="用户名" required>
          <el-input v-model="config.username" placeholder="SMTP用户名" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item label="密码" required>
          <el-input
            v-model="config.password"
            type="password"
            placeholder="SMTP密码"
            show-password
          />
        </el-form-item>
      </el-col>
    </el-row>

    <el-form-item label="发件人邮箱">
      <el-input
        v-model="config.from_address"
        placeholder="发件人邮箱(可选，默认使用用户名)"
      />
    </el-form-item>

    <el-form-item label="收件人邮箱" required>
      <el-select
        v-model="config.to_addresses"
        multiple
        filterable
        allow-create
        placeholder="请输入收件人邮箱地址"
        style="width: 100%"
      >
        <el-option
          v-for="email in commonEmails"
          :key="email"
          :label="email"
          :value="email"
        />
      </el-select>
      <div class="form-tip">
        可以输入多个邮箱地址，按回车键添加
      </div>
    </el-form-item>

    <el-form-item label="使用TLS">
      <el-switch v-model="config.use_tls" />
      <div class="form-tip">
        大多数SMTP服务器需要启用TLS加密
      </div>
    </el-form-item>

    <!-- 常用SMTP配置快速设置 -->
    <el-divider content-position="left">快速配置</el-divider>
    
    <el-form-item label="常用邮箱">
      <el-select
        v-model="selectedProvider"
        placeholder="选择常用邮箱提供商"
        @change="applyProviderConfig"
      >
        <el-option label="Gmail" value="gmail" />
        <el-option label="Outlook/Hotmail" value="outlook" />
        <el-option label="QQ邮箱" value="qq" />
        <el-option label="163邮箱" value="163" />
        <el-option label="126邮箱" value="126" />
        <el-option label="企业邮箱" value="enterprise" />
      </el-select>
      <div class="form-tip">
        选择后会自动填入对应的SMTP配置
      </div>
    </el-form-item>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue'])

const selectedProvider = ref('')
const commonEmails = ref([])

const config = reactive({
  smtp_server: '',
  smtp_port: 587,
  username: '',
  password: '',
  from_address: '',
  to_addresses: [],
  use_tls: true,
  ...props.modelValue
})

const providerConfigs = {
  gmail: {
    smtp_server: 'smtp.gmail.com',
    smtp_port: 587,
    use_tls: true
  },
  outlook: {
    smtp_server: 'smtp-mail.outlook.com',
    smtp_port: 587,
    use_tls: true
  },
  qq: {
    smtp_server: 'smtp.qq.com',
    smtp_port: 587,
    use_tls: true
  },
  163: {
    smtp_server: 'smtp.163.com',
    smtp_port: 994,
    use_tls: true
  },
  126: {
    smtp_server: 'smtp.126.com',
    smtp_port: 994,
    use_tls: true
  },
  enterprise: {
    smtp_server: 'mail.company.com',
    smtp_port: 587,
    use_tls: true
  }
}

const applyProviderConfig = (provider) => {
  if (providerConfigs[provider]) {
    Object.assign(config, providerConfigs[provider])
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
.email-config {
  .form-tip {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 5px;
  }
}
</style>