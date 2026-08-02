// @vitest-environment jsdom
import { createPinia, setActivePinia } from 'pinia'
import { createApp, nextTick } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import GlobalSearchBar from './GlobalSearchBar.vue'
import { getSearchSuggestions } from '@/shared/api/search'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { findDesktopPlaybackProvider } from '@/features/video/composables/useVideoOperations'
import { useUIStore } from '@/shared/stores/ui'

vi.mock('@/shared/icons/AppIcon.vue', () => ({
  default: { template: '<span aria-hidden="true" />' },
}))

vi.mock('@/shared/components/AppSpinner.vue', () => ({
  default: { template: '<span class="test-spinner" />' },
}))

vi.mock('@/shared/api/search', () => ({
  getSearchSuggestions: vi.fn(),
}))

vi.mock('@/features/video/composables/videoPlaybackSeed', () => ({
  rememberVideoPlaybackSeed: vi.fn(),
}))

vi.mock('@/features/video/composables/useVideoOperations', () => ({
  findDesktopPlaybackProvider: vi.fn(() => undefined),
  resolveDesktopPlayback: vi.fn(),
  isDesktopPlaybackClient: vi.fn(() => false),
}))

const mountedApps: Array<ReturnType<typeof createApp>> = []
const mockedGetSearchSuggestions = vi.mocked(getSearchSuggestions)
const mockedFindDesktopPlaybackProvider = vi.mocked(findDesktopPlaybackProvider)
const mockedRememberVideoPlaybackSeed = vi.mocked(rememberVideoPlaybackSeed)
const storageValues = new Map<string, string>()
const testStorage: Storage = {
  get length() { return storageValues.size },
  clear: () => storageValues.clear(),
  getItem: (key) => storageValues.get(key) ?? null,
  key: (index) => Array.from(storageValues.keys())[index] ?? null,
  removeItem: (key) => { storageValues.delete(key) },
  setItem: (key, value) => { storageValues.set(key, String(value)) },
}
Object.defineProperty(window, 'localStorage', { configurable: true, value: testStorage })
Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: testStorage })

const flushPromises = () => new Promise<void>((resolve) => setTimeout(resolve, 0))

async function mountSearch(overrides: Record<string, unknown> = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'Home', component: { render: () => null } },
      { path: '/results', name: 'SearchResults', component: { render: () => null } },
      { path: '/video/:videoId', name: 'VideoPlay', component: { render: () => null } },
    ],
  })
  await router.push('/')
  await router.isReady()

  const pinia = createPinia()
  setActivePinia(pinia)
  const host = document.createElement('div')
  document.body.append(host)
  const props = {
    searchScope: 'global-test',
    placeholder: '搜索内容',
    suggestionScope: 'all',
    suggestionsEnabled: true,
    ...overrides,
  }
  const app = createApp(GlobalSearchBar, props)
  mountedApps.push(app)
  app.use(pinia)
  app.use(router)
  app.mount(host)
  await nextTick()

  return {
    host,
    router,
    input: host.querySelector<HTMLInputElement>('[role="combobox"]')!,
  }
}

beforeEach(() => {
  localStorage.clear()
  mockedGetSearchSuggestions.mockReset()
  mockedGetSearchSuggestions.mockResolvedValue({ items: [], scope: 'all', query: null })
  mockedFindDesktopPlaybackProvider.mockReset()
  mockedFindDesktopPlaybackProvider.mockReturnValue(null)
  mockedRememberVideoPlaybackSeed.mockReset()
})

afterEach(() => {
  vi.useRealTimers()
  mountedApps.splice(0).forEach((app) => app.unmount())
  document.body.replaceChildren()
})

