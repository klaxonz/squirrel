import { computed, type Ref } from 'vue'

import {
  getMusicAlbumDetail,
  getMusicArtistDetail,
  getMusicPlaylists,
  getMusicRankDetail,
  getMusicUserPlaylists,
  type MusicAlbum,
  type MusicArtist,
  type MusicPlaylist,
  type MusicRank,
  type MusicUserPlaylist,
} from '@/shared/api/music'
import {
  getMusicDetailIdentity,
  isMusicDetailView,
  type MusicDetailView,
  type MusicView,
} from './useMusicNavigation'
import { useMusicRouteRestoration, type MusicDetailRoute } from './useMusicRouteRestoration'

type MusicDetailState = {
  selectedPlaylist: Ref<MusicPlaylist | null>
  selectedUserPlaylist: Ref<MusicUserPlaylist | null>
  selectedArtist: Ref<MusicArtist | null>
  selectedAlbum: Ref<MusicAlbum | null>
  selectedRank: Ref<MusicRank | null>
  userPlaylists: Ref<MusicUserPlaylist[]>
  homePlaylists: Ref<MusicPlaylist[]>
  targetUserPlaylistId: Ref<string>
  selectPlaylist: (playlist: MusicPlaylist) => Promise<unknown>
  selectUserPlaylist: (playlist: MusicUserPlaylist) => Promise<unknown>
  selectArtistDetail: (artist: MusicArtist) => Promise<unknown>
  selectAlbum: (album: MusicAlbum) => Promise<unknown>
  selectRankAsPlaylist: (rank: MusicRank & { rank_cid?: string; play_count?: number }) => Promise<unknown>
}

type MusicDetailRouteControllerOptions = MusicDetailState & {
  activeView: Ref<MusicView>
  routeQuery: Ref<Record<string, unknown>>
  detailParent: Ref<MusicView | null>
  navigateTo: (view: MusicView) => void
  toastInfo: (message: string) => void
}

function playlistIdentity(playlist: MusicPlaylist | null): string {
  return String(playlist?.specialid || playlist?.global_collection_id || playlist?.id || '')
}

export function useMusicDetailRouteController(options: MusicDetailRouteControllerOptions) {
  const detailRoute = computed<MusicDetailRoute | null>(() => {
    if (!isMusicDetailView(options.activeView.value)) return null
    return { view: options.activeView.value, identity: getMusicDetailIdentity(options.routeQuery.value) }
  })

  async function restore(request: MusicDetailRoute): Promise<boolean> {
    const identity = request.identity
    if (!identity?.id) return false

    if (request.view === 'artist-detail') {
      if (options.selectedArtist.value?.id === identity.id) return true
      const artist = await getMusicArtistDetail(identity.id)
      if (!artist) return false
      await options.selectArtistDetail(artist)
      return options.selectedArtist.value?.id === identity.id
    }

    if (request.view === 'album-detail') {
      if (options.selectedAlbum.value?.id === identity.id) return true
      const album = await getMusicAlbumDetail(identity.id)
      if (!album) return false
      await options.selectAlbum(album)
      return options.selectedAlbum.value?.id === identity.id
    }

    if (request.view === 'user-playlist-detail') {
      if (String(options.selectedUserPlaylist.value?.listid || '') === identity.id) return true
      const known = options.userPlaylists.value.find(item => String(item.listid || '') === identity.id)
      const playlist = known || (await getMusicUserPlaylists())?.items.find(
        item => String(item.listid || '') === identity.id,
      )
      if (!playlist) return false
      await options.selectUserPlaylist(playlist)
      options.targetUserPlaylistId.value = identity.id
      return String(options.selectedUserPlaylist.value?.listid || '') === identity.id
    }

    if (identity.kind === 'rank') {
      if (options.selectedRank.value?.id === identity.id && options.selectedPlaylist.value) return true
      const rank = await getMusicRankDetail(identity.id)
      if (!rank) return false
      await options.selectRankAsPlaylist({ ...rank, rank_cid: identity.rankCid || '', play_count: 0 })
      return options.selectedRank.value?.id === identity.id && Boolean(options.selectedPlaylist.value)
    }

    if (playlistIdentity(options.selectedPlaylist.value) === identity.id && !options.selectedRank.value) return true
    let playlist = options.homePlaylists.value.find(item => playlistIdentity(item) === identity.id)
    if (!playlist) {
      const data = await getMusicPlaylists({ page: 1, page_size: 100 })
      playlist = data?.items.find(item => playlistIdentity(item) === identity.id)
    }
    if (!playlist) return false
    await options.selectPlaylist(playlist)
    return playlistIdentity(options.selectedPlaylist.value) === identity.id
  }

  function fallback(request: MusicDetailRoute) {
    const labels: Record<MusicDetailView, string> = {
      'playlist-detail': '该歌单无法从链接恢复，已返回歌单列表',
      'user-playlist-detail': '该个人歌单不可用，已返回我的音乐',
      'artist-detail': '该歌手详情不可用，已返回搜索',
      'album-detail': '该专辑详情不可用，已返回专辑列表',
    }
    options.toastInfo(labels[request.view])
    options.navigateTo(options.detailParent.value || 'home')
  }

  const restoration = useMusicRouteRestoration({ route: detailRoute, restore, fallback })
  return { detailRoute, restoring: restoration.restoring }
}
