import request from '@/utils/request'

/**
 * 获取仪表板数据
 */
export function getDashboard() {
  return request({
    url: '/api/metrics/dashboard',
    method: 'get'
  })
}

/**
 * 获取原始指标数据（调试用）
 */
export function getRawMetrics() {
  return request({
    url: '/api/metrics/raw',
    method: 'get'
  })
}

/**
 * 触发指标收集
 */
export function collectMetrics() {
  return request({
    url: '/api/metrics/collect',
    method: 'post'
  })
}

/**
 * 清理过期指标
 */
export function cleanupMetrics(days = 30) {
  return request({
    url: '/api/metrics/cleanup',
    method: 'delete',
    params: { days }
  })
}
