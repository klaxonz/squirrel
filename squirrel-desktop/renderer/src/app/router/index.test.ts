// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes, shouldReplaceStackEntry } from './index'

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes,
  })
}

describe('application fallback route', () => {
  it('keeps known routes ahead of the wildcard', () => {
    const router = createTestRouter()

    expect(router.resolve('/music').name).toBe('Music')
    expect(router.resolve('/settings/appearance').name).toBe('SettingsAppearance')
  })

  it('resolves unknown paths to the authenticated main-app not-found route', () => {
    const route = createTestRouter().resolve('/missing/deep/link?from=test')

    expect(route.name).toBe('NotFound')
    expect(route.meta).toMatchObject({
      title: '页面未找到',
      showSearch: false,
      historyStrategy: 'push',
    })
    expect(route.meta.requiresAuth).not.toBe(false)
    expect(route.meta.layout).not.toBe('auth')
  })
})

describe('shouldReplaceStackEntry', () => {
  const ctx = {
    currentFullPath: '/video/1',
    toFullPath: '/video/2',
    toName: 'VideoPlay',
    fromName: 'VideoPlay',
    toStrategy: 'push',
    fromStrategy: 'push',
  }

  it('replaces when re-entering the exact same path (F5 / deep link)', () => {
    expect(shouldReplaceStackEntry({ ...ctx, toFullPath: '/video/1' })).toBe(true)
  })

  it('replaces for replace-strategy tab routes', () => {
    expect(shouldReplaceStackEntry({
      ...ctx,
      currentFullPath: '/videos/all',
      toFullPath: '/videos/unread',
      toName: 'UnreadVideos',
      fromName: 'AllVideos',
      toStrategy: 'replace',
      fromStrategy: 'replace',
    })).toBe(true)
  })

  it('replaces for same-name video switches (related / playlist / random / autoplay)', () => {
    expect(shouldReplaceStackEntry(ctx)).toBe(true)
  })

  it('pushes when entering the play page from the library', () => {
    expect(shouldReplaceStackEntry({
      ...ctx,
      currentFullPath: '/videos/all',
      toFullPath: '/video/1',
      toName: 'VideoPlay',
      fromName: 'AllVideos',
    })).toBe(false)
  })

  it('pushes for ordinary cross-page navigation', () => {
    expect(shouldReplaceStackEntry({
      ...ctx,
      currentFullPath: '/videos/all',
      toFullPath: '/history',
      toName: 'History',
      fromName: 'AllVideos',
    })).toBe(false)
  })
})
