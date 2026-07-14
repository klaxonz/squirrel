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
})
