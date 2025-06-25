import request from './request'

// 获取告警模板列表
export const getAlertTemplates = (params) => {
  return request.get('/alert-templates', { params })
}

// 创建告警模板
export const createAlertTemplate = (data) => {
  return request.post('/alert-templates', data)
}

// 更新告警模板
export const updateAlertTemplate = (id, data) => {
  return request.put(`/alert-templates/${id}`, data)
}

// 删除告警模板
export const deleteAlertTemplate = (id) => {
  return request.delete(`/alert-templates/${id}`)
}

// 获取告警模板详情
export const getAlertTemplate = (id) => {
  return request.get(`/alert-templates/${id}`)
}

// 预览模板
export const previewTemplate = (data) => {
  return request.post('/alert-templates/preview', data)
}

// 验证模板
export const validateTemplate = (data) => {
  return request.post('/alert-templates/validate', data)
}

// 获取模板字段
export const getTemplateFields = (templateType) => {
  return request.get(`/alert-templates/fields/${templateType}`)
}

// 获取内置模板
export const getBuiltinTemplates = () => {
  return request.get('/alert-templates/builtin')
}

// 获取模板统计
export const getTemplateStats = (id) => {
  return request.get(`/alert-templates/${id}/stats`)
}

export default {
  getAlertTemplates,
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