import { nextTick, ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'
import { useMusicDetailRouteController } from './useMusicDetailRouteController'
import type { MusicAlbum, MusicArtist, MusicPlaylist, MusicRank, MusicUserPlaylist } from '@/shared/api/music'


vi.mock('./useMusicNavigation', () => ({
  isMusicDetailView: (view: string) => view.endsWith('-detail'),
  getMusicDetailIdentity: (query: Record<string, unknown>) => query.id ? { id: String(query.id) } : null,
}))

vi.mock('@/shared/api/music', () => ({
  getMusicAlbumDetail: vi.fn(),
  getMusicArtistDetail: vi.fn(),
  getMusicPlaylists: vi.fn(),
  getMusicRankDetail: vi.fn(),
  getMusicUserPlaylists: vi.fn(),
}))

const flush = async () => {
  await nextTick()
  await Promise.resolve()
}

function setup(view: 'playlist-detail' | 'album-detail', id: string) {
  const selectedPlaylist = ref<MusicPlaylist | null>(null)
  const selectedUserPlaylist = ref<MusicUserPlaylist | null>(null)
  const selectedArtist = ref<MusicArtist | null>(null)
  const selectedAlbum = ref<MusicAlbum | null>(null)
  const selectedRank = ref<MusicRank | null>(null)
  const homePlaylists = ref<MusicPlaylist[]>([{ id: 'playlist-1', name: 'Saved' }])
  const userPlaylists = ref<MusicUserPlaylist[]>([])
  const targetUserPlaylistId = ref('')
  const selectPlaylist = vi.fn(async (playlist: MusicPlaylist) => { selectedPlaylist.value = playlist })
  const navigateTo = vi.fn()
  const toastInfo = vi.fn()

  const state = useMusicDetailRouteController({
    activeView: ref(view),
    routeQuery: ref({ view, id }),
    detailParent: ref(view === 'playlist-detail' ? 'playlists' : 'new-albums'),
    selectedPlaylist, selectedUserPlaylist, selectedArtist, selectedAlbum, selectedRank,
    userPlaylists, homePlaylists, targetUserPlaylistId,
    selectPlaylist,
    selectUserPlaylist: vi.fn(), selectArtistDetail: vi.fn(), selectAlbum: vi.fn(), selectRankAsPlaylist: vi.fn(),
    navigateTo, toastInfo,
  })
  return { state, selectedPlaylist, selectPlaylist, navigateTo, toastInfo }
}

describe('useMusicDetailRouteController', () => {
  it('restores a known playlist through the detail selector', async () => {
    const { state, selectedPlaylist, selectPlaylist } = setup('playlist-detail', 'playlist-1')
    await flush()
    expect(selectPlaylist).toHaveBeenCalledWith({ id: 'playlist-1', name: 'Saved' })
    expect(selectedPlaylist.value?.id).toBe('playlist-1')
    expect(state.restoring.value).toBe(false)
  })

  it('reports failed restoration and navigates to the detail parent', async () => {
    const { state, navigateTo, toastInfo } = setup('album-detail', 'missing')
    await nextTick()
    await flush()
    expect(toastInfo).toHaveBeenCalledWith('该专辑详情不可用，已返回专辑列表')
    expect(navigateTo).toHaveBeenCalledWith('new-albums')
    expect(state.restoring.value).toBe(false)
  })
})
