<template>
  <AppPageShell variant="compact" surface="consume" width="media" fill>
    <AppTwoColumnLayout preset="music">
      <template #header>
        <div class="music-nav-header">
          <AppSectionNav
            class="app-section-nav--optical"
            :model-value="musicActiveMode"
            :options="musicNavItems"
            aria-label="音乐分类"
            @update:model-value="(value) => handleMusicNavSelect(String(value))"
          />
        </div>
      </template>

      <div class="app-workbench__content music-content">
        <div v-if="isDetailView" class="music-detail-navigation">
          <Button text severity="secondary" size="sm" @click="goBackInMusic">
            <AppIcon name="chevronLeft" class="h-4 w-4" />
            {{ detailBackLabel }}
          </Button>
        </div>

        <AppBlockLoader v-if="restoringDetail" text="正在恢复详情..." />

        <MusicHomeView
          v-else-if="activeView === 'home'"
          :playlists="homePlaylists"
          :ranks="ranks"
          :albums="newAlbums"
          :playlists-loading="playlistsLoading"
          :ranks-loading="ranksLoading"
          :albums-loading="newAlbumsLoading"
          :history-tracks="profileHistory"
          :fm-mode="fm.mode.value"
          :fm-pool-id="fm.poolId.value"
          :fm-loading="fm.loading.value"
          :fm-active="fmActive"
          :fm-playing="fmPlaying"
          @navigate="handleNavigate"
          @select-playlist="handleSelectPlaylist"
          @select-rank="handleSelectRank"
          @select-album="handleSelectAlbum"
          @fm-play="handleHomeFmPlay"
          @play-playlist="handlePlayPlaylist"
          @play-album="handlePlayAlbum"
          @switch-fm-mode="handleSwitchFmMode"
          @switch-fm-pool="handleSwitchFmPool"
        />

        <MusicSearchView
          v-else-if="activeView === 'search'"
          :hot-searches="hotSearches"
          :loading="searchLoading"
          :error="searchError"
          :result="complexResult"
          :search-query="searchQuery"
          @search="handleSearch"
          @retry="searchQuery && handleSearch(searchQuery)"
          @select-artist="handleSelectArtistDetail"
          @select-album="handleSelectAlbumFromSearch"
        />

        <MusicRankGrid
          v-else-if="activeView === 'ranks'"
          :ranks="ranks"
          @select="handleSelectRank"
        />

        <MusicPlaylistGrid
          v-else-if="activeView === 'playlists'"
          :playlists="homePlaylists"
          :tags="playlistTags"
          :selected-category="selectedPlaylistCategory"
          :has-more="playlistHasMore"
          :loading="playlistsLoading"
          @select="handleSelectPlaylist"
          @play="handlePlayPlaylist"
          @select-category="handleSelectPlaylistCategoryLocal"
          @load-more="handleLoadMorePlaylistsLocal"
        />

        <MusicPlaylistDetailView
          v-else-if="activeView === 'playlist-detail' && selectedPlaylist"
          :playlist="selectedPlaylist"
          :tracks="tracks"
          :total="total"
          :loading="tracksLoading"
          :loading-more="tracksLoadingMore"
          :has-more="tracksHasMore"
          :similar="similarPlaylists"
          :show-collect="true"
          :collected="playlistCollected"
          @play-all="handlePlayAll"
          @collect="handleCollectPlaylist"
          @load-more="handleLoadMoreTracks"
          @select-artist="handleSelectArtistFromTrack"
          @select-album="handleSelectAlbumFromTrack"
          @play-mv="handlePlayMv"
          @select-related="handleSelectRelated"
          @add-to-playlist="handleAddToPlaylist"
          @change="handleChangePlaylist"
        />

        <MusicPlaylistDetailView
          v-else-if="activeView === 'user-playlist-detail' && userPlaylistAsPlaylist"
          :playlist="userPlaylistAsPlaylist"
          :tracks="tracks"
          :total="total"
          :loading="tracksLoading"
          :loading-more="tracksLoadingMore"
          :has-more="tracksHasMore"
          :similar="[]"
          :show-collect="false"
          :collected="false"
          @play-all="handlePlayAll"
          @load-more="handleLoadMoreTracks"
          @select-artist="handleSelectArtistFromTrack"
          @select-album="handleSelectAlbumFromTrack"
          @play-mv="handlePlayMv"
          @select-related="handleSelectRelated"
          @add-to-playlist="handleAddToPlaylist"
        />

        <MusicArtistDetailView
          v-else-if="activeView === 'artist-detail' && selectedArtist"
          :artist="selectedArtist"
          :tracks="tracks"
          :albums="artistAlbums"
          :videos="artistVideos"
          :followed="artistFollowed"
          :follow-loading="artistFollowLoading"
          :tracks-loading="tracksLoading"
          :loading-more="tracksLoadingMore"
          :has-more="tracksHasMore"
          @play-all="handlePlayAllArtistTracks"
          @follow="handleFollowArtist"
          @unfollow="handleUnfollowArtist"
          @load-more="handleLoadMoreTracks"
          @select-album="handleSelectAlbum"
          @play-video="handlePlayArtistVideo"
          @select-artist-track="handleSelectArtistFromTrack"
          @play-mv="handlePlayMv"
        />

        <MusicAlbumDetailView
          v-else-if="activeView === 'album-detail' && selectedAlbum"
          :album="selectedAlbum"
          :tracks="tracks"
          :total="total"
          :loading="tracksLoading"
          :loading-more="tracksLoadingMore"
          :has-more="tracksHasMore"
          @play-all="handlePlayAll"
          @load-more="handleLoadMoreTracks"
          @select-artist="handleSelectArtistFromAlbum"
          @select-artist-track="handleSelectArtistFromTrack"
          @play-mv="handlePlayMv"
        />

        <MusicProfileView
          v-else-if="activeView === 'profile'"
          :profile="kugouProfile"
          :auth-status="authStatus"
          :user-playlists="userPlaylists"
          :history="profileHistory"
          :listen-rank="profileListenRank"
          :history-loading="profileHistoryLoading"
          :rank-loading="profileRankLoading"
          :loading="profileLoading"
          :error="profileError"
          :logout-loading="logoutLoading"
          :vip-claim-status="vipClaimStatus"
          :vip-claim-loading="vipClaimLoading"
          :vip-claim-error="vipClaimError"
          :vip-claim-message="vipClaimMessage"
          :target-playlist-id="targetUserPlaylistId"
          :create-playlist="handleCreatePlaylist"
          @retry="handleLoadProfile"
          @logout="handleLogout"
          @claim-daily-vip="claimDailyVip"
          @play-all-profile="handlePlayAllProfile"
          @select-playlist="handleSelectUserPlaylist"
          @select-artist="handleSelectArtistFromTrack"
          @add-to-playlist="handleAddToPlaylist"
        >
          <template #login>
            <MusicQrLoginPanel
              :qr-open="qrLogin.isOpen.value"
              :qr-loading="qrLogin.loading.value"
              :qr-login="qrLogin.qrLogin.value"
              :qr-status="qrLogin.status.value"
              :qr-status-text="qrLogin.statusText.value"
              @open="qrLogin.open"
              @close="qrLogin.close"
              @refresh="qrLogin.open"
            />
          </template>
        </MusicProfileView>

        <MusicTrackList
          v-else-if="activeView === 'new-songs'"
          :tracks="newSongs"
          :show-mv="false"
          :show-related="false"
          @select-artist="handleSelectArtistFromTrack"
          @select-album="handleSelectAlbumFromTrack"
        />

        <MusicAlbumGrid
          v-else-if="activeView === 'new-albums'"
          :albums="viewAlbums"
          :loading="newAlbumsLoading"
          @select="handleSelectAlbum"
          @play="handlePlayAlbum"
        />

        <MusicTrackList
          v-else-if="activeView === 'favorites'"
          :tracks="favoriteTracks"
          :show-mv="false"
          :show-related="false"
          @select-artist="handleSelectArtistFromTrack"
          @select-album="handleSelectAlbumFromTrack"
        />

        <MusicTrackList
          v-else-if="activeView === 'ai-recommend'"
          :tracks="aiRecommend"
          :show-mv="false"
          :show-related="false"
          @select-artist="handleSelectArtistFromTrack"
          @select-album="handleSelectAlbumFromTrack"
        />

        <MusicTrackList
          v-else-if="activeView === 'everyday-recommend'"
          :tracks="everydayRecommend"
          :show-mv="false"
          :show-related="false"
          @select-artist="handleSelectArtistFromTrack"
          @select-album="handleSelectAlbumFromTrack"
        />
      </div>
    </AppTwoColumnLayout>

    <MusicVideoModal
      :visible="videoModalVisible"
      :title="videoTitle"
      :url="videoUrl"
      @close="handleCloseVideoModal"
    />
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSectionNav from '@/shared/components/layout/AppSectionNav.vue'
import AppTwoColumnLayout from '@/shared/components/layout/AppTwoColumnLayout.vue'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import MusicHomeView from '@/features/music/components/home/MusicHomeView.vue'
import MusicSearchView from '@/features/music/components/MusicSearchView.vue'
import MusicRankGrid from '@/features/music/components/MusicRankGrid.vue'
import MusicPlaylistGrid from '@/features/music/components/MusicPlaylistGrid.vue'
import MusicAlbumGrid from '@/features/music/components/MusicAlbumGrid.vue'
import MusicPlaylistDetailView from '@/features/music/components/MusicPlaylistDetailView.vue'
import MusicArtistDetailView from '@/features/music/components/MusicArtistDetailView.vue'
import MusicAlbumDetailView from '@/features/music/components/MusicAlbumDetailView.vue'
import MusicProfileView from '@/features/music/components/MusicProfileView.vue'
import MusicTrackList from '@/features/music/components/MusicTrackList.vue'
import MusicVideoModal from '@/features/music/components/MusicVideoModal.vue'
import MusicQrLoginPanel from '@/features/music/components/MusicQrLoginPanel.vue'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { useUIStore } from '@/shared/stores/ui'
import {
  useMusicNavigation,
  getMusicDetailIdentity,
  isMusicDetailView,
  type MusicDetailView,
  type MusicView,
} from '@/features/music/composables/useMusicNavigation'
import { useMusicRouteRestoration, type MusicDetailRoute } from '@/features/music/composables/useMusicRouteRestoration'
import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'
import { useMusicHome } from '@/features/music/composables/useMusicHome'
import { useMusicDetail } from '@/features/music/composables/useMusicDetail'
import { useMusicAuth } from '@/features/music/composables/useMusicAuth'
import { useMusicFm } from '@/features/music/composables/useMusicFm'
import {
  collectMusicPlaylist,
  getMusicAlbumDetail,
  getMusicArtistDetail,
  getMusicRankDetail,
  getMusicPlaylists,
  getMusicUserPlaylists,
  type MusicTrack,
  type MusicPlaylist,
  type MusicArtist,
  type MusicAlbum,
  type MusicRank,
  type MusicUserPlaylist,
} from '@/shared/api/music'
import { useMusicQrLogin } from '@/features/music/composables/useMusicQrLogin'
import { useMusicVideoModal } from '@/features/music/composables/useMusicVideoModal'
import { useMusicSearch } from '@/features/music/composables/useMusicSearch'
import { useMusicTrackNavigation } from '@/features/music/composables/useMusicTrackNavigation'
import { Logger } from '@/shared/lib/logger'
import { useToast } from '@/shared/components/toast/useToast'

