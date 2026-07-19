import { nextTick, ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import { usePlayerError } from './usePlayerError'
import type { ExternalErrorState } from '@/features/playback/types/playerSession'

const t = (key: string) => `translated:${key}`

describe('usePlayerError', () => {
  it('presents session resolution errors and keeps them across source-sync engine cleanup', async () => {
    const externalError = ref<ExternalErrorState | null>({
      code: 'RESOLVE_FAILED',
      title: '播放失败',
      message: '无法获取播放地址',
      canRetry: true,
    })
    const state = usePlayerError({ t, externalError })

    expect(state.errorState.value).toMatchObject({
      show: true,
      code: 'RESOLVE_FAILED',
      title: '播放失败',
      message: '无法获取播放地址',
      canRetry: true,
    })

    state.clearEngineError()
    expect(state.errorState.value.show).toBe(true)

    externalError.value = null
    await nextTick()
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