describe('GlobalSearchBar combobox', () => {
  it('connects the editable combobox to its listbox and exposes virtual option focus', async () => {
    localStorage.setItem('search-history:global-test', JSON.stringify(['first query', 'second query']))
    const { host, input } = await mountSearch()

    input.focus()
    await nextTick()

    const listbox = host.querySelector<HTMLElement>('[role="listbox"]')!
    const options = Array.from(host.querySelectorAll<HTMLElement>('[role="option"]'))
    expect(input.id).toMatch(/^global-search-\d+-input$/)
    expect(listbox.id).toMatch(/^global-search-\d+-listbox$/)
    expect(input.getAttribute('aria-controls')).toBe(listbox.id)
    expect(input.getAttribute('aria-expanded')).toBe('true')
    expect(input.getAttribute('aria-autocomplete')).toBe('list')
    expect(options).toHaveLength(2)
    expect(options.every((option) => option.getAttribute('aria-selected') === 'false')).toBe(true)

    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }))
    await nextTick()
    expect(document.activeElement).toBe(input)
    expect(input.getAttribute('aria-activedescendant')).toBe(options[0].id)
    expect(options[0].getAttribute('aria-selected')).toBe('true')

    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true }))
    await nextTick()
    expect(input.getAttribute('aria-activedescendant')).toBe(options[1].id)

    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await nextTick()
    expect(document.activeElement).toBe(input)
    expect(input.getAttribute('aria-expanded')).toBe('false')
    expect(input.hasAttribute('aria-activedescendant')).toBe(false)
  })

  it('labels history removal controls and keeps focus on the combobox when removing an item', async () => {
    localStorage.setItem('search-history:global-test', JSON.stringify(['saved search']))
    const { host, input } = await mountSearch()
    input.focus()
    await nextTick()

    const remove = host.querySelector<HTMLButtonElement>('[aria-label="从最近搜索中移除 saved search"]')!
    expect(remove.title).toBe('从最近搜索中移除 saved search')
    remove.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }))
    remove.click()
    await nextTick()

    expect(document.activeElement).toBe(input)
    expect(host.querySelectorAll('[role="option"]')).toHaveLength(0)
    expect(JSON.parse(localStorage.getItem('search-history:global-test') || '[]')).toEqual([])
  })

  it('waits for IME composition, reports async loading, and renders returned options', async () => {
    vi.useFakeTimers()
    let resolveSuggestions!: (value: Awaited<ReturnType<typeof getSearchSuggestions>>) => void
    mockedGetSearchSuggestions.mockReturnValue(new Promise((resolve) => {
      resolveSuggestions = resolve
    }))
    const { host, input } = await mountSearch()
    input.focus()
    input.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true }))
    input.value = '测试'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    await vi.advanceTimersByTimeAsync(500)
    expect(mockedGetSearchSuggestions).not.toHaveBeenCalled()

    input.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true }))
    await vi.advanceTimersByTimeAsync(300)
    await nextTick()
    expect(mockedGetSearchSuggestions).toHaveBeenCalledWith({ query: '测试', scope: 'all' })
    expect(input.getAttribute('aria-busy')).toBe('true')
    expect(host.querySelector('[role="listbox"]')?.getAttribute('aria-busy')).toBe('true')
    expect(host.querySelector('[role="status"]')?.textContent).toContain('正在加载搜索建议')

    resolveSuggestions({
      items: [{ type: 'query', value: '测试结果', label: '测试结果', meta: '远程' }],
      scope: 'all',
      query: '测试',
    })
    await Promise.resolve()
    await nextTick()
    expect(input.hasAttribute('aria-busy')).toBe(false)
    expect(host.querySelector('[role="option"]')?.textContent).toContain('测试结果')
  })

  it('selects suggestions with Enter and preserves redirect query and mode behavior', async () => {
    localStorage.setItem('search-history:global-test', JSON.stringify(['selected query']))
    const { router, input } = await mountSearch({
      activeSearchMode: 'remote',
      searchRedirectName: 'SearchResults',
    })
    input.focus()
    await nextTick()
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }))
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('SearchResults')
    expect(router.currentRoute.value.query).toEqual({ q: 'selected query', mode: 'remote' })
    expect(useUIStore().getSearchQuery('global-test')).toBe('selected query')
  })

  it('preserves direct URL playback routing and seed creation', async () => {
    mockedFindDesktopPlaybackProvider.mockReturnValue({ site: 'youtube' } as ReturnType<typeof findDesktopPlaybackProvider>)
    const { router, input } = await mountSearch()
    input.focus()
    input.value = 'https://example.test/watch/42'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('VideoPlay')
    expect(mockedRememberVideoPlaybackSeed).toHaveBeenCalledWith(expect.objectContaining({
      url: 'https://example.test/watch/42',
      site: 'youtube',
      source: 'remote',
    }))
  })

  it('cycles search mode and focuses from Ctrl/Cmd+K', async () => {
    const onSearchModeChange = vi.fn()
    const { host, input } = await mountSearch({
      searchModes: [{ value: 'local', label: '本地' }, { value: 'remote', label: '远程' }],
      activeSearchMode: 'local',
      onSearchModeChange,
    })

    host.querySelector<HTMLButtonElement>('[aria-label="搜索范围：本地"]')?.click()
    await nextTick()
    expect(onSearchModeChange).toHaveBeenCalledWith('remote')
    expect(document.activeElement).toBe(input)

    input.blur()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true }))
    expect(document.activeElement).toBe(input)

    input.blur()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true, bubbles: true }))
    expect(document.activeElement).toBe(input)
  })
})