const route = useRoute()
const uiStore = useUIStore()
const playerStore = useMusicPlayerStore()
const appNavigation = useNavigationHistory()
const toast = useToast()

const {
  activeView,
  navigateTo,
  goBack: goBackInMusic,
  isDetailView,
  detailParent,
} = useMusicNavigation()

const {
  playlists: homePlaylists,
  ranks,
  newAlbums,
  newSongs,
  hotSearches,
  aiRecommend,
  everydayRecommend,
  playlistsLoading,
  ranksLoading,
  newAlbumsLoading,
  playlistTags,
  selectedPlaylistCategory,
  playlistHasMore,
  loadHomeData,
  loadNewAlbumsForView,
  loadNewSongs,
  loadPlaylistTags,
  loadAiRecommend,
  loadEverydayRecommend,
  handleSelectPlaylistCategory,
  handleLoadMorePlaylists,
} = useMusicHome()

const {
  selectedPlaylist,
  selectedUserPlaylist,
  selectedArtist,
  selectedAlbum,
  selectedRank,
  tracks,
  tracksLoading,
  tracksLoadingMore,
  tracksHasMore,
  total,
  similarPlaylists,
  artistAlbums,
  artistVideos,
  artistFollowed,
  artistFollowLoading,
  playlistCollected,
  userPlaylistAsPlaylist,
  selectPlaylist,
  selectUserPlaylist,
  selectArtistDetail,
  selectAlbum,
  selectRankAsPlaylist,
  loadMoreTracks,
  followArtist,
  unfollowArtist,
  playAll,
  playAllArtistTracks,
} = useMusicDetail()

