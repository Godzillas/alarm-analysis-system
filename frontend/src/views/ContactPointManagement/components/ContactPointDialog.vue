<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑联络点' : '创建联络点'"
    width="800px"
    :close-on-click-modal="false"
    @closed="resetForm"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="120px"
    >
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="联络点名称" prop="name">
            <el-input v-model="formData.name" placeholder="请输入联络点名称" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="联络点类型" prop="contact_type">
            <el-select 
              v-model="formData.contact_type" 
              placeholder="请选择联络点类型"
              @change="handleTypeChange"
            >
              <el-option
                v-for="type in contactPointTypes"
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
          <el-form-item label="所属系统">
            <el-select v-model="formData.system_id" placeholder="选择所属系统(可选)" clearable>
              <el-option
                v-for="system in availableSystems"
                :key="system.id"
                :label="system.name"
                :value="system.id"
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
          :rows="3"
          placeholder="请输入联络点描述(可选)"
        />
      </el-form-item>

      <!-- 配置区域 -->
      <el-divider content-position="left">联络点配置</el-divider>
      
      <!-- 邮件配置 -->
      <template v-if="formData.contact_type === 'email'">
        <EmailConfig v-model="formData.config" />
      </template>

      <!-- Webhook配置 -->
      <template v-else-if="formData.contact_type === 'webhook'">
        <WebhookConfig v-model="formData.config" />
      </template>

      <!-- 飞书配置 -->
      <template v-else-if="formData.contact_type === 'feishu'">
        <FeishuConfig v-model="formData.config" />
      </template>

      <!-- 其他类型的占位符 -->
      <template v-else-if="formData.contact_type">
        <el-alert
          title="配置功能开发中"
          :description="`${currentTypeLabel} 配置功能正在开发中，敬请期待！`"
          type="info"
          show-icon
          :closable="false"
        />
      </template>

      <!-- 高级设置 -->
      <el-divider content-position="left">高级设置</el-divider>
      
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="重试次数">
            <el-input-number
              v-model="formData.retry_count"
              :min="0"
              :max="10"
              placeholder="重试次数"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="重试间隔(秒)">
            <el-input-number
              v-model="formData.retry_interval"
              :min="30"
              :max="3600"
              placeholder="重试间隔"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="超时时间(秒)">
            <el-input-number
              v-model="formData.timeout"
              :min="5"
              :max="300"
              placeholder="超时时间"
            />
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '更新' : '创建' }}
        </el-button>
        <el-button v-if="!isEdit" type="success" :loading="submitting" @click="handleSubmitAndTest">
          创建并测试
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useContactPointStore } from '@/store/contactPoint'
import { useSystemStore } from '@/store/system'
import EmailConfig from './configs/EmailConfig.vue'
import WebhookConfig from './configs/WebhookConfig.vue'
import FeishuConfig from './configs/FeishuConfig.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  contactPoint: {
    type: Object,
    default: null
  },
  isEdit: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const contactPointStore = useContactPointStore()
const systemStore = useSystemStore()

const formRef = ref()
const submitting = ref(false)

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const contactPointTypes = computed(() => contactPointStore.contactPointTypes)
const availableSystems = computed(() => systemStore.systems.filter(s => s.enabled))

const currentTypeLabel = computed(() => {
  const type = contactPointTypes.value.find(t => t.value === formData.contact_type)
  return type ? type.label : ''
})

const formData = reactive({
  name: '',
  description: '',
  contact_type: '',
  config: {},
  system_id: null,
  enabled: true,
  retry_count: 3,
  retry_interval: 300,
  timeout: 30
})

const formRules = {
  name: [
    { required: true, message: '请输入联络点名称', trigger: 'blur' },
    { min: 2, max: 50, message: '名称长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  contact_type: [
    { required: true, message: '请选择联络点类型', trigger: 'change' }
  ]
}

const handleTypeChange = () => {
  // 重置配置
  formData.config = {}
}

const resetForm = () => {
  Object.assign(formData, {
    name: '',
    description: '',
    contact_type: '',
    config: {},
    system_id: null,
    enabled: true,
    retry_count: 3,
    retry_interval: 300,
    timeout: 30
  })
  
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

const validateConfig = () => {
  // 根据不同类型验证配置
  const { contact_type, config } = formData
  
  if (contact_type === 'email') {
    if (!config.smtp_server || !config.smtp_port || !config.username || !config.password || !config.to_addresses?.length) {
      throw new Error('邮件配置不完整')
    }
  } else if (contact_type === 'webhook') {
    if (!config.url) {
      throw new Error('Webhook URL 不能为空')
    }
  } else if (contact_type === 'feishu') {
    if (!config.webhook_url) {
      throw new Error('飞书 Webhook URL 不能为空')
    }
  }
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    validateConfig()
    
    submitting.value = true
    
    if (props.isEdit) {
      await contactPointStore.updateContactPoint(props.contactPoint.id, formData)
      ElMessage.success('联络点更新成功')
    } else {
      await contactPointStore.createContactPoint(formData)
      ElMessage.success('联络点创建成功')
    }
    
    emit('success')
  } catch (error) {
    if (error.message) {
      ElMessage.error(error.message)
    } else {
      ElMessage.error(props.isEdit ? '更新失败' : '创建失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleSubmitAndTest = async () => {
  try {
    await formRef.value.validate()
    validateConfig()
    
    submitting.value = true
    
    const result = await contactPointStore.createContactPoint(formData)
    ElMessage.success('联络点创建成功')
    
    // 测试联络点
    ElMessage.info('正在测试联络点...')
    const testResult = await contactPointStore.testContactPoint(result.id)
    
    if (testResult.success) {
      ElMessage.success('联络点测试成功')
    } else {
      ElMessage.warning(`联络点创建成功，但测试失败: ${testResult.error}`)
    }
    
    emit('success')
  } catch (error) {
    if (error.message) {
      ElMessage.error(error.message)
    } else {
      ElMessage.error('创建失败')
    }
  } finally {
    submitting.value = false
  }
}

// 监听联络点数据变化
watch(() => props.contactPoint, (newValue) => {
  if (newValue && props.isEdit) {
    Object.assign(formData, {
      name: newValue.name || '',
      description: newValue.description || '',
      contact_type: newValue.contact_type || '',
      config: { ...newValue.config } || {},
      system_id: newValue.system_id || null,
      enabled: newValue.enabled ?? true,
      retry_count: newValue.retry_count || 3,
      retry_interval: newValue.retry_interval || 300,
      timeout: newValue.timeout || 30
    })
  }
}, { immediate: true })
</script>

<style lang="scss" scoped>
.dialog-footer {
  text-align: right;
}

:deep(.el-divider__text) {
  font-weight: 600;
  color: var(--el-text-color-primary);
}
</style>