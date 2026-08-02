// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes } from './index'

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
