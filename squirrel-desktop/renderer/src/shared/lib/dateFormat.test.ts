import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { formatCount, formatDate, formatDuration, formatDurationMs } from './dateFormat'

describe('formatDate', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-17T12:00:00'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns unknown for empty or invalid input', () => {
    expect(formatDate(null)).toBe('未知日期')
    expect(formatDate(undefined)).toBe('未知日期')
    expect(formatDate('not-a-date')).toBe('未知日期')
  })

  it('uses calendar relatives for same-month pure dates', () => {
    expect(formatDate('2026-07-17')).toBe('今天')
    expect(formatDate('2026-07-16')).toBe('昨天')
    expect(formatDate('2026-07-18')).toBe('明天')
    expect(formatDate('2026-07-20')).toBe('3天后')
  })

  it('keeps near-future relatives within 30 days', () => {
    expect(formatDate('2026-07-24')).toBe('7天后')
    expect(formatDate('2026-08-01')).toBe('2周后')
  })

  it('never renders far-future dates as N年后 (garbage RSS schedules)', () => {
    expect(formatDate('2198-01-01')).toBe('2198-01-01')
    expect(formatDate('2100-06-15')).toBe('2100-06-15')
    expect(formatDate('2026-12-01')).toBe('2026-12-01')
    expect(formatDate('2198-01-01')).not.toMatch(/年后/)
  })

  it('keeps past relatives and absolute-style year lag', () => {
    // noon anchor → pure-date midnight is ~N+0.5 calendar days of abs diff
    expect(formatDate('2026-07-14')).toBe('3天前')
    expect(formatDate('2026-07-10')).toBe('1周前')
    // ~30.5d lands in month bucket
    expect(formatDate('2026-06-17')).toBe('1个月前')
    expect(formatDate('2026-04-17')).toBe('3个月前')
    expect(formatDate('2024-07-17')).toBe('2年前')
  })

  it('formats recent datetimes relatively then falls back through date part', () => {
    expect(formatDate('2026-07-17T11:30:00')).toBe('30分钟前')
    expect(formatDate('2026-07-16T12:00:00')).toBe('昨天')
  })
})

describe('formatDuration / formatCount', () => {
  it('formats media durations', () => {
    expect(formatDuration(65)).toBe('01:05')
    expect(formatDuration(3661)).toBe('1:01:01')
    expect(formatDuration(null)).toBe('未知')
  })

  it('formats duration ms compactly', () => {
    expect(formatDurationMs(500)).toBe('500ms')
    expect(formatDurationMs(1500)).toBe('1.5秒')
  })

  it('formats counts in 万/亿', () => {
    expect(formatCount(9999)).toBe('9999')
    expect(formatCount(12_000)).toBe('1.2万')
    expect(formatCount(200_000_000)).toBe('2亿')
  })
})
