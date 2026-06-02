<template>
  <AppPageShell variant="compact">
    <div class="music-page">
      <MusicSidebar
        :active-mode="activeView"
        :user-playlists="userPlaylists"
        :selected-user-playlist="selectedUserPlaylist"
        :auth-status="authStatus"
        @navigate="handleSetMode"
        @select-playlist="handleSelectUserPlaylist"
        @create-playlist="handleCreatePlaylist"
      />

      <section class="music-main">
        <div class="music-content custom-scrollbar">
          <MusicHomeView
            v-if="activeView === 'home'"
            :banners="banners"
            :playlists="playlists"
            :ranks="ranks"
            :albums="newAlbums"
            :loading="playlistsLoading"
            :ranks-loading="ranksLoading"
            :albums-loading="newAlbumsLoading"
            @navigate="handleSetMode"
            @select-playlist="handleSelectPlaylist"
            @select-rank="handleSelectRank"
            @select-album="handleSelectAlbum"
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
            @more-songs="handleMoreSongs"
          />

          <MusicFmView
            v-else-if="activeView === 'fm'"
            :batch="fmBatch"
            :mode="fmMode"
            :pool-id="fmPoolId"
            :hearted="fmHearted"
            :loading="fmLoading"
            :liking="fmLiking"
            :error="fmError"
            @next="handleFmNext"
            @like="handleFmLike"
            @dislike="handleFmDislike"
            @switch-mode="handleFmSwitchMode($event as any)"
            @switch-pool="handleFmSwitchPool($event as any)"
            @play-first="handleFmPlayFirst"
            @select-artist="handleSelectArtistFromTrack"
          />

          <MusicRankGrid
            v-else-if="activeView === 'ranks'"
            :ranks="ranks"
            @select="handleSelectRank"
          />

          <MusicPlaylistGrid
            v-else-if="activeView === 'playlists'"
            :playlists="playlists"
            :tags="playlistTags"
            :selected-category="selectedPlaylistCategory"
            :has-more="playlistHasMore"
            :loading="playlistsLoading"
            @select="handleSelectPlaylist"
            @select-category="handleSelectPlaylistCategory"
            @load-more="handleLoadMorePlaylists"
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
            :favorite-counts="favoriteCounts"
            :show-collect="true"
            :collected="playlistCollected"
            :collect-loading="collectLoading"
            @play-all="handlePlayAll"
            @collect="handleCollectPlaylist"
            @load-more="handleLoadMoreTracks"
            @select-artist="handleSelectArtistFromTrack"
            @select-album="handleSelectAlbumFromTrack"
            @play-mv="handlePlayMv"
            @select-related="handleSelectRelated"
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
            :favorite-counts="favoriteCounts"
            :show-collect="false"
            :collected="false"
            :collect-loading="false"
            @play-all="handlePlayAll"
            @load-more="handleLoadMoreTracks"
            @select-artist="handleSelectArtistFromTrack"
            @select-album="handleSelectAlbumFromTrack"
            @play-mv="handlePlayMv"
            @select-related="handleSelectRelated"
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
                :qr-open="qrOpen"
                :qr-loading="qrLoading"
                :qr-login="qrLogin"
                :qr-status="qrStatus"
                :qr-status-text="qrStatusText"
                @open="handleOpenQrLogin"
                @close="handleCloseQrLogin"
                @refresh="handleOpenQrLogin"
              />
            </template>
          </MusicProfileView>

          <MusicTrackList
            v-else-if="activeView === 'new-songs'"
            :tracks="tracks"
            :show-mv="false"
            :show-related="false"
            @select-artist="handleSelectArtistFromTrack"
            @select-album="handleSelectAlbumFromTrack"
          />

          <MusicAlbumGrid
            v-else-if="activeView === 'new-albums'"
            :albums="newAlbums"
            :loading="newAlbumsLoading"
            @select="handleSelectAlbum"
          />

          <MusicTrackList
            v-else-if="activeView === 'ai-recommend'"
            :tracks="tracks"
            :show-mv="false"
            :show-related="false"
            @select-artist="handleSelectArtistFromTrack"
            @select-album="handleSelectAlbumFromTrack"
          />

          <MusicTrackList
            v-else-if="activeView === 'everyday-recommend'"
            :tracks="tracks"
            :show-mv="false"
            :show-related="false"
            @select-artist="handleSelectArtistFromTrack"
            @select-album="handleSelectAlbumFromTrack"
          />
        </div>
      </section>

      <MusicVideoModal
        :visible="videoModalVisible"
        :title="videoTitle"
        :url="videoUrl"
        @close="handleCloseVideoModal"
      />
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import MusicSidebar from '@/components/music/MusicSidebar.vue'
import MusicHomeView from '@/components/music/MusicHomeView.vue'
import MusicSearchView from '@/components/music/MusicSearchView.vue'
import MusicFmView from '@/components/music/MusicFmView.vue'
import MusicRankGrid from '@/components/music/MusicRankGrid.vue'
import MusicPlaylistGrid from '@/components/music/MusicPlaylistGrid.vue'
import MusicAlbumGrid from '@/components/music/MusicAlbumGrid.vue'
import MusicPlaylistDetailView from '@/components/music/MusicPlaylistDetailView.vue'
import MusicArtistDetailView from '@/components/music/MusicArtistDetailView.vue'
import MusicAlbumDetailView from '@/components/music/MusicAlbumDetailView.vue'
import MusicProfileView from '@/components/music/MusicProfileView.vue'
import MusicTrackList from '@/components/music/MusicTrackList.vue'
import MusicVideoModal from '@/components/music/MusicVideoModal.vue'
import MusicQrLoginPanel from '@/components/music/MusicQrLoginPanel.vue'
import { useMusicPlayerStore } from '@/stores/musicPlayer'
import { useUIStore } from '@/stores/ui'
import { useMusicFm } from '@/composables/useMusicFm'
import { useMusicQrLogin } from '@/composables/useMusicQrLogin'
import { Logger } from '@/utils/logger'
import {
  getMusicBanner,
  getMusicRanks,
  getMusicPlaylists,
  getMusicPlaylistTags,
  getMusicPlaylistTracks,
  getMusicSimilarPlaylists,
  getMusicUserPlaylists,
  getMusicUserPlaylistTracks,
  getMusicArtistDetail,
  getMusicArtistTracks,
  getMusicArtistAlbums,
  getMusicArtistVideos,
  getMusicAlbumDetail,
  getMusicAlbumTracks,
  getMusicNewSongs,
  getMusicNewAlbums,
  getMusicHotSearch,
  searchMusicComplex,
  getMusicAuthStatus,
  getMusicUserProfile,
  getMusicUserHistory,
  getMusicUserListenRank,
  getMusicFavoriteCount,
  getMusicTrackMv,
  getMusicVideoUrl,
  getMusicSongComments,
  getMusicCommentCounts,
  createMusicUserPlaylist,
  collectMusicPlaylist,
  deleteMusicUserPlaylist,
  addMusicUserPlaylistTrack,
  followMusicArtist,
  unfollowMusicArtist,
  logoutMusicUser,
  createMusicQrLogin,
  checkMusicQrLogin,
  getMusicAiRecommend,
  getMusicEverydayRecommend,
  type MusicTrack,
  type MusicPlaylist,
  type MusicRank,
  type MusicAlbum,
  type MusicArtist,
  type MusicUserPlaylist,
  type MusicVideo,
  type MusicAuthStatus,
  type MusicUserProfile,
  type MusicQrLogin,
  type MusicHotSearch,
  type MusicPlaylistTag,
} from '@/api/music'

