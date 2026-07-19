// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick, ref } from 'vue'
import { createPinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import useVideoPlaybackShell from './useVideoPlaybackShell'
import { __resetPlaybackSessionForTests, usePlaybackSession } from './usePlaybackSession'
import type { PlaylistEntry } from '@/features/playback/types/playerSession'

vi.mock('@/shared/stores/ui', () => ({
  useUIStore: () => ({ setVideoWidescreen: vi.fn() }),
}))

describe('useVideoPlaybackShell queue projection', () => {
  let app: ReturnType<typeof createApp> | null = null

  beforeEach(() => {
    __resetPlaybackSessionForTests()
  })

  afterEach(() => {
    app?.unmount()
    app = null
    document.body.replaceChildren()
  })

  it('publishes navigation handlers and keeps session queue facts reactive', async () => {
    const playlistEntries = ref<PlaylistEntry[]>([
      { id: 'item-1', title: '第一条', source: null, videoId: 1 },
      { id: 'item-2', title: '第二条', source: null, videoId: 2 },
    ])
    const playlistIndex = ref(0)
    const hasPrev = ref(false)
    const hasNext = ref(true)
    const handlePlaylistSelect = vi.fn()
    const publishWiring = vi.fn()
    const loadAndPlayById = vi.fn().mockResolvedValue(undefined)

    const Harness = defineComponent({
      setup() {
        const shell = useVideoPlaybackShell({
          route: { params: { videoId: '1' } },
          effectiveTheme: ref('dark'),
          consumePlaybackSeed: () => null,
          loadAndPlayById,
          registerGlobalVideoPlayerTarget: vi.fn(),
          unregisterGlobalVideoPlayerTarget: vi.fn(),
          focusGlobalVideoPlayer: vi.fn().mockResolvedValue(undefined),
          publishWiring,
          flushPendingReport: vi.fn().mockResolvedValue(undefined),
          onVideoPlay: vi.fn(),
          onVideoPause: vi.fn(),
          handleAutoplayNext: vi.fn(),
          handlePlaybackTimeUpdate: vi.fn(),
          handlePrevVideoFromPlaylist: vi.fn(),
          handleNextVideoFromPlaylist: vi.fn(),
          handlePlayerRetry: vi.fn(),
          handleClipMarkerSeek: vi.fn(),
          handleClipMarkersUpdated: vi.fn(),
          handlePlaylistSelect,
          hasPrev,
          hasNext,
          playlistEntries,
          playlistIndex,
        })
        return () => h('div', { ref: shell.videoPlayerHostRef })
      },
    })

    const host = document.createElement('div')
    document.body.append(host)
    app = createApp(Harness)
    app.use(createPinia())
    app.mount(host)
    await nextTick()

    const session = usePlaybackSession()
    expect(session.facts.hasPrev).toBe(false)
    expect(session.facts.hasNext).toBe(true)
    expect(session.facts.playlist.map((entry) => entry.title)).toEqual(['第一条', '第二条'])
    expect(session.facts.playlistIndex).toBe(0)

    const handlers = publishWiring.mock.calls[publishWiring.mock.calls.length - 1]?.[0]
    await handlers.onPlaylistSelect?.(1)
    expect(handlePlaylistSelect).toHaveBeenCalledWith(1)

    playlistEntries.value = [{ id: 'item-2', title: '第二条', source: null, videoId: 2 }]
    playlistIndex.value = 0
    hasPrev.value = true
    await nextTick()

    expect(session.facts.hasPrev).toBe(true)
    expect(session.facts.playlist).toHaveLength(1)
    expect(session.facts.playlist[0]?.videoId).toBe(2)
    expect(loadAndPlayById).toHaveBeenCalledWith('1', null)
  })
})
