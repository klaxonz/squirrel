import { describe, expect, it } from 'vitest'
import { useSiteRuntimeStatus } from './useSiteRuntimeStatus'

describe('site runtime status tones', () => {
  const {
    getSiteRuntimeStatusVariant,
    getNetworkVariant,
    getLoginText,
    getLoginVariant,
  } = useSiteRuntimeStatus()

  it('uses the success tone for healthy states', () => {
    expect(getSiteRuntimeStatusVariant({
      enabled: true,
      active_runtime: { state: 'running' },
    })).toBe('success')
    expect(getNetworkVariant({ siteAccessible: true })).toBe('success')
    expect(getLoginVariant({ siteLoginStatus: { logged_in: true } })).toBe('success')
  })

  it('keeps unchecked and pending states muted', () => {
    expect(getSiteRuntimeStatusVariant({ enabled: false })).toBe('muted')
    expect(getNetworkVariant({})).toBe('muted')
    expect(getLoginVariant({ siteOAuthStatus: 'pending' })).toBe('muted')
  })

  it('reserves the critical tone for actual failures', () => {
    expect(getSiteRuntimeStatusVariant({
      enabled: true,
      active_runtime: { state: 'failed' },
    })).toBe('critical')
    expect(getNetworkVariant({ siteAccessible: false })).toBe('critical')
    expect(getLoginVariant({ siteLoginStatus: { logged_in: false } })).toBe('critical')
  })

  it('uses concise copy for desktop login states', () => {
    expect(getLoginText({
      siteLoginStatus: { source: 'desktop', logged_in: true },
    })).toBe('已登录')
    expect(getLoginText({
      siteLoginStatus: { source: 'desktop', logged_in: false },
    })).toBe('未登录')
  })
})