type MusicView = 
  | 'home' 
  | 'search' 
  | 'fm' 
  | 'ranks' 
  | 'playlists' 
  | 'playlist-detail' 
  | 'user-playlist-detail'
  | 'artist-detail' 
  | 'album-detail' 
  | 'profile' 
  | 'new-songs' 
  | 'new-albums'
  | 'ai-recommend'
  | 'everyday-recommend'

const route = useRoute()
const uiStore = useUIStore()
const store = useMusicPlayerStore()

const activeView = ref<MusicView>('home')
const trackSource = ref<string>('idle')

const banners = ref<Array<{ id: string; title: string; cover: string }>>([])
const bannerLoading = ref(false)

const ranks = ref<MusicRank[]>([])
const ranksLoading = ref(false)

const playlists = ref<MusicPlaylist[]>([])
const playlistsLoading = ref(false)
const playlistTags = ref<MusicPlaylistTag[]>([])
const selectedPlaylistCategory = ref(0)
const playlistHasMore = ref(false)

const selectedPlaylist = ref<MusicPlaylist | null>(null)
const selectedUserPlaylist = ref<MusicUserPlaylist | null>(null)
const selectedArtist = ref<MusicArtist | null>(null)
const selectedAlbum = ref<MusicAlbum | null>(null)

const tracks = ref<MusicTrack[]>([])
const tracksLoading = ref(false)
const tracksLoadingMore = ref(false)
const tracksHasMore = ref(false)
const total = ref(0)
const currentPage = ref(1)
const favoriteCounts = ref<Record<string, number>>({})

const similarPlaylists = ref<MusicPlaylist[]>([])
const artistAlbums = ref<MusicAlbum[]>([])
const artistVideos = ref<MusicVideo[]>([])
const artistFollowed = ref(false)
const artistFollowLoading = ref(false)

const userPlaylists = ref<MusicUserPlaylist[]>([])
const targetUserPlaylistId = ref('')

const newAlbums = ref<MusicAlbum[]>([])
const newAlbumsLoading = ref(false)

const hotSearches = ref<MusicHotSearch[]>([])
const searchLoading = ref(false)
const complexResult = ref<{ songs: MusicTrack[]; artists: MusicArtist[]; albums: MusicAlbum[] } | null>(null)
const searchQuery = ref('')

const authStatus = ref<MusicAuthStatus | null>(null)
const kugouProfile = ref<MusicUserProfile | null>(null)
const profileLoading = ref(false)
const profileError = ref('')
const logoutLoading = ref(false)
const profileHistory = ref<MusicTrack[]>([])
const profileListenRank = ref<MusicTrack[]>([])
const profileHistoryLoading = ref(false)
const profileRankLoading = ref(false)
const profileRankType = ref<0 | 1>(0)

const playlistCollected = ref(false)
const collectLoading = ref(false)

const videoModalVisible = ref(false)
const videoTitle = ref('')
const videoUrl = ref('')

const qrOpen = ref(false)
const qrLoading = ref(false)
const qrLogin = ref<MusicQrLogin | null>(null)
const qrStatus = ref(0)
let qrTimer: ReturnType<typeof setInterval> | null = null

const fm = useMusicFm()
const fmBatch = computed(() => fm.batch.value)
const fmMode = computed(() => fm.mode.value)
const fmPoolId = computed(() => fm.poolId.value)
const fmLoading = computed(() => fm.loading.value)
const fmLiking = computed(() => fm.liking.value)
const fmError = computed(() => fm.error.value)
const fmHearted = computed(() => fm.hearted.value)

const qrStatusText = computed(() => {
  if (qrLoading.value) return 'Generating QR code'
  if (qrStatus.value === 4) return 'Login successful'
  if (qrStatus.value === 2) return 'Scanned, please confirm'
  if (qrStatus.value === 0 && qrLogin.value) return 'QR code expired, refresh'
  return 'Scan with KuGou Music App'
})

const userPlaylistAsPlaylist = computed(() => {
  if (!selectedUserPlaylist.value) return null
  const pl = selectedUserPlaylist.value
  return {
    id: pl.id,
    name: pl.name,
    cover: pl.cover,
    intro: '',
    creator: '',
    play_count: 0,
    collect_count: 0,
    tags: [],
    list_create_userid: pl.list_create_userid,
    list_create_listid: pl.list_create_listid,
    list_create_gid: pl.list_create_gid,
  } as MusicPlaylist
})

watch(() => uiStore.searchTrigger, () => {
  if (route.name === 'Music' && uiStore.searchQuery) {
    handleSetMode('search')
    handleSearch(uiStore.searchQuery)
  }
})

watch(() => authStatus.value?.logged_in, (loggedIn) => {
  if (loggedIn) {
    loadUserPlaylists()
  } else {
    userPlaylists.value = []
    kugouProfile.value = null
  }
})

onMounted(() => {
  loadAuthStatus()
  loadInitialData()
})

onUnmounted(() => {
  stopQrPolling()
})

async function loadInitialData() {
  await Promise.all([
    loadBanners(),
    loadRanks(),
    loadPlaylists(),
    loadNewAlbums(),
    loadHotSearches(),
  ])
}

async function loadAuthStatus() {
  const { data } = await getMusicAuthStatus()
  authStatus.value = data || null
  if (data?.logged_in) {
    loadUserPlaylists()
  }
}

async function loadBanners() {
  bannerLoading.value = true
  const { data } = await getMusicBanner()
  bannerLoading.value = false
  banners.value = data?.items || []
}

async function loadRanks() {
  ranksLoading.value = true
  const { data } = await getMusicRanks()
  ranksLoading.value = false
  ranks.value = data?.items || []
}

async function loadPlaylists(append = false) {
  playlistsLoading.value = true
  const { data } = await getMusicPlaylists({
    category_id: selectedPlaylistCategory.value,
    page: 1,
    page_size: 20,
  })
  playlistsLoading.value = false
  playlists.value = data?.items || []
  playlistHasMore.value = data?.has_more || false
}

async function loadPlaylistTags() {
  const { data } = await getMusicPlaylistTags()
  playlistTags.value = (data?.items || []).slice(0, 12) as MusicPlaylistTag[]
}

async function loadNewAlbums() {
  newAlbumsLoading.value = true
  const { data } = await getMusicNewAlbums({ page: 1, page_size: 6 })
  newAlbumsLoading.value = false
  newAlbums.value = data?.items || []
}

async function loadHotSearches() {
  const { data } = await getMusicHotSearch()
  hotSearches.value = (data?.items || []).slice(0, 12) as MusicHotSearch[]
}

async function loadUserPlaylists() {
  const { data } = await getMusicUserPlaylists()
  userPlaylists.value = data?.items || []
  if (userPlaylists.value.length && !targetUserPlaylistId.value) {
    targetUserPlaylistId.value = userPlaylists.value[0].id
  }
}

function handleSetMode(mode: string) {
  if (mode === 'home') {
    activeView.value = 'home'
  } else if (mode === 'search') {
    activeView.value = 'search'
  } else if (mode === 'fm' || mode === 'recommend') {
    activeView.value = 'fm'
    fm.loadBatch(false, true, userPlaylists.value)
  } else if (mode === 'new_song' || mode === 'new_songs') {
    activeView.value = 'new-songs'
    loadNewSongs()
  } else if (mode === 'rank' || mode === 'ranks') {
    activeView.value = 'ranks'
  } else if (mode === 'playlist' || mode === 'playlists') {
    activeView.value = 'playlists'
    if (!playlistTags.value.length) loadPlaylistTags()
  } else if (mode === 'new_album' || mode === 'new_albums') {
    activeView.value = 'new-albums'
    loadNewAlbumsForView()
  } else if (mode === 'ai' || mode === 'ai_recommend') {
    activeView.value = 'ai-recommend'
    loadAiRecommend()
  } else if (mode === 'everyday' || mode === 'everyday-recommend') {
    activeView.value = 'everyday-recommend'
    loadEverydayRecommend()
  } else if (mode === 'profile') {
    handleLoadProfile()
  }
}

function handleNavigate(section: string) {
  if (section === 'playlists') {
    activeView.value = 'playlists'
  } else if (section === 'ranks') {
    activeView.value = 'ranks'
  } else if (section === 'new-albums') {
    activeView.value = 'new-albums'
  }
}

async function handleSearch(query: string) {
  searchQuery.value = query
  searchLoading.value = true
  const { data } = await searchMusicComplex(query)
  searchLoading.value = false
  complexResult.value = data || { songs: [], artists: [], albums: [] }
}

function handleMoreSongs(query: string) {
  activeView.value = 'search'
}

async function handleSelectRank(rank: MusicRank) {
  selectedPlaylist.value = null
  selectedUserPlaylist.value = null
  selectedArtist.value = null
  selectedAlbum.value = null
  tracks.value = []
  currentPage.value = 1
  
  tracksLoading.value = true
  const { data } = await getMusicPlaylistTracks({ playlist_id: rank.id, page: 1, page_size: 50 })
  tracksLoading.value = false
  
  tracks.value = data?.items || []
  total.value = data?.total || 0
  tracksHasMore.value = tracks.value.length < total.value
  
  activeView.value = 'playlist-detail'
  selectedPlaylist.value = {
    id: rank.id,
    name: rank.name,
    cover: rank.cover,
    intro: rank.intro || '',
    creator: '',
    play_count: rank.play_count || 0,
    collect_count: 0,
    tags: [],
    list_create_userid: '',
    list_create_listid: '',
    list_create_gid: '',
  }
}

async function handleSelectPlaylist(playlist: MusicPlaylist) {
  selectedPlaylist.value = playlist
  selectedUserPlaylist.value = null
  selectedArtist.value = null
  selectedAlbum.value = null
  currentPage.value = 1
  tracks.value = []
  
  tracksLoading.value = true
  const [tracksData, similarData] = await Promise.all([
    getMusicPlaylistTracks({ playlist_id: playlist.id, page: 1, page_size: 30 }),
    getMusicSimilarPlaylists(playlist.id),
  ])
  tracksLoading.value = false
  
  tracks.value = tracksData.data?.items || []
  total.value = tracksData.data?.total || 0
  tracksHasMore.value = tracks.value.length < total.value
  similarPlaylists.value = (similarData.data?.items || []).slice(0, 6)
  
  activeView.value = 'playlist-detail'
  loadFavoriteCounts(tracks.value)
}

async function handleSelectUserPlaylist(playlist: MusicUserPlaylist) {
  selectedUserPlaylist.value = playlist
  selectedPlaylist.value = null
  selectedArtist.value = null
  selectedAlbum.value = null
  currentPage.value = 1
  tracks.value = []
  
  tracksLoading.value = true
  const { data } = await getMusicUserPlaylistTracks({ list_id: playlist.id, page: 1, page_size: 30 })
  tracksLoading.value = false
  
  tracks.value = data?.items || []
  total.value = data?.total || 0
  tracksHasMore.value = tracks.value.length < total.value
  targetUserPlaylistId.value = playlist.id
  
  activeView.value = 'user-playlist-detail'
  loadFavoriteCounts(tracks.value)
}

async function handleSelectArtistDetail(artist: MusicArtist) {
  selectedArtist.value = artist
  selectedPlaylist.value = null
  selectedUserPlaylist.value = null
  selectedAlbum.value = null
  currentPage.value = 1
  tracks.value = []
  
  tracksLoading.value = true
  const [tracksData, albumsData, videosData] = await Promise.all([
    getMusicArtistTracks({ artist_id: artist.id, page: 1, page_size: 30 }),
    getMusicArtistAlbums({ artist_id: artist.id, page: 1, page_size: 6 }),
    getMusicArtistVideos({ artist_id: artist.id, page: 1, page_size: 4 }),
  ])
  tracksLoading.value = false
  
  tracks.value = tracksData.data?.items || []
  total.value = tracksData.data?.total || 0
  tracksHasMore.value = tracks.value.length < total.value
  artistAlbums.value = albumsData.data?.items || []
  artistVideos.value = videosData.data?.items || []
  artistFollowed.value = false
  
  activeView.value = 'artist-detail'
  loadFavoriteCounts(tracks.value)
}

async function handleSelectArtistFromTrack(track: MusicTrack) {
  if (!track.artist_id) return
  const { data } = await getMusicArtistDetail(track.artist_id)
  if (data) {
    handleSelectArtistDetail(data)
  }
}

async function handleSelectAlbum(album: MusicAlbum) {
  selectedAlbum.value = album
  selectedPlaylist.value = null
  selectedUserPlaylist.value = null
  selectedArtist.value = null
  currentPage.value = 1
  tracks.value = []
  
  tracksLoading.value = true
  const { data } = await getMusicAlbumTracks({ album_id: album.id, page: 1, page_size: 30 })
  tracksLoading.value = false
  
  tracks.value = data?.items || []
  total.value = data?.total || 0
  tracksHasMore.value = tracks.value.length < total.value
  
  activeView.value = 'album-detail'
  loadFavoriteCounts(tracks.value)
}

async function handleSelectAlbumFromTrack(track: MusicTrack) {
  if (!track.album_id) return
  const { data } = await getMusicAlbumDetail(track.album_id)
  if (data) {
    handleSelectAlbum(data)
  }
}

function handleSelectAlbumFromSearch(album: MusicAlbum) {
  handleSelectAlbum(album)
}

function handleSelectArtistFromAlbum() {
  if (selectedAlbum.value?.artist_id) {
    const artist: MusicArtist = {
      id: selectedAlbum.value.artist_id,
      name: selectedAlbum.value.artist,
      avatar: '',
      intro: '',
      song_count: 0,
      album_count: 0,
      fan_count: 0,
    }
    handleSelectArtistDetail(artist)
  }
}

async function handleLoadMoreTracks() {
  if (tracksLoadingMore.value || !tracksHasMore.value) return
  
  currentPage.value++
  tracksLoadingMore.value = true
  
  let data: { items: MusicTrack[]; total: number } | null = null
  
  if (selectedPlaylist.value) {
    const result = await getMusicPlaylistTracks({
      playlist_id: selectedPlaylist.value.id,
      page: currentPage.value,
      page_size: 30,
    })
    data = result.data
  } else if (selectedUserPlaylist.value) {
    const result = await getMusicUserPlaylistTracks({
      list_id: selectedUserPlaylist.value.id,
      page: currentPage.value,
      page_size: 30,
    })
    data = result.data
  } else if (selectedArtist.value) {
    const result = await getMusicArtistTracks({
      artist_id: selectedArtist.value.id,
      page: currentPage.value,
      page_size: 30,
    })
    data = result.data
  } else if (selectedAlbum.value) {
    const result = await getMusicAlbumTracks({
      album_id: selectedAlbum.value.id,
      page: currentPage.value,
      page_size: 30,
    })
    data = result.data
  }
  
  tracksLoadingMore.value = false
  
  if (data?.items?.length) {
    tracks.value = [...tracks.value, ...data.items]
    tracksHasMore.value = tracks.value.length < (data.total || 0)
    loadFavoriteCounts(data.items)
  }
}

async function loadFavoriteCounts(trackList: MusicTrack[]) {
  const ids = trackList.map(t => t.album_audio_id).filter(Boolean)
  if (!ids.length) return
  const { data } = await getMusicFavoriteCount(ids.join(','))
  if (data?.items) {
    const counts: Record<string, number> = { ...favoriteCounts.value }
    for (const item of data.items) {
      if (item.mixsongid) {
        counts[item.mixsongid] = item.count
      }
    }
    favoriteCounts.value = counts
  }
}

function handlePlayAll(shuffle: boolean) {
  store.shuffle = shuffle
  store.playQueue(tracks.value, 0)
}

function handlePlayAllArtistTracks() {
  store.playQueue(tracks.value, 0)
}

function handlePlayAllProfile(shuffle: boolean) {
  const tracksList = activeView.value === 'profile' ? profileHistory.value : profileListenRank.value
  store.shuffle = shuffle
  store.playQueue(tracksList, 0)
}

async function handleCollectPlaylist() {
  if (!selectedPlaylist.value?.id) return
  collectLoading.value = true
  const { error } = await collectMusicPlaylist(selectedPlaylist.value.id)
  collectLoading.value = false
  if (!error) {
    playlistCollected.value = true
    loadUserPlaylists()
  }
}

function handleChangePlaylist(playlist: MusicPlaylist) {
  handleSelectPlaylist(playlist)
}

async function handleFollowArtist() {
  if (!selectedArtist.value?.id) return
  artistFollowLoading.value = true
  const { error } = await followMusicArtist(selectedArtist.value.id)
  artistFollowLoading.value = false
  if (!error) {
    artistFollowed.value = true
  }
}

async function handleUnfollowArtist() {
  if (!selectedArtist.value?.id) return
  artistFollowLoading.value = true
  const { error } = await unfollowMusicArtist(selectedArtist.value.id)
  artistFollowLoading.value = false
  if (!error) {
    artistFollowed.value = false
  }
}

async function handleSelectPlaylistCategory(categoryId: number) {
  selectedPlaylistCategory.value = categoryId
  await loadPlaylists()
}

async function handleLoadMorePlaylists() {
  if (playlistsLoading.value || !playlistHasMore.value) return
  playlistsLoading.value = true
  const { data } = await getMusicPlaylists({
    category_id: selectedPlaylistCategory.value,
    page: 2,
    page_size: 20,
  })
  playlistsLoading.value = false
  if (data?.items?.length) {
    playlists.value = [...playlists.value, ...data.items]
    playlistHasMore.value = data.has_more || false
  }
}

async function handleCreatePlaylist(name: string) {
  const { error } = await createMusicUserPlaylist({ name, is_private: false })
  if (!error) {
    loadUserPlaylists()
  }
}

async function handleAddToPlaylist(track: MusicTrack) {
  if (!targetUserPlaylistId.value) return
  await addMusicUserPlaylistTrack({
    list_id: targetUserPlaylistId.value,
    track: {
      title: track.title,
      hash: track.hash,
      album_id: track.album_id,
      album_audio_id: track.album_audio_id,
    },
  })
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

function handlePlayArtistVideo(video: MusicVideo) {
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

async function loadNewSongs() {
  tracksLoading.value = true
  const { data } = await getMusicNewSongs({ page: 1, page_size: 50 })
  tracksLoading.value = false
  tracks.value = data?.items || []
  total.value = data?.total || 0
}

async function loadNewAlbumsForView() {
  newAlbumsLoading.value = true
  const { data } = await getMusicNewAlbums({ page: 1, page_size: 30 })
  newAlbumsLoading.value = false
  newAlbums.value = data?.items || []
}

async function loadAiRecommend() {
  tracksLoading.value = true
  const { data } = await getMusicAiRecommend({ page_size: 30 })
  tracksLoading.value = false
  tracks.value = data?.items || []
}

async function loadEverydayRecommend() {
  tracksLoading.value = true
  const { data } = await getMusicEverydayRecommend()
  tracksLoading.value = false
  tracks.value = data?.items || []
}

async function handleLoadProfile() {
  activeView.value = 'profile'
  if (!authStatus.value?.logged_in) {
    qrOpen.value = false
    return
  }
  
  profileLoading.value = true
  profileError.value = ''
  
  const { data, error } = await getMusicUserProfile()
  profileLoading.value = false
  
  if (error) {
    profileError.value = error.message
    kugouProfile.value = null
    return
  }
  
  kugouProfile.value = data || null
  loadProfileHistory()
  loadProfileListenRank()
}

async function loadProfileHistory() {
  if (!authStatus.value?.logged_in) return
  profileHistoryLoading.value = true
  const { data } = await getMusicUserHistory()
  profileHistoryLoading.value = false
  profileHistory.value = data?.items || []
}

async function loadProfileListenRank() {
  if (!authStatus.value?.logged_in) return
  profileRankLoading.value = true
  const { data } = await getMusicUserListenRank({ type: profileRankType.value })
  profileRankLoading.value = false
  profileListenRank.value = data?.items || []
}

function handleToggleRankType(type: 0 | 1) {
  profileRankType.value = type
  loadProfileListenRank()
}

async function handleLogout() {
  logoutLoading.value = true
  await logoutMusicUser()
  logoutLoading.value = false
  authStatus.value = null
  kugouProfile.value = null
  userPlaylists.value = []
}

function handleOpenQrLogin() {
  qrOpen.value = true
  qrLoading.value = true
  qrStatus.value = 0
  
  createMusicQrLogin().then(({ data, error }) => {
    qrLoading.value = false
    if (error || !data) {
      Logger.error('Failed to create QR login', error)
      return
    }
    qrLogin.value = data
    startQrPolling()
  })
}

function handleCloseQrLogin() {
  qrOpen.value = false
  stopQrPolling()
}

function startQrPolling() {
  stopQrPolling()
  qrTimer = setInterval(async () => {
    if (!qrLogin.value?.key) return
    const { data } = await checkMusicQrLogin(qrLogin.value.key)
    qrStatus.value = data?.status || 0
    if (data?.logged_in) {
      authStatus.value = data.auth
      stopQrPolling()
      qrOpen.value = false
    }
    if (qrStatus.value === 0 && qrLogin.value) {
      stopQrPolling()
    }
  }, 2000)
}

function stopQrPolling() {
  if (qrTimer) {
    clearInterval(qrTimer)
    qrTimer = null
  }
}

function handleFmNext() {
  fm.next()
}

async function handleFmLike(track: MusicTrack) {
  await fm.like(track, userPlaylists.value)
}

function handleFmDislike() {
  fm.dislike()
}

function handleFmSwitchMode(mode: 'normal' | 'small' | 'peak') {
  fm.switchMode(mode)
}

function handleFmSwitchPool(poolId: string) {
  fm.switchPool(poolId)
}

function handleFmPlayFirst() {
  fm.playFirst()
}
</script>

<style scoped>
.music-page {
  display: flex;
  height: 100%;
}

.music-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
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
  background: hsl(var(--muted-foreground) / 0.3);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--muted-foreground) / 0.5);
}
</style>
