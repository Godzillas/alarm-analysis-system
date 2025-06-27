/**
 * 接入点管理 API
 */
import request from './request'

/**
 * 获取接入点列表
 * @param {Object} params - 查询参数
 * @returns {Promise}
 */
export function getEndpoints(params = {}) {
  return request({
    url: '/endpoints/',
    method: 'get',
    params
  })
}

/**
 * 获取接入点详情
 * @param {number} id - 接入点ID
 * @returns {Promise}
 */
export function getEndpoint(id) {
  return request({
    url: `/endpoints/${id}`,
    method: 'get'
  })
}

/**
 * 创建接入点
 * @param {Object} data - 接入点数据
 * @returns {Promise}
 */
export function createEndpoint(data) {
  return request({
    url: '/endpoints/',
    method: 'post',
    data
  })
}

/**
 * 更新接入点
 * @param {number} id - 接入点ID
 * @param {Object} data - 更新数据
 * @returns {Promise}
 */
export function updateEndpoint(id, data) {
  return request({
    url: `/endpoints/${id}`,
    method: 'put',
    data
  })
}

/**
 * 删除接入点
 * @param {number} id - 接入点ID
 * @returns {Promise}
 */
export function deleteEndpoint(id) {
  return request({
    url: `/endpoints/${id}`,
    method: 'delete'
  })
}

/**
 * 测试接入点
 * @param {number} id - 接入点ID
 * @returns {Promise}
 */
export function testEndpoint(id) {
  return request({
    url: `/endpoints/${id}/test`,
    method: 'post'
  })
}

/**
 * 获取接入点统计信息
 * @param {number} id - 接入点ID
 * @param {Object} params - 查询参数
 * @returns {Promise}
 */
export function getEndpointStats(id, params = {}) {
  return request({
    url: `/endpoints/${id}/stats`,
    method: 'get',
    params
  })
}

// 注意: 以下功能需要后端实现对应的API端点

/**
 * 重新生成API Token (需要后端实现)
 * @param {number} id - 接入点ID
 * @returns {Promise}
 */
export function regenerateToken(id) {
  // TODO: 后端需要实现此API
  return request({
    url: `/endpoints/${id}/regenerate-token`,
    method: 'post'
  })
}

/**
 * 获取字段映射配置 (需要后端实现)
 * @param {number} id - 接入点ID
 * @returns {Promise}
 */
export function getFieldMapping(id) {
  // TODO: 后端需要实现此API
  return request({
    url: `/endpoints/${id}/field-mapping`,
    method: 'get'
  })
}

/**
 * 更新字段映射配置 (需要后端实现)
 * @param {number} id - 接入点ID
 * @param {Object} mapping - 映射配置
 * @returns {Promise}
 */
export function updateFieldMapping(id, mapping) {
  // TODO: 后端需要实现此API
  return request({
    url: `/endpoints/${id}/field-mapping`,
    method: 'put',
    data: mapping
  })
}

/**
 * 测试字段映射 (需要后端实现)
 * @param {number} id - 接入点ID
 * @param {Object} sampleData - 样本数据
 * @returns {Promise}
 */
export function testFieldMapping(id, sampleData) {
  // TODO: 后端需要实现此API
  return request({
    url: `/endpoints/${id}/test-mapping`,
    method: 'post',
    data: sampleData
  })
}

/**
 * 获取接入点日志 (需要后端实现)
 * @param {number} id - 接入点ID
 * @param {Object} params - 查询参数
 * @returns {Promise}
 */
export function getEndpointLogs(id, params = {}) {
  // TODO: 后端需要实现此API
  return request({
    url: `/endpoints/${id}/logs`,
    method: 'get',
    params
  })
}

/**
 * 获取接入点健康状态 (需要后端实现)
 * @param {number} id - 接入点ID
 * @returns {Promise}
 */
export function getEndpointHealth(id) {
  // TODO: 后端需要实现此API
  return request({
    url: `/endpoints/${id}/health`,
    method: 'get'
  })
}

/**
 * 批量测试接入点 (需要后端实现)
 * @param {Array} ids - 接入点ID数组
 * @returns {Promise}
 */
export function batchTestEndpoints(ids) {
  // TODO: 后端需要实现此API
  return request({
    url: '/endpoints/batch-test',
    method: 'post',
    data: { ids }
  })
}

/**
 * 批量导入接入点 (需要后端实现)
 * @param {Array} endpoints - 接入点配置数组
 * @returns {Promise}
 */
export function batchImportEndpoints(endpoints) {
  // TODO: 后端需要实现此API
  return request({
    url: '/endpoints/batch-import',
    method: 'post',
    data: { endpoints }
  })
}

/**
 * 导出接入点配置 (需要后端实现)
 * @param {Array} ids - 接入点ID数组
 * @returns {Promise}
 */
export function exportEndpoints(ids = []) {
  // TODO: 后端需要实现此API
  return request({
    url: '/endpoints/export',
    method: 'post',
    data: { ids },
    responseType: 'blob'
  })
}

// 映射配置相关API (需要后端实现)

/**
 * 获取映射配置文件列表 (需要后端实现)
 * @returns {Promise}
 */
export function getMappingProfiles() {
  // TODO: 后端需要实现此API
  return request({
    url: '/mapping/profiles/',
    method: 'get'
  })
}

/**
 * 获取指定映射配置文件 (需要后端实现)
 * @param {string} profileName - 配置文件名称
 * @returns {Promise}
 */
export function getMappingProfile(profileName) {
  // TODO: 后端需要实现此API
  return request({
    url: `/mapping/profiles/${profileName}`,
    method: 'get'
  })
}

/**
 * 创建映射配置文件 (需要后端实现)
 * @param {Object} profileData - 配置文件数据
 * @returns {Promise}
 */
export function createMappingProfile(profileData) {
  // TODO: 后端需要实现此API
  return request({
    url: '/mapping/profiles/',
    method: 'post',
    data: profileData
  })
}

/**
 * 测试映射配置文件 (需要后端实现)
 * @param {string} profileName - 配置文件名称
 * @param {Object} sampleData - 样本数据
 * @returns {Promise}
 */
export function testMappingProfile(profileName, sampleData) {
  // TODO: 后端需要实现此API
  return request({
    url: `/mapping/test/${profileName}`,
    method: 'post',
    data: sampleData
  })
}

/**
 * 发送测试告警 (需要后端实现)
 * @param {number} id - 接入点ID
 * @param {Object} testData - 测试数据
 * @returns {Promise}
 */
export function sendTestAlarm(id, testData) {
  // TODO: 后端需要实现此API
  return request({
    url: `/endpoints/${id}/send-test`,
    method: 'post',
    data: testData
  })
}