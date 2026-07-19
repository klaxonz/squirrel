import { describe, expect, it } from 'vitest'
import {
  formatDateTime,
  formatTaskInterval,
  getTaskDisplayName,
} from './scheduledTaskPresenters'

describe('scheduled task presenters', () => {
  it('presents built-in implementation names as user-facing task names', () => {
    expect(getTaskDisplayName({
      name: 'SubscriptionIncrementalUpdateTask',
      task_class: 'SubscriptionIncrementalUpdateTask',
    })).toBe('订阅增量更新')
    expect(getTaskDisplayName({
      name: '每日清理',
      task_class: 'CleanupTask',
    })).toBe('每日清理')
    expect(getTaskDisplayName({
      name: 'CustomCacheWarmupTask',
      task_class: 'CustomCacheWarmupTask',
    })).toBe('Custom Cache Warmup')
  })

  it('normalizes intervals to the largest exact unit', () => {
    expect(formatTaskInterval(1440, 'minutes')).toBe('每天')
    expect(formatTaskInterval(120, 'minutes')).toBe('每 2 小时')
    expect(formatTaskInterval(30, 'minutes')).toBe('每 30 分钟')
    expect(formatTaskInterval(1, 'hours')).toBe('每小时')
  })

  it('returns null for empty and invalid datetimes', () => {
    expect(formatDateTime(null)).toBeNull()
    expect(formatDateTime('not-a-date')).toBeNull()
  })
})
