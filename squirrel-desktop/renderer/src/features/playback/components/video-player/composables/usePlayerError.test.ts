import { describe, expect, it, vi } from 'vitest'

import { usePlayerError } from './usePlayerError'

const t = (key: string) => `translated:${key}`

describe('usePlayerError', () => {
  it('presents resolver and engine failures through the same error entry point', () => {
    const state = usePlayerError({ t })
    state.reportError('RESOLVE_FAILED', '无法获取播放地址')

    expect(state.errorState.value).toMatchObject({
      show: true,
      code: 'RESOLVE_FAILED',
      title: 'translated:errorTitle',
      message: '无法获取播放地址',
      canRetry: true,
    })

    state.clearEngineError()
    expect(state.errorState.value.show).toBe(false)
  })

  it('clears an engine error on source replacement without affecting retry delivery', () => {
    const onRetry = vi.fn()
    const state = usePlayerError({ t, onRetry })

    state.reportError('NETWORK_TIMEOUT', 'raw error')
    expect(state.errorState.value.message).toBe('translated:errorNetwork')

    state.clearEngineError()
    expect(state.errorState.value.show).toBe(false)

    state.reportError('MEDIA_FAILED', 'raw error')
    state.handleRetry()
    expect(state.errorState.value.show).toBe(false)
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('keeps the provider login message and flags auth-required for YOUTUBE_LOGIN_REQUIRED', () => {
    const onAuthRequired = vi.fn()
    const state = usePlayerError({ t, onAuthRequired })

    state.reportError('YOUTUBE_LOGIN_REQUIRED', 'YouTube 要求登录后才能播放（机器人验证/登录门禁）。请在设置中完成 YouTube TV 授权后重试。')

    // 自定义登录提示不能被 authorization 分类的通用文案吞掉。
    expect(state.errorState.value).toMatchObject({
      show: true,
      code: 'YOUTUBE_LOGIN_REQUIRED',
      message: 'YouTube 要求登录后才能播放（机器人验证/登录门禁）。请在设置中完成 YouTube TV 授权后重试。',
      requiresAuth: true,
    })

    state.handleAuthRequired()
    expect(state.errorState.value.show).toBe(false)
    expect(onAuthRequired).toHaveBeenCalledOnce()
  })

  it('treats a generic authorization failure as a stream problem, not a login prompt', () => {
    const state = usePlayerError({ t })

    state.reportError('HTTP_403', 'googlevideo rejected the range request')

    expect(state.errorState.value.requiresAuth).toBe(false)
    expect(state.errorState.value.message).toBe('translated:errorStreamUnavailable')
  })
})
