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
})
