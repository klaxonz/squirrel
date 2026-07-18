import { describe, expect, it } from 'vitest'
import { getAppRoutePath, isAuthShellRoute } from './auth'

describe('auth hash-route helpers', () => {
  it('reads SPA path from hash history locations', () => {
    expect(getAppRoutePath({ hash: '#/login', pathname: '/' })).toBe('/login')
    expect(getAppRoutePath({ hash: '#/home', pathname: '/' })).toBe('/home')
    expect(getAppRoutePath({ hash: '#/settings/appearance?x=1', pathname: '/' })).toBe('/settings/appearance')
    expect(getAppRoutePath({ hash: '', pathname: '/login' })).toBe('/login')
  })

  it('recognizes auth shell routes that must not hard-redirect', () => {
    expect(isAuthShellRoute('/login')).toBe(true)
    expect(isAuthShellRoute('/register')).toBe(true)
    expect(isAuthShellRoute('/server-config')).toBe(true)
    expect(isAuthShellRoute('/home')).toBe(false)
  })
})
