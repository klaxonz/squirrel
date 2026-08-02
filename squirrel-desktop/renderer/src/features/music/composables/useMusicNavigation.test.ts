// @vitest-environment jsdom
import { createApp, defineComponent, nextTick } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it } from 'vitest'

import {
  buildMusicViewQuery,
  getMusicDetailIdentity,
  parseMusicView,
  useMusicNavigation,
  type MusicView,
} from './useMusicNavigation'
import { reset as resetNavigationHistory } from '@/shared/lib/navigationHistory'

const mountedApps: Array<ReturnType<typeof createApp>> = []

afterEach(() => {
  mountedApps.splice(0).forEach(app => app.unmount())
  document.body.replaceChildren()
  resetNavigationHistory()
})

async function mountNavigation(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/music', name: 'Music', component: { render: () => null } }],
  })
  await router.push(path)
  await router.isReady()

  let navigation!: ReturnType<typeof useMusicNavigation>
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp(defineComponent({
    setup() {
      navigation = useMusicNavigation()
      return () => null
    },
  }))
  mountedApps.push(app)
  app.use(router)
  app.mount(host)
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
  return { navigation, router }
}

describe('music navigation query contract', () => {
  it('normalizes unsupported and array view values to home', async () => {
    expect(parseMusicView('not-a-view')).toBe('home')
    expect(parseMusicView(['ranks', 'home'])).toBe('home')

    const { navigation, router } = await mountNavigation('/music?view=not-a-view&id=stale')
    expect(navigation.activeView.value).toBe('home')
    expect(router.currentRoute.value.fullPath).toBe('/music')
  })

  it('generates stable detail identity queries', () => {
    expect(buildMusicViewQuery(
      'playlist-detail',
      { id: 'rank-1', kind: 'rank', rankCid: 'weekly' },
      'ranks',
    )).toEqual({
      view: 'playlist-detail',
      id: 'rank-1',
      kind: 'rank',
      rank_cid: 'weekly',
      from: 'ranks',
    })
    expect(getMusicDetailIdentity({
      id: 'rank-1',
      kind: 'rank',
      rank_cid: 'weekly',
    })).toEqual({ id: 'rank-1', kind: 'rank', rankCid: 'weekly' })
  })

  it.each<[MusicView, string]>([
    ['album-detail', '/music?view=new-albums'],
    ['artist-detail', '/music?view=search'],
    ['user-playlist-detail', '/music?view=profile'],
  ])('falls back to the contextual parent for direct %s links', async (view, expectedPath) => {
    const { navigation, router } = await mountNavigation(`/music?view=${view}&id=42`)

    expect(navigation.canGoBack.value).toBe(true)
    expect(navigation.goBack()).toBe(true)
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 0))

    expect(router.currentRoute.value.fullPath).toBe(expectedPath)
  })
})