const {
  authStatus,
  kugouProfile,
  userPlaylists,
  targetUserPlaylistId,
  profileLoading,
  profileError,
  logoutLoading,
  profileHistory,
  profileListenRank,
  profileHistoryLoading,
  profileRankLoading,
  vipClaimStatus,
  vipClaimLoading,
  vipClaimError,
  vipClaimMessage,
  claimDailyVip,
  loadAuthStatus,
  loadProfile,
  logout,
  createPlaylist,
  addToPlaylist,
} = useMusicAuth()

const detailRoute = computed<MusicDetailRoute | null>(() => {
  if (!isMusicDetailView(activeView.value)) return null
  return {
    view: activeView.value,
    identity: getMusicDetailIdentity(route.query),
  }
})

const detailBackLabels: Record<MusicView, string> = {
  home: '返回首页',
  search: '返回搜索',
  fm: '返回首页',
  ranks: '返回榜单',
  playlists: '返回歌单',
  'playlist-detail': '返回歌单',
  'user-playlist-detail': '返回我的',
  'artist-detail': '返回搜索',
  'album-detail': '返回专辑',
  profile: '返回我的',
  'new-songs': '返回首页',
  'new-albums': '返回专辑',
  'ai-recommend': '返回首页',
  'everyday-recommend': '返回首页',
  favorites: '返回我的',
}
const detailBackLabel = computed(() => detailBackLabels[detailParent.value || 'home'])

