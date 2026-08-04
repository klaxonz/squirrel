import { describe, expect, it } from 'vitest'
import { useSiteRuntimeStatus } from './useSiteRuntimeStatus'

describe('site runtime status tones', () => {
  const {
    getNetworkVariant,
    getLoginText,
    getLoginVariant,
    getCapabilityLabel,
    needsAttention,
    supportsLogin,
    isConnected,
  } = useSiteRuntimeStatus()

  it('uses the success tone for healthy states', () => {
    expect(getNetworkVariant({ siteAccessible: true })).toBe('success')
    expect(getLoginVariant({ siteLoginStatus: { logged_in: true } })).toBe('success')
    expect(getLoginVariant({ siteOAuthStatus: 'authenticated' })).toBe('success')
  })

  it('keeps unchecked and pending states muted', () => {
    expect(getNetworkVariant({})).toBe('muted')
    expect(getLoginVariant({ siteOAuthStatus: 'pending' })).toBe('muted')
    expect(getLoginVariant({ siteLoginStatus: { supported: false } })).toBe('muted')
  })

  it('reserves the critical tone for actual failures', () => {
    expect(getNetworkVariant({ siteAccessible: false })).toBe('critical')
    expect(getLoginVariant({ siteLoginStatus: { logged_in: false } })).toBe('critical')
  })

  it('maps feature names to user-facing labels', () => {
    expect(getCapabilityLabel('sync_subscription')).toBe('同步订阅')
    expect(getCapabilityLabel('unknown_capability')).toBe('unknown_capability')
  })

  it('derives login support from catalog flags and desktop bridge', () => {
    expect(supportsLogin({ siteSupportsLogin: true })).toBe(true)
    expect(supportsLogin({ siteDesktopLoginSupported: true })).toBe(true)
    expect(supportsLogin({ siteName: 'youtube' })).toBe(true)
    expect(supportsLogin({ siteName: 'bilibili' })).toBe(false)
  })

  it('tracks connection via oauth or login status', () => {
    expect(isConnected({ siteOAuthStatus: 'authenticated' })).toBe(true)
    expect(isConnected({ siteLoginStatus: { logged_in: true } })).toBe(true)
    expect(isConnected({ siteLoginStatus: { logged_in: false } })).toBe(false)
  })

  it('flags only enabled sources with a known failure', () => {
    expect(needsAttention({ enabled: false, siteAccessible: false })).toBe(false)
    expect(needsAttention({ enabled: true, siteAccessible: false })).toBe(true)
    expect(needsAttention({ enabled: true, siteAccessible: true, siteName: 'youtube' })).toBe(false)
    expect(needsAttention({
      enabled: true,
      siteAccessible: true,
      siteName: 'youtube',
      siteLoginStatus: { logged_in: false },
    })).toBe(true)
  })
})
