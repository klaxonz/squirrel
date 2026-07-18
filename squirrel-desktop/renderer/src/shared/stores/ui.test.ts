import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUIStore } from './ui'

describe('ui search contexts', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    })
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('isolates queries and triggers by search scope', () => {
    const store = useUIStore()

    store.setSearchQuery('rss', 'security')
    store.setSearchQuery('history', 'conference')
    store.triggerSearch('rss')

    expect(store.getSearchQuery('rss')).toBe('security')
    expect(store.getSearchQuery('history')).toBe('conference')
    expect(store.getSearchTrigger('rss')).toBe(1)
    expect(store.getSearchTrigger('history')).toBe(0)
  })

  it('persists video canvas density', () => {
    const store = useUIStore()

    store.setVideoDensity('large')

    expect(store.videoDensity).toBe('large')
    expect(localStorage.setItem).toHaveBeenCalledWith('ui.videoDensity', 'large')
  })

  it('remembers view preferences per video collection', () => {
    const store = useUIStore()

    store.setViewMode('list', 'local:later')
    store.setVideoDensity('compact', 'local:later')
    store.setViewMode('grid')
    store.setVideoDensity('large')
    store.applyVideoViewPreference('local:later')

    expect(store.viewMode).toBe('list')
    expect(store.videoDensity).toBe('compact')
    expect(localStorage.setItem).toHaveBeenCalledWith(
      'ui.videoViewPreferences',
      expect.stringContaining('local:later'),
    )
  })
})