function playlistIdentity(playlist: MusicPlaylist) {
  return {
    id: String(playlist.specialid || playlist.global_collection_id || playlist.id || ''),
    kind: playlist.kind,
  }
}

async function restoreDetail(request: MusicDetailRoute): Promise<boolean> {
  const identity = request.identity
  if (!identity?.id) return false

  if (request.view === 'artist-detail') {
    if (selectedArtist.value?.id === identity.id) return true
    const artist = await getMusicArtistDetail(identity.id)
    if (!artist) return false
    await selectArtistDetail(artist)
    return selectedArtist.value?.id === identity.id
  }

  if (request.view === 'album-detail') {
    if (selectedAlbum.value?.id === identity.id) return true
    const album = await getMusicAlbumDetail(identity.id)
    if (!album) return false
    await selectAlbum(album)
    return selectedAlbum.value?.id === identity.id
  }

  if (request.view === 'user-playlist-detail') {
    if (String(selectedUserPlaylist.value?.listid || '') === identity.id) return true
    const known = userPlaylists.value.find(item => String(item.listid || '') === identity.id)
    const playlist = known || (await getMusicUserPlaylists())?.items.find(
      item => String(item.listid || '') === identity.id,
    )
    if (!playlist) return false
    await selectUserPlaylist(playlist)
    targetUserPlaylistId.value = identity.id
    return String(selectedUserPlaylist.value?.listid || '') === identity.id
  }

  if (identity.kind === 'rank') {
    if (selectedRank.value?.id === identity.id && selectedPlaylist.value) return true
    const rank = await getMusicRankDetail(identity.id)
    if (!rank) return false
    await selectRankAsPlaylist({
      ...rank,
      rank_cid: identity.rankCid || '',
      play_count: 0,
    })
    return selectedRank.value?.id === identity.id && Boolean(selectedPlaylist.value)
  }

  if (playlistIdentity(selectedPlaylist.value || {}).id === identity.id && !selectedRank.value) return true
  let playlist = homePlaylists.value.find(item => playlistIdentity(item).id === identity.id)
  if (!playlist) {
    const data = await getMusicPlaylists({ page: 1, page_size: 100 })
    playlist = data?.items.find(item => playlistIdentity(item).id === identity.id)
  }
  if (!playlist) return false
  await selectPlaylist(playlist)
  return playlistIdentity(selectedPlaylist.value || {}).id === identity.id
}

function fallbackDetail(request: MusicDetailRoute) {
  const labels: Record<MusicDetailView, string> = {
    'playlist-detail': '该歌单无法从链接恢复，已返回歌单列表',
    'user-playlist-detail': '该个人歌单不可用，已返回我的音乐',
    'artist-detail': '该歌手详情不可用，已返回搜索',
    'album-detail': '该专辑详情不可用，已返回专辑列表',
  }
  toast.info(labels[request.view])
  navigateTo(detailParent.value || 'home')
}

const { restoring: restoringDetail } = useMusicRouteRestoration({
  route: detailRoute,
  restore: restoreDetail,
  fallback: fallbackDetail,
})

const fm = useMusicFm()
const fmTrack = computed(() => fm.batch.value[fm.batchIndex.value] || null)
const fmActive = computed(() => Boolean(
  playerStore.currentTrack?.hash && fm.batch.value.some(track => track.hash === playerStore.currentTrack?.hash),
))
const fmPlaying = computed(() => fmActive.value && playerStore.playing)

// ponytail: complex-search state + execute/reset live in useMusicSearch. The
// error-string mapping + empty-query reset policy are owned there; the view
// injects the navigation hand-off so the composable doesn't reach into nav.
const {
  searchLoading,
  searchError,
  complexResult,
  searchQuery,
  handleSearch,
  resetSearch,
} = useMusicSearch({
  isSearchView: () => activeView.value === 'search',
  onResetWhenSearching: () => navigateTo('home'),
})

// ponytail: MV/artist-video modal state + async URL resolution live in
// useMusicVideoModal. The two open-then-fetch flows + their error handling are
// co-located; the modal opens optimistically and the URL fills on response.
const {
  videoModalVisible,
  videoTitle,
  videoUrl,
  handlePlayMv,
  handlePlayArtistVideo,
  handleCloseVideoModal,
} = useMusicVideoModal()

// ponytail: QR login used to be hand-rolled inline (~50 lines mirroring
// useMusicQrLogin). The composable now owns open/close + polling + cleanup;
// we bridge its authStatus back into useMusicAuth so the logged_in watcher
// fires loadUserPlaylists exactly as before.
const qrLogin = useMusicQrLogin()

const viewAlbums = ref<MusicAlbum[]>([])

const sidebarActiveMode = computed(() => {
  if (activeView.value === 'playlist-detail') return 'playlists'
  if (activeView.value === 'user-playlist-detail') return 'favorites'
  if (activeView.value === 'search' || activeView.value === 'artist-detail' || activeView.value === 'album-detail') return ''
  if (activeView.value === 'everyday-recommend' || activeView.value === 'ai-recommend' || activeView.value === 'new-songs' || activeView.value === 'new-albums') return 'home'
  return activeView.value
})

const musicActiveMode = computed(() => {
  const valid = musicNavItems.value.some((item) => item.value === sidebarActiveMode.value)
  return valid ? sidebarActiveMode.value : ''
})

const musicNavItems = computed<Array<{ value: string; label: string }>>(() => [
  { value: 'home', label: '首页' },
  { value: 'ranks', label: '榜单' },
  { value: 'playlists', label: '歌单' },
  { value: 'profile', label: authStatus.value?.logged_in ? '我的' : '登录' },
])

// ponytail: bridge useMusicQrLogin.authStatus -> useMusicAuth.authStatus so
// the logged_in watcher (loadUserPlaylists) fires after a successful scan,
// preserving the pre-refactor side effect.
watch(() => qrLogin.authStatus.value, async (status) => {
  if (!status) return
  authStatus.value = status
  if (status.logged_in) {
    navigateTo('profile')
    await loadProfile()
  }
})

const favoriteTracks = computed(() => {
  const favoritePlaylist = userPlaylists.value.find(p => p.name === '我喜欢' || p.name === '我喜欢的音乐')
  if (favoritePlaylist && String(selectedUserPlaylist.value?.listid || '') === String(favoritePlaylist.listid || '')) {
    return tracks.value
  }
  return []
})

watch(() => uiStore.getSearchTrigger('music'), async () => {
  if (route.name === 'Music') {
    const query = uiStore.getSearchQuery('music').trim()
    if (!query) {
      resetSearch()
      return
    }
    handleNavigate('search')
    await handleSearch(query)
  }
})

onMounted(() => {
  loadAuthStatus()
  loadHomeData()
})

watch(
  [() => activeView.value, () => authStatus.value?.logged_in],
  ([view, loggedIn]) => {
    if (view !== 'profile' || !loggedIn || kugouProfile.value || profileLoading.value) return
    loadProfile()
  },
)

onUnmounted(() => {
  qrLogin.close()
  appNavigation.setInternalBackAvailable(false)
})

function handleNavigate(mode: string) {
  if (mode === 'home') {
    navigateTo('home')
  } else if (mode === 'search') {
    navigateTo('search')
  } else if (mode === 'fm' || mode === 'recommend') {
    navigateTo('home')
    if (!fm.batch.value.length) {
      fm.loadBatch(false, true, userPlaylists.value)
    } else {
      fm.playAt(fm.batchIndex.value)
    }
  } else if (mode === 'new-song' || mode === 'new_song' || mode === 'new-songs' || mode === 'new_songs') {
    navigateTo('new-songs')
    loadNewSongs()
  } else if (mode === 'rank' || mode === 'ranks') {
    navigateTo('ranks')
  } else if (mode === 'playlist' || mode === 'playlists') {
    navigateTo('playlists')
    if (!playlistTags.value.length) loadPlaylistTags()
  } else if (mode === 'new-album' || mode === 'new_album' || mode === 'new-albums' || mode === 'new_albums') {
    navigateTo('new-albums')
    loadNewAlbumsForView().then(() => {
      viewAlbums.value = newAlbums.value
    })
  } else if (mode === 'ai' || mode === 'ai_recommend') {
    navigateTo('ai-recommend')
    loadAiRecommend()
  } else if (mode === 'everyday' || mode === 'everyday-recommend') {
    navigateTo('everyday-recommend')
    loadEverydayRecommend()
  } else if (mode === 'favorites') {
    handleNavigateFavorites()
  } else if (mode === 'profile') {
    handleLoadProfile()
  }
}

function handleMusicNavSelect(mode: string) {
  if (musicActiveMode.value === mode) return
  handleNavigate(mode)
}

function handleNavigateFavorites() {
  if (!authStatus.value?.logged_in) {
    handleNavigate('profile')
    return
  }
  const favoritePlaylist = userPlaylists.value.find(p => p.name === '我喜欢' || p.name === '我喜欢的音乐')
  if (favoritePlaylist) {
    handleSelectUserPlaylist(favoritePlaylist)
  } else if (userPlaylists.value.length) {
    handleSelectUserPlaylist(userPlaylists.value[0])
  }
}

async function handleSelectPlaylist(playlist: MusicPlaylist) {
  await selectPlaylist(playlist)
  navigateTo('playlist-detail', playlistIdentity(playlist))
}

async function handleSelectUserPlaylist(playlist: MusicUserPlaylist) {
  await selectUserPlaylist(playlist)
  navigateTo('user-playlist-detail', { id: String(playlist.listid || '') })
  targetUserPlaylistId.value = String(playlist.listid || '')
}

async function handleSelectRank(rank: MusicRank) {
  await selectRankAsPlaylist(rank)
  navigateTo('playlist-detail', { id: rank.id, kind: 'rank', rankCid: rank.rank_cid })
}

async function handleSelectArtistDetail(artist: MusicArtist) {
  await selectArtistDetail(artist)
  navigateTo('artist-detail', { id: artist.id })
}

async function handleSelectAlbum(album: MusicAlbum) {
  await selectAlbum(album)
  navigateTo('album-detail', { id: album.id })
}

async function handleSelectAlbumFromSearch(album: MusicAlbum) {
  await handleSelectAlbum(album)
}

// ponytail: artist/album resolution from a track or album context lives in
// useMusicTrackNavigation. The fetch-then-navigate + error-toast pattern is
// co-located; the view's select handlers are injected so this composable
// doesn't reach into detail/navigation internals.
const {
  handleSelectArtistFromTrack,
  handleSelectAlbumFromTrack,
  handleSelectArtistFromAlbum,
} = useMusicTrackNavigation({
  selectedAlbum,
  onSelectArtist: handleSelectArtistDetail,
  onSelectAlbum: handleSelectAlbum,
})

function handlePlayAll(shuffle: boolean) {
  playAll(shuffle)
}

function handlePlayAllArtistTracks() {
  playAllArtistTracks()
}

function handlePlayAllProfile(category: 'history' | 'rank', shuffle: boolean) {
  const tracksList = category === 'history' ? profileHistory.value : profileListenRank.value
  playerStore.shuffle = shuffle
  playerStore.playQueue(tracksList, 0)
}

async function handlePlayPlaylist(playlist: MusicPlaylist) {
  if (await selectPlaylist(playlist)) {
    playAll(false)
  }
}

async function handlePlayAlbum(album: MusicAlbum) {
  if (await selectAlbum(album)) {
    playAll(false)
  }
}

function handleHomeFmPlay() {
  if (fm.loading.value) return
  if (fmActive.value && playerStore.currentTrack) {
    playerStore.togglePlayback()
    return
  }
  if (fmTrack.value) {
    fm.playAt(fm.batchIndex.value)
  } else if (fm.batch.value.length) {
    fm.playFirst()
  } else {
    fm.loadBatch(false, true, userPlaylists.value)
  }
}

function handleSwitchFmMode(mode: 'normal' | 'small' | 'peak') {
  fm.switchMode(mode)
}

function handleSwitchFmPool(poolId: string) {
  fm.switchPool(poolId)
}

async function handleLoadMoreTracks() {
  await loadMoreTracks()
}

async function handleCollectPlaylist() {
  if (!selectedPlaylist.value?.id) return
  try {
    await collectMusicPlaylist(selectedPlaylist.value.id)
    playlistCollected.value = true
  } catch (err) {
    Logger.warn('handleCollectPlaylist failed', err)
    toast.error('收藏歌单失败')
  }
}

function handleChangePlaylist(playlist: MusicPlaylist) {
  handleSelectPlaylist(playlist)
}

async function handleFollowArtist() {
  await followArtist()
}

async function handleUnfollowArtist() {
  await unfollowArtist()
}

async function handleSelectPlaylistCategoryLocal(categoryId: number) {
  await handleSelectPlaylistCategory(categoryId)
}

async function handleLoadMorePlaylistsLocal() {
  await handleLoadMorePlaylists()
}

async function handleCreatePlaylist(name: string) {
  return createPlaylist(name)
}

async function handleAddToPlaylist(track: MusicTrack) {
  await addToPlaylist(track)
}

function handleSelectRelated(track: MusicTrack) {
  Logger.info('Select related tracks', track)
}

async function handleLoadProfile() {
  navigateTo('profile')
  if (!authStatus.value?.logged_in) {
    qrLogin.close()
    return
  }
  await loadProfile()
}

async function handleLogout() {
  await logout()
}
</script>

<style scoped>
.music-nav-header {
  display: flex;
  width: 100%;
  min-width: 0;
  align-items: center;
  justify-content: flex-start;
  gap: var(--space-3);
}

.music-detail-navigation {
  display: flex;
  align-items: center;
  min-height: 2.25rem;
  margin-bottom: var(--space-3);
}

.music-content {
  min-height: 100%;
  max-width: var(--app-content-media-max);
  margin-inline: auto;
  padding-block: var(--space-4) var(--space-7);
}
</style>
