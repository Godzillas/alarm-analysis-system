<template>
  <div class="contact-info-editor">
    <el-form :model="contactInfo" label-width="80px" size="small">
      <el-form-item label="邮箱">
        <el-input 
          v-model="contactInfo.email" 
          placeholder="请输入邮箱地址"
          type="email"
        />
      </el-form-item>
      
      <el-form-item label="电话">
        <el-input 
          v-model="contactInfo.phone" 
          placeholder="请输入电话号码"
        />
      </el-form-item>
      
      <el-form-item label="微信">
        <el-input 
          v-model="contactInfo.wechat" 
          placeholder="请输入微信号"
        />
      </el-form-item>
      
      <el-form-item label="备注">
        <el-input 
          v-model="contactInfo.note" 
          placeholder="其他联系方式或备注"
          type="textarea"
          :rows="2"
        />
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue'])

// 初始化联系信息
const contactInfo = reactive({
  email: props.modelValue.email || '',
  phone: props.modelValue.phone || '',
  wechat: props.modelValue.wechat || '',
  note: props.modelValue.note || ''
})

// 监听变化并向上传递
watch(contactInfo, (newVal) => {
  emit('update:modelValue', { ...newVal })
}, { deep: true })

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  Object.assign(contactInfo, {
    email: newVal.email || '',
    phone: newVal.phone || '',
    wechat: newVal.wechat || '',
    note: newVal.note || ''
  })
}, { deep: true })
</script>

<style lang="scss" scoped>
.contact-info-editor {
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  padding: 16px;
  background-color: var(--el-bg-color-page);
}
</style>