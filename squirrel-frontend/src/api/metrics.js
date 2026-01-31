import { del, get, post } from '@/utils/request'

/**
 * 获取仪表板数据
 */
export function getDashboard() {
  return get('/api/metrics/dashboard')
}

/**
 * 获取原始指标数据（调试用）
 */
export function getRawMetrics() {
  return get('/api/metrics/raw')
}

/**
 * 触发指标收集
 */
export function collectMetrics() {
  return post('/api/metrics/collect', null)
}

/**
 * 清理过期指标
 */
export function cleanupMetrics(days = 30) {
  return del('/api/metrics/cleanup', null, { params: { days } })
}
