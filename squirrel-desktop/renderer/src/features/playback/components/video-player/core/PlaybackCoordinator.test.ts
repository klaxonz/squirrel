import { describe, expect, it, vi } from 'vitest'
import { PlaybackCoordinator } from './PlaybackCoordinator'

describe('PlaybackCoordinator', () => {
  it('owns resolving, loading, seeking and playing as one generation', () => {
    const coordinator = new PlaybackCoordinator()
    const resolve = coordinator.beginResolving('video-1')
    expect(coordinator.getSnapshot()).toMatchObject({
      phase: 'resolving',
      loadingStage: 'resolving',
      generation: 1,
      operationId: resolve.operationId,
    })

    const load = coordinator.beginLoading('manifest-1')
    expect(load.generation).toBe(resolve.generation)
    coordinator.markReady()
    expect(coordinator.getSnapshot().phase).toBe('ready')

    coordinator.markPlaying()
    const seek = coordinator.beginSeek(120, true)
    expect(coordinator.getSnapshot()).toMatchObject({
      phase: 'seeking',
      currentTime: 120,
      intent: 'play',
    })
    coordinator.markReady(true)
    expect(coordinator.getSnapshot()).toMatchObject({ phase: 'playing', loading: false })
    expect(coordinator.isCurrent(seek)).toBe(true)
  })

  it('aborts stale operations when a newer source begins', () => {
    const coordinator = new PlaybackCoordinator()
    const first = coordinator.beginResolving('video-1')
    const second = coordinator.beginResolving('video-2')

    expect(first.signal.aborted).toBe(true)
    expect(coordinator.isCurrent(first)).toBe(false)
    expect(coordinator.isCurrent(second)).toBe(true)
    expect(second.generation).toBe(first.generation + 1)
  })

  it('ignores media events from the detached source while resolving', () => {
    const coordinator = new PlaybackCoordinator()
    coordinator.beginResolving('video-2')

    coordinator.updateMedia({ currentTime: 900, duration: 1200, bufferedPercent: 80 })
    coordinator.markBuffering()
    coordinator.markReady(true)
    coordinator.markPaused()

    expect(coordinator.getSnapshot()).toMatchObject({
      phase: 'resolving',
      intent: 'play',
      currentTime: 0,
      duration: 0,
      bufferedPercent: 0,
    })
  })

  it('waits for operation completion and rejects a superseded seek', async () => {
    vi.useFakeTimers()
    const coordinator = new PlaybackCoordinator()
    coordinator.beginResolving('video-1')
    coordinator.beginLoading('manifest-1')
    coordinator.markPlaying()
    const firstSeek = coordinator.beginSeek(50, true)
    const firstResult = coordinator.waitFor(firstSeek, state => state.phase === 'playing', 5000)

    coordinator.beginSeek(100, true)
    await expect(firstResult).rejects.toMatchObject({ name: 'AbortError' })
    vi.useRealTimers()
  })

  it('surfaces typed failure state without losing the active generation', () => {
    const coordinator = new PlaybackCoordinator()
    const operation = coordinator.beginResolving('video-1')
    coordinator.fail({ code: 'NETWORK_ERROR', message: 'offline', fatal: true })

    expect(coordinator.getSnapshot()).toMatchObject({
      phase: 'error',
      generation: operation.generation,
      loading: false,
      error: { code: 'NETWORK_ERROR' },
    })
  })
})
