/**
 * 解决方案管理 API
 */
import request from './request'

// 解决方案管理
export function createSolution(data) {
  return request({
    url: '/solutions/',
    method: 'post',
    data
  })
}

export function getSolutionsByCategory(category, params = {}) {
  return request({
    url: `/solutions/categories/${category}`,
    method: 'get',
    params
  })
}

export function searchSolutions(params = {}) {
  return request({
    url: '/solutions/search',
    method: 'get',
    params
  })
}

export function getRecommendedSolutions(params = {}) {
  return request({
    url: '/solutions/recommendations',
    method: 'get',
    params
  })
}

export function getSolutionDetail(solutionId) {
  return request({
    url: `/solutions/${solutionId}`,
    method: 'get'
  })
}

export function applySolution(solutionId, data) {
  return request({
    url: `/solutions/${solutionId}/apply`,
    method: 'post',
    data
  })
}

export function approveSolution(solutionId) {
  return request({
    url: `/solutions/${solutionId}/approve`,
    method: 'post'
  })
}

// 统计和元数据
export function getSolutionStatistics(params = {}) {
  return request({
    url: '/solutions/statistics/overview',
    method: 'get',
    params
  })
}

export function getSolutionCategories() {
  return request({
    url: '/solutions/categories',
    method: 'get'
  })
}

export function getSolutionTags() {
  return request({
    url: '/solutions/tags',
    method: 'get'
  })
}