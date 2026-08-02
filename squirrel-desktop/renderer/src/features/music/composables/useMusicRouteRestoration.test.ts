import { nextTick, ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import { useMusicRouteRestoration, type MusicDetailRoute } from './useMusicRouteRestoration'

const flush = () => new Promise<void>(resolve => setTimeout(resolve, 0))

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}

describe('useMusicRouteRestoration', () => {
  it('restores a directly loaded detail identity', async () => {
    const route = ref<MusicDetailRoute | null>({
      view: 'album-detail',
      identity: { id: 'album-42' },
    })
    const restore = vi.fn().mockResolvedValue(true)
    const fallback = vi.fn()

    const state = useMusicRouteRestoration({ route, restore, fallback })
    expect(state.restoring.value).toBe(true)
    await flush()

    expect(restore).toHaveBeenCalledWith(route.value)
    expect(fallback).not.toHaveBeenCalled()
    expect(state.restoring.value).toBe(false)
  })

  it('falls back visibly when the current identity cannot be restored', async () => {
    const request: MusicDetailRoute = {
      view: 'playlist-detail',
      identity: { id: 'missing-playlist' },
    }
    const route = ref<MusicDetailRoute | null>(request)
    const fallback = vi.fn()

    const state = useMusicRouteRestoration({
      route,
      restore: vi.fn().mockResolvedValue(false),
      fallback,
    })
    await flush()

    expect(fallback).toHaveBeenCalledWith(request)
    expect(state.restoring.value).toBe(false)
  })

  it('ignores stale restoration results during back-forward changes', async () => {
    const first = deferred<boolean>()
    const second = deferred<boolean>()
    const route = ref<MusicDetailRoute | null>({
      view: 'artist-detail',
      identity: { id: 'artist-old' },
    })
    const restore = vi.fn()
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise)
    const fallback = vi.fn()
    const state = useMusicRouteRestoration({ route, restore, fallback })

    route.value = { view: 'album-detail', identity: { id: 'album-current' } }
    await nextTick()
    first.resolve(false)
    await flush()

    expect(restore).toHaveBeenCalledTimes(2)
    expect(fallback).not.toHaveBeenCalled()
    expect(state.restoring.value).toBe(true)

    second.resolve(true)
    await flush()
    expect(fallback).not.toHaveBeenCalled()
    expect(state.restoring.value).toBe(false)
  })
})
