import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import * as alertTemplateApi from '@/api/alertTemplate'

export const useAlertTemplateStore = defineStore('alertTemplate', () => {
  const alertTemplates = ref([])
  const loading = ref(false)
  const selectedTemplate = ref(null)

  const templateTypes = [
    { value: 'email', label: '邮件模板' },
    { value: 'webhook', label: 'Webhook模板' },
    { value: 'feishu', label: '飞书模板' }
  ]

  const templateCategories = [
    { value: 'system', label: '系统告警' },
    { value: 'business', label: '业务告警' },
    { value: 'infrastructure', label: '基础设施' },
    { value: 'application', label: '应用服务' },
    { value: 'custom', label: '自定义' }
  ]

  const getTemplateTypeLabel = (type) => {
    const typeObj = templateTypes.find(t => t.value === type)
    return typeObj ? typeObj.label : type
  }

  const getCategoryLabel = (category) => {
    const categoryObj = templateCategories.find(c => c.value === category)
    return categoryObj ? categoryObj.label : category
  }

  const fetchAlertTemplates = async (params = {}) => {
    loading.value = true
    try {
      const response = await alertTemplateApi.getAlertTemplates(params)
      // Handle different response structures safely
      const data = response?.data || response
      alertTemplates.value = data?.items || data || []
      return {
        items: alertTemplates.value,
        total: data?.total || data?.count || alertTemplates.value.length
      }
    } catch (error) {
      console.error('Failed to fetch alert templates:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const createAlertTemplate = async (templateData) => {
    try {
      const response = await alertTemplateApi.createAlertTemplate(templateData)
      await fetchAlertTemplates()
      return response.data
    } catch (error) {
      console.error('Failed to create alert template:', error)
      throw error
    }
  }

  const updateAlertTemplate = async (id, templateData) => {
    try {
      const response = await alertTemplateApi.updateAlertTemplate(id, templateData)
      await fetchAlertTemplates()
      return response.data
    } catch (error) {
      console.error('Failed to update alert template:', error)
      throw error
    }
  }

  const deleteAlertTemplate = async (id) => {
    try {
      await alertTemplateApi.deleteAlertTemplate(id)
      await fetchAlertTemplates()
    } catch (error) {
      console.error('Failed to delete alert template:', error)
      throw error
    }
  }

  const getAlertTemplate = async (id) => {
    try {
      const response = await alertTemplateApi.getAlertTemplate(id)
      selectedTemplate.value = response.data
      return response.data
    } catch (error) {
      console.error('Failed to get alert template:', error)
      throw error
    }
  }

  const previewTemplate = async (templateData, sampleData = null) => {
    try {
      const response = await alertTemplateApi.previewTemplate({
        ...templateData,
        sample_data: sampleData
      })
      return response.data
    } catch (error) {
      console.error('Failed to preview template:', error)
      throw error
    }
  }

  const validateTemplate = async (templateData) => {
    try {
      const response = await alertTemplateApi.validateTemplate(templateData)
      return response.data
    } catch (error) {
      console.error('Failed to validate template:', error)
      throw error
    }
  }

  const getTemplateFields = async (templateType) => {
    try {
      const response = await alertTemplateApi.getTemplateFields(templateType)
      return response.data
    } catch (error) {
      console.error('Failed to get template fields:', error)
      throw error
    }
  }

  const getBuiltinTemplates = async () => {
    try {
      const response = await alertTemplateApi.getBuiltinTemplates()
      return response.data
    } catch (error) {
      console.error('Failed to get builtin templates:', error)
      throw error
    }
  }

  const getTemplateStats = async (id) => {
    try {
      const response = await alertTemplateApi.getTemplateStats(id)
      return response.data
    } catch (error) {
      console.error('Failed to get template stats:', error)
      throw error
    }
  }

  return {
    alertTemplates,
    loading,
    selectedTemplate,
    templateTypes,
    templateCategories,
    getTemplateTypeLabel,
    getCategoryLabel,
    fetchAlertTemplates,
    createAlertTemplate,
    updateAlertTemplate,
    deleteAlertTemplate,
    getAlertTemplate,
    previewTemplate,
    validateTemplate,
    getTemplateFields,
    getBuiltinTemplates,
    getTemplateStats
  }
})