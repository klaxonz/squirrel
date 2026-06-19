<template>
  <div class="music-page">
    <main class="music-main">
      <div class="music-top-nav" aria-label="音乐导航">
        <div class="music-primary-tabs">
          <button
            v-for="item in musicNavItems"
            :key="item.id"
            class="music-primary-tab"
            :class="{ 'music-primary-tab--active': sidebarActiveMode === item.id }"
            @click="handleNavigate(item.id)"
          >
            <AppIcon :name="item.icon" class="h-4 w-4" />
            <span>{{ item.label }}</span>
          </button>
        </div>

        <MusicCreatePlaylistButton
          v-if="authStatus?.logged_in && activeView === 'profile'"
          class="music-top-create"
          @create="handleCreatePlaylist"
        />
      </div>

      <div class="music-content custom-scrollbar">
        <MusicHomeView
          v-if="activeView === 'home'"
          :playlists="homePlaylists"
          :ranks="ranks"
          :albums="newAlbums"
          :playlists-loading="playlistsLoading"
          :ranks-loading="ranksLoading"
          :albums-loading="newAlbumsLoading"
          :user="kugouProfile"
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
          @continue-play="handleContinuePlay"
          @play-playlist="handlePlayPlaylist"
          @switch-fm-mode="handleSwitchFmMode"
          @switch-fm-pool="handleSwitchFmPool"
        />

        <MusicSearchView
          v-else-if="activeView === 'search'"
          :hot-searches="hotSearches"
          :loading="searchLoading"
          :result="complexResult"
          :search-query="searchQuery"
          @search="handleSearch"
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
          :rank-type="profileRankType"
          :loading="profileLoading"
          :error="profileError"
          :logout-loading="logoutLoading"
          :target-playlist-id="targetUserPlaylistId"
          @retry="handleLoadProfile"
          @logout="handleLogout"
          @toggle-rank-type="handleToggleRankType"
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
    </main>

    <MusicVideoModal
      :visible="videoModalVisible"
      :title="videoTitle"
      :url="videoUrl"
      @close="handleCloseVideoModal"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'
import MusicCreatePlaylistButton from '@/features/music/components/sidebar/MusicCreatePlaylistButton.vue'
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
import { useMusicNavigation } from '@/features/music/composables/useMusicNavigation'
import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'
import { useMusicHome } from '@/features/music/composables/useMusicHome'
import { useMusicDetail } from '@/features/music/composables/useMusicDetail'
import { useMusicAuth } from '@/features/music/composables/useMusicAuth'
import { useMusicFm } from '@/features/music/composables/useMusicFm'
import {
  searchMusicComplex,
  getMusicTrackMv,
  getMusicVideoUrl,
  collectMusicPlaylist,
  getMusicArtistDetail,
  getMusicAlbumDetail,
  type MusicTrack,
  type MusicPlaylist,
  type MusicArtist,
  type MusicAlbum,
  type MusicRank,
  type MusicUserPlaylist,
} from '@/shared/api/music'
import { useMusicQrLogin } from '@/features/music/composables/useMusicQrLogin'
import { Logger } from '@/shared/lib/logger'

const route = useRoute()
const uiStore = useUIStore()
const playerStore = useMusicPlayerStore()
const appNavigation = useNavigationHistory()

const {
  activeView,
  navigateTo,
  goBack: goBackInMusic,
  canGoBack: canGoBackInMusic,
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
  profileRankType,
  loadAuthStatus,
  loadProfile,
  toggleRankType,
  logout,
  createPlaylist,
  addToPlaylist,
} = useMusicAuth()

const fm = useMusicFm()
const fmTrack = computed(() => fm.batch.value[fm.batchIndex.value] || null)
const fmActive = computed(() => Boolean(
  playerStore.currentTrack?.hash && fm.batch.value.some(track => track.hash === playerStore.currentTrack?.hash),
))
const fmPlaying = computed(() => fmActive.value && playerStore.playing)

const searchLoading = ref(false)
const complexResult = ref<{ songs: MusicTrack[]; artists: MusicArtist[]; albums: MusicAlbum[] } | null>(null)
const searchQuery = ref('')

const videoModalVisible = ref(false)
const videoTitle = ref('')
const videoUrl = ref('')

// ponytail: QR login used to be hand-rolled inline (~50 lines mirroring
// useMusicQrLogin). The composable now owns open/close + polling + cleanup;
// we bridge its authStatus back into useMusicAuth so the logged_in watcher
// fires loadUserPlaylists exactly as before.
const qrLogin = useMusicQrLogin()

const viewAlbums = ref<MusicAlbum[]>([])
let unregisterInternalBack: (() => void) | null = null

const sidebarActiveMode = computed(() => {
  if (activeView.value === 'playlist-detail') return 'playlists'
  if (activeView.value === 'user-playlist-detail') return 'favorites'
  if (activeView.value === 'search' || activeView.value === 'artist-detail' || activeView.value === 'album-detail') return ''
  if (activeView.value === 'everyday-recommend' || activeView.value === 'ai-recommend' || activeView.value === 'new-songs' || activeView.value === 'new-albums') return 'home'
  return activeView.value
})

const musicNavItems = computed<Array<{ id: string; label: string; icon: AppIconName }>>(() => [
  { id: 'home', label: '首页', icon: 'home' },
  { id: 'ranks', label: '榜单', icon: 'list' },
  { id: 'playlists', label: '歌单', icon: 'playlistMusic' },
  { id: 'profile', label: authStatus.value?.logged_in ? '我的' : '登录', icon: 'user' },
])

// ponytail: bridge useMusicQrLogin.authStatus -> useMusicAuth.authStatus so
// the logged_in watcher (loadUserPlaylists) fires after a successful scan,
// preserving the pre-refactor side effect.
watch(() => qrLogin.authStatus.value, (status) => {
  if (status) authStatus.value = status
})

const favoriteTracks = computed(() => {
  const favoritePlaylist = userPlaylists.value.find(p => p.name === '我喜欢' || p.name === '我喜欢的音乐')
  if (favoritePlaylist && selectedUserPlaylist.value?.id === favoritePlaylist.id) {
    return tracks.value
  }
  return []
})

watch(() => uiStore.searchTrigger, () => {
  if (route.name === 'Music') {
    const query = uiStore.searchQuery.trim()
    if (!query) {
      resetSearch()
      return
    }
    handleNavigate('search')
    handleSearch(query)
  }
})

watch(canGoBackInMusic, (available) => {
  appNavigation.setInternalBackAvailable(available)
}, { immediate: true })

onMounted(() => {
  loadAuthStatus()
  loadHomeData()
  unregisterInternalBack = appNavigation.registerInternalBackHandler(goBackInMusic)
})

onUnmounted(() => {
  qrLogin.close()
  unregisterInternalBack?.()
  unregisterInternalBack = null
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

async function handleSearch(query: string) {
  const normalizedQuery = query.trim()
  if (!normalizedQuery) {
    resetSearch()
    return
  }
  searchQuery.value = normalizedQuery
  searchLoading.value = true
  const { data } = await searchMusicComplex(normalizedQuery)
  searchLoading.value = false
  complexResult.value = data || { songs: [], artists: [], albums: [] }
}

function resetSearch() {
  searchQuery.value = ''
  searchLoading.value = false
  complexResult.value = null
  if (activeView.value === 'search') {
    navigateTo('home')
  }
}

async function handleSelectPlaylist(playlist: MusicPlaylist) {
  await selectPlaylist(playlist)
  navigateTo('playlist-detail')
}

async function handleSelectUserPlaylist(playlist: MusicUserPlaylist) {
  await selectUserPlaylist(playlist)
  navigateTo('user-playlist-detail')
  targetUserPlaylistId.value = playlist.id
}

async function handleSelectRank(rank: MusicRank) {
  await selectRankAsPlaylist(rank)
  navigateTo('playlist-detail')
}

async function handleSelectArtistDetail(artist: MusicArtist) {
  await selectArtistDetail(artist)
  navigateTo('artist-detail')
}

async function handleSelectAlbum(album: MusicAlbum) {
  await selectAlbum(album)
  navigateTo('album-detail')
}

async function handleSelectAlbumFromSearch(album: MusicAlbum) {
  await handleSelectAlbum(album)
}

function handleSelectArtistFromAlbum() {
  if (selectedAlbum.value?.artist_id) {
    const artist: MusicArtist = {
      id: selectedAlbum.value.artist_id,
      name: selectedAlbum.value.artist || '',
      avatar: '',
      intro: '',
      song_count: 0,
      album_count: 0,
      fan_count: 0,
    }
    handleSelectArtistDetail(artist)
  }
}

function handlePlayAll(shuffle: boolean) {
  playAll(shuffle)
}

function handlePlayAllArtistTracks() {
  playAllArtistTracks()
}

function handlePlayAllProfile(shuffle: boolean) {
  const tracksList = activeView.value === 'profile' ? profileHistory.value : profileListenRank.value
  playerStore.shuffle = shuffle
  playerStore.playQueue(tracksList, 0)
}

function handlePlayPlaylist(playlist: MusicPlaylist) {
  selectPlaylist(playlist).then(() => {
    playAll(false)
  })
}

function handleContinuePlay(track: MusicTrack) {
  if (playerStore.continueLastSession()) {
    return
  }
  if (track) playerStore.playTrack(track)
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
  const { error } = await collectMusicPlaylist(selectedPlaylist.value.id)
  if (!error) {
    playlistCollected.value = true
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
  await createPlaylist(name)
}

async function handleAddToPlaylist(track: MusicTrack) {
  await addToPlaylist(track)
}

async function handlePlayMv(track: MusicTrack) {
  if (!track.album_audio_id) return
  const { data: mvData } = await getMusicTrackMv(track.album_audio_id)
  const mv = mvData?.items?.[0]
  if (!mv?.id) return

  videoTitle.value = `${track.title} - ${track.artist}`
  videoModalVisible.value = true
  videoUrl.value = ''

  const { data: urlData } = await getMusicVideoUrl(mv.id)
  videoUrl.value = urlData?.url || ''
}

function handlePlayArtistVideo(video: { id: string; name: string }) {
  videoTitle.value = video.name
  videoModalVisible.value = true
  videoUrl.value = ''

  getMusicVideoUrl(video.id).then(({ data }) => {
    videoUrl.value = data?.url || ''
  })
}

function handleCloseVideoModal() {
  videoModalVisible.value = false
  videoUrl.value = ''
}

function handleSelectRelated(track: MusicTrack) {
  Logger.info('Select related tracks', track)
}

async function handleSelectArtistFromTrack(track: MusicTrack) {
  if (!track.artist_id) return
  const { data } = await getMusicArtistDetail(track.artist_id)
  if (data) {
    handleSelectArtistDetail(data)
  }
}

async function handleSelectAlbumFromTrack(track: MusicTrack) {
  if (!track.album_id) return
  const { data } = await getMusicAlbumDetail(track.album_id)
  if (data) {
    handleSelectAlbum(data)
  }
}

async function handleLoadProfile() {
  navigateTo('profile')
  if (!authStatus.value?.logged_in) {
    qrLogin.close()
    return
  }
  await loadProfile()
}

function handleToggleRankType(type: 0 | 1) {
  toggleRankType(type)
}

async function handleLogout() {
  await logout()
}
</script>

<style scoped>
.music-page {
  display: flex;
  height: 100%;
  background: hsl(var(--background));
}

.music-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.music-top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 2rem;
  border-bottom: 1px solid hsl(var(--border) / 0.35);
  background: hsl(var(--background) / 0.96);
}

.music-primary-tabs {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  overflow-x: auto;
  scrollbar-width: none;
}

.music-primary-tabs::-webkit-scrollbar {
  display: none;
}

.music-primary-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  height: 2.25rem;
  padding: 0 0.75rem;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.music-primary-tab:hover {
  background: hsl(var(--accent) / 0.7);
  color: hsl(var(--foreground));
}

.music-primary-tab--active {
  background: hsl(var(--accent));
  border-color: hsl(var(--border) / 0.6);
  color: hsl(var(--foreground));
}

.music-top-create {
  flex: 0 0 auto;
}

.music-top-create :deep(.music-create-playlist-btn),
.music-create-playlist-btn.music-top-create {
  width: auto;
  height: 2.25rem;
  margin: 0;
  padding: 0 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
}

.music-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: hsl(var(--muted-foreground) / 0.2);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--muted-foreground) / 0.35);
}

@media (max-width: 768px) {
  .music-top-nav {
    padding: 0.625rem 1rem;
  }
}
</style>
