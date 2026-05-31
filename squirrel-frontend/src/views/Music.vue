<template>
  <AppPageShell variant="compact">
    <div class="music-page">
      <!-- Left sidebar navigation for music app -->
      <nav class="music-nav-sidebar">
        <div class="music-nav-brand">
          <AppIcon name="playlistMusic" class="h-5 w-5 text-primary" />
          <h1 class="text-sm font-semibold tracking-wider">我的音乐库</h1>
        </div>

        <div class="music-nav-section">
          <div class="music-nav-label">发现音乐</div>
          <button
            class="music-nav-item"
            :class="{ 'active': activeMode === 'recommend' && !selectedRank && !selectedPlaylist }"
            @click="selectRecommendNav"
          >
            <AppIcon name="playlistMusic" class="h-4 w-4" />
            <span>为您推荐</span>
          </button>
          <button
            class="music-nav-item"
            :class="{ 'active': activeMode === 'rank' }"
            @click="setMusicMode('rank')"
          >
            <AppIcon name="list" class="h-4 w-4" />
            <span>排行榜</span>
          </button>
          <button
            class="music-nav-item"
            :class="{ 'active': activeMode === 'playlist' }"
            @click="setMusicMode('playlist')"
          >
            <AppIcon name="playlistMusic" class="h-4 w-4" />
            <span>热门歌单</span>
          </button>
        </div>

        <div class="music-nav-section">
          <div class="music-nav-label">我的音乐</div>
          <button
            class="music-nav-item"
            :class="{ 'active': trackSource === 'history' }"
            @click="loadUserHistory(false)"
          >
            <AppIcon name="history" class="h-4 w-4" />
            <span>最近播放</span>
          </button>
          <button
            class="music-nav-item"
            :class="{ 'active': trackSource === 'listen_rank' && listenRankType === 0 }"
            @click="loadUserListenRank(0)"
          >
            <AppIcon name="list" class="h-4 w-4" />
            <span>一周排行</span>
          </button>
          <button
            class="music-nav-item"
            :class="{ 'active': trackSource === 'listen_rank' && listenRankType === 1 }"
            @click="loadUserListenRank(1)"
          >
            <AppIcon name="list" class="h-4 w-4" />
            <span>累计排行</span>
          </button>
          <button
            class="music-nav-item"
            :class="{ 'active': trackSource === 'latest_listen' }"
            @click="loadLatestListenSongs"
          >
            <AppIcon name="refresh" class="h-4 w-4" />
            <span>继续播放</span>
          </button>
        </div>

        <div class="music-nav-section">
          <div class="music-nav-label">新建歌单</div>
          <form class="music-playlist-create" @submit.prevent="createUserPlaylist">
            <Input
              v-model="newPlaylistName"
              class="h-7 text-xs border-none bg-muted/40"
              placeholder="歌单名称..."
            />
            <div class="music-playlist-create-footer">
              <label class="music-private-toggle">
                <input v-model="newPlaylistPrivate" type="checkbox" />
                <span>私密</span>
              </label>
              <button class="music-row-action" :disabled="!newPlaylistName.trim()" title="新建歌单" type="submit">
                <AppIcon name="plus" class="h-3.5 w-3.5" />
              </button>
            </div>
          </form>
        </div>

        <div class="music-nav-section" v-if="userPlaylists.length">
          <div class="music-nav-label">我的歌单</div>
          <button
            v-for="playlist in userPlaylists"
            :key="playlist.id"
            class="music-nav-item"
            :class="{ 'active': selectedUserPlaylist?.id === playlist.id && trackSource === 'user_playlist' }"
            @click="selectUserPlaylist(playlist)"
          >
            <AppIcon name="playlistMusic" class="h-4 w-4" />
            <span class="truncate">{{ playlist.name }}</span>
          </button>
        </div>
      </nav>

      <section class="music-main">
        <header class="music-header">
          <div class="min-w-0">
            <h1 class="truncate text-sm font-semibold tracking-wide text-muted-foreground">{{ resultSummary }}</h1>
          </div>
          <div class="music-header-actions">
            <Button variant="outline" class="h-8 rounded-md px-3 text-xs" @click="openQrLogin">
              <AppIcon name="user" class="h-3.5 w-3.5" />
              {{ authStatus?.logged_in ? '已登录' : '扫码登录' }}
            </Button>
            <form class="music-search" @submit.prevent="submitSearch">
              <Input
                v-model="query"
                class="h-8 border-none bg-muted/50 text-xs focus-visible:ring-1"
                placeholder="搜索歌曲、歌手、专辑"
              />
              <Button type="submit" class="h-8 rounded-md px-3 text-xs" :disabled="loading || !query.trim()">
                <AppIcon v-if="loading" name="loadingSpinner" class="h-3.5 w-3.5 animate-spin" />
                <AppIcon v-else name="search" class="h-3.5 w-3.5" />
                搜索
              </Button>
            </form>
          </div>
        </header>

        <div class="music-content custom-scrollbar" @scroll="handleContentScroll">
          <!-- Ranks Grid View -->
          <div v-if="activeMode === 'rank' && !selectedRank" class="music-discovery-grid">
            <h3 class="text-sm font-semibold mb-3">官方排行榜</h3>
            <div class="music-grid">
              <div
                v-for="rank in ranks"
                :key="rank.id"
                class="music-grid-card"
                @click="selectRank(rank)"
              >
                <div class="music-source-cover-wrap">
                  <img v-if="rank.cover" :src="rank.cover" alt="" class="music-source-cover" />
                  <div v-else class="music-source-cover">
                    <AppIcon name="playlistMusic" class="h-6 w-6 text-muted-foreground" />
                  </div>
                  <div class="music-source-play-overlay">
                    <AppIcon name="play" class="h-6 w-6 text-primary-foreground fill-current" />
                  </div>
                </div>
                <span class="music-grid-card-title">{{ rank.name }}</span>
                <span class="music-grid-card-subtitle">{{ rank.update_frequency || '排行榜' }}</span>
              </div>
            </div>
          </div>

          <!-- Playlists Grid View -->
          <div v-else-if="activeMode === 'playlist' && !selectedPlaylist" class="music-discovery-grid">
            <h3 class="text-sm font-semibold mb-3">热门精品歌单</h3>
            <div class="music-grid">
              <div
                v-for="playlist in playlists"
                :key="playlist.id"
                class="music-grid-card"
                @click="selectPlaylist(playlist)"
              >
                <div class="music-source-cover-wrap">
                  <img v-if="playlist.cover" :src="playlist.cover" alt="" class="music-source-cover" />
                  <div v-else class="music-source-cover">
                    <AppIcon name="playlistMusic" class="h-6 w-6 text-muted-foreground" />
                  </div>
                  <div class="music-source-play-overlay">
                    <AppIcon name="play" class="h-6 w-6 text-primary-foreground fill-current" />
                  </div>
                </div>
                <span class="music-grid-card-title">{{ playlist.name }}</span>
                <span class="music-grid-card-subtitle">{{ playlist.creator || '歌单' }}</span>
              </div>
            </div>
            <div class="flex justify-center mt-6" v-if="playlistHasMore">
              <Button variant="outline" class="h-8 text-xs px-4" :disabled="discoveryLoading" @click="loadMorePlaylists">
                <AppIcon v-if="discoveryLoading" name="loadingSpinner" class="h-3.5 w-3.5 animate-spin" />
                加载更多歌单
              </Button>
            </div>
          </div>

          <!-- Normal Track List Area -->
          <div v-else class="music-tracks-container">
            <!-- Sleek Header Banner for Playlists -->
            <header class="music-playlist-header" v-if="selectedRank || selectedPlaylist || selectedUserPlaylist || selectedArtist || selectedAlbum || trackSource === 'history' || trackSource === 'listen_rank' || trackSource === 'latest_listen' || trackSource === 'search' || trackSource === 'recommend'">
              <div class="music-playlist-header-cover">
                <img v-if="selectedRank?.cover" :src="selectedRank.cover" alt="" />
                <img v-else-if="selectedPlaylist?.cover" :src="selectedPlaylist.cover" alt="" />
                <img v-else-if="selectedUserPlaylist?.cover" :src="selectedUserPlaylist.cover" alt="" />
                <img v-else-if="selectedArtist?.avatar" :src="selectedArtist.avatar" alt="" />
                <img v-else-if="selectedAlbum?.cover" :src="selectedAlbum.cover" alt="" />
                <div v-else class="music-playlist-header-placeholder">
                  <AppIcon name="playlistMusic" class="h-10 w-10 text-muted-foreground" />
                </div>
              </div>
              <div class="music-playlist-header-info">
                <div class="text-[0.6875rem] font-bold uppercase tracking-wider text-primary">{{ trackSourceText }}</div>
                <h1 class="text-xl font-bold mt-1 text-foreground leading-tight">{{ selectedSourceTitle || '为您推荐' }}</h1>
                <p class="text-xs text-muted-foreground mt-2">{{ total }} 首歌曲 · 酷狗音乐提供</p>
                <p v-if="selectedArtist?.intro" class="music-detail-intro">{{ selectedArtist.intro }}</p>
                <p v-else-if="selectedAlbum?.intro" class="music-detail-intro">{{ selectedAlbum.intro }}</p>
                <div v-if="selectedAlbum" class="music-detail-meta">
                  <button v-if="selectedAlbum.artist_id" class="music-link" @click="selectAlbumArtist">
                    {{ selectedAlbum.artist }}
                  </button>
                  <span v-if="selectedAlbum.publish_date">{{ selectedAlbum.publish_date }}</span>
                  <span v-if="selectedAlbum.type">{{ selectedAlbum.type }}</span>
                </div>
                
                <div class="music-playlist-header-actions mt-4">
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <button class="music-chip" title="播放全部" @click="playAll(false)">
                      <AppIcon name="play" class="h-3.5 w-3.5" />
                      播放全部
                    </button>
                    <button class="music-chip" :class="{ 'music-chip--active': store.shuffle }" title="随机播放" @click="playAll(true)">
                      <AppIcon name="shuffle" class="h-3.5 w-3.5" />
                      随机
                    </button>
                    <button v-if="selectedPlaylist" class="music-chip" title="收藏歌单" @click="collectSelectedPlaylist">
                      <AppIcon name="heart" class="h-3.5 w-3.5" />
                      收藏
                    </button>
                    <button v-if="selectedUserPlaylist" class="music-chip music-chip--danger" title="删除歌单" @click="deleteSelectedUserPlaylist">
                      <AppIcon name="trash" class="h-3.5 w-3.5" />
                      删除
                    </button>
                    <div class="flex items-center gap-1.5 ml-auto" v-if="userPlaylists.length">
                      <select v-model="targetUserPlaylistId" class="music-inline-select">
                        <option value="">快速加入到歌单</option>
                        <option v-for="playlist in userPlaylists" :key="playlist.id" :value="playlist.id">
                          {{ playlist.name }}
                        </option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            </header>

            <div v-if="selectedArtist && artistAlbums.length" class="music-album-strip">
              <button
                v-for="album in artistAlbums"
                :key="album.id"
                class="music-album-card"
                @click="selectAlbumSummary(album)"
              >
                <img v-if="album.cover" :src="album.cover" alt="" />
                <div v-else class="music-album-placeholder">
                  <AppIcon name="playlistMusic" class="h-5 w-5 text-muted-foreground" />
                </div>
                <span>{{ album.name }}</span>
              </button>
            </div>

            <div v-if="trackSource === 'search' && (searchArtists.length || searchAlbums.length)" class="music-search-sections">
              <section v-if="searchArtists.length" class="music-search-section">
                <h2>歌手</h2>
                <div class="music-result-grid">
                  <button
                    v-for="artist in searchArtists"
                    :key="artist.id"
                    class="music-result-card"
                    @click="selectArtistSummary(artist)"
                  >
                    <img v-if="artist.avatar" :src="artist.avatar" alt="" />
                    <div v-else class="music-result-placeholder">
                      <AppIcon name="user" class="h-5 w-5 text-muted-foreground" />
                    </div>
                    <span>{{ artist.name }}</span>
                    <small>{{ artist.song_count }} 首歌曲</small>
                  </button>
                </div>
              </section>
              <section v-if="searchAlbums.length" class="music-search-section">
                <h2>专辑</h2>
                <div class="music-result-grid">
                  <button
                    v-for="album in searchAlbums"
                    :key="album.id"
                    class="music-result-card"
                    @click="selectAlbumSummary(album)"
                  >
                    <img v-if="album.cover" :src="album.cover" alt="" />
                    <div v-else class="music-result-placeholder">
                      <AppIcon name="playlistMusic" class="h-5 w-5 text-muted-foreground" />
                    </div>
                    <span>{{ album.name }}</span>
                    <small>{{ album.artist }}</small>
                  </button>
                </div>
              </section>
            </div>

            <div v-if="loading && tracks.length === 0" class="music-list">
              <div v-for="index in 8" :key="index" class="music-skeleton" />
            </div>

            <div v-else-if="error" class="music-empty">
              <AppIcon name="warning" class="h-9 w-9 text-destructive/60" />
              <h2 class="mt-4 text-sm font-semibold">加载失败</h2>
              <p class="mt-1 max-w-md text-sm text-muted-foreground">{{ error }}</p>
            </div>

            <div v-else-if="searched && tracks.length === 0" class="music-empty">
              <AppIcon name="playlistMusic" class="h-9 w-9 text-muted-foreground/30" />
              <h2 class="mt-4 text-sm font-semibold">没有结果</h2>
            </div>

            <div v-else class="music-list">
              <!-- Clean aligned header row -->
              <div class="music-row music-row--header text-[0.6875rem] uppercase font-bold tracking-wider text-muted-foreground/50 border-b border-border/15 pb-2 mb-1.5 pointer-events-none select-none">
                <div class="text-center">#</div>
                <div></div> <!-- Cover space -->
                <div>歌曲标题</div>
                <div class="hidden md:block">专辑</div>
                <div class="text-right pr-4 hidden sm:block">时长</div>
                <div></div> <!-- Actions space -->
              </div>

              <article
                v-for="(track, index) in tracks"
                :key="trackKey(track, index)"
                class="music-row"
                :class="{ 'music-row--active': isCurrentTrack(track) }"
                @click="store.playTrack(track)"
                @dblclick="store.playTrack(track)"
              >
                <div class="music-row-index">
                  <span v-if="isCurrentTrack(track) && store.playing" class="music-row-equalizer">
                    <span class="eq-bar" /><span class="eq-bar" /><span class="eq-bar" />
                  </span>
                  <span v-else class="music-row-number">{{ index + 1 }}</span>
                  <AppIcon name="play" class="music-row-play h-4 w-4 fill-current" />
                </div>
                <div class="music-cover">
                  <img v-if="track.cover" :src="track.cover" alt="" class="h-full w-full object-cover" />
                  <AppIcon v-else name="playlistMusic" class="h-5 w-5 text-muted-foreground" />
                </div>
                <div class="min-w-0">
                  <div class="truncate text-sm font-medium" :class="{ 'text-primary': isCurrentTrack(track) }">
                    {{ track.title || '未知歌曲' }}
                  </div>
                  <button
                    class="music-link mt-1 block truncate text-xs"
                    :disabled="!track.artist_id"
                    @click.stop="selectArtist(track)"
                  >
                    {{ track.artist || '未知歌手' }}
                  </button>
                </div>
                <button
                  class="music-link hidden truncate text-sm md:block"
                  :disabled="!track.album_id"
                  @click.stop="selectAlbum(track)"
                >
                  {{ track.album }}
                </button>
                <div class="music-row-side hidden text-right text-sm tabular-nums text-muted-foreground sm:block">
                  <span>{{ formatDuration(track.duration) }}</span>
                  <span v-if="favoriteCounts[track.album_audio_id]" class="music-favorite-count">
                    <AppIcon name="heart" class="h-3 w-3" />
                    {{ formatCompactCount(favoriteCounts[track.album_audio_id]) }}
                  </span>
                </div>
                <div class="music-row-actions">
                  <button
                    class="music-row-action"
                    :disabled="!targetUserPlaylistId"
                    title="加入所选歌单"
                    @click.stop="addTrackToSelectedPlaylist(track)"
                  >
                    <AppIcon name="addToPlaylist" class="h-3.5 w-3.5" />
                  </button>
                  <button
                    v-if="trackSource === 'user_playlist' && track.file_id"
                    class="music-row-action"
                    title="从歌单删除"
                    @click.stop="removeTrackFromSelectedPlaylist(track)"
                  >
                    <AppIcon name="close" class="h-3.5 w-3.5" />
                  </button>
                </div>
              </article>

              <div v-if="hasMore" class="flex justify-center pt-3">
                <Button variant="outline" class="h-9 rounded-md px-4 text-xs" :disabled="loading" @click="loadMoreSearch">
                  <AppIcon v-if="loading" name="loadingSpinner" class="h-3.5 w-3.5 animate-spin" />
                  加载更多
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>



      <div v-if="qrOpen" class="music-qr-modal" @click.self="closeQrLogin">
        <section class="music-qr-panel">
          <header class="flex items-center justify-between gap-3 border-b border-border/50 px-4 py-3">
            <div class="min-w-0">
              <h2 class="truncate text-sm font-semibold">酷狗扫码登录</h2>
              <p class="mt-0.5 text-xs text-muted-foreground">{{ qrStatusText }}</p>
            </div>
            <Button variant="ghost" size="icon" class="h-8 w-8 rounded-md" @click="closeQrLogin">
              <AppIcon name="close" class="h-4 w-4" />
            </Button>
          </header>

          <div class="flex flex-col items-center gap-4 p-5">
            <div class="music-qr-image">
              <img v-if="qrLogin?.base64" :src="qrLogin.base64" alt="KuGou login QR code" class="h-full w-full" />
              <AppIcon v-else name="loadingSpinner" class="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
            <div class="flex gap-2">
              <Button variant="outline" class="h-9 rounded-md px-3" :disabled="qrLoading" @click="openQrLogin">
                <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': qrLoading }" />
                刷新
              </Button>
              <Button class="h-9 rounded-md px-3" :disabled="!qrLogin?.url" @click="openQrUrl">
                <AppIcon name="externalLink" class="h-4 w-4" />
                打开
              </Button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  collectMusicPlaylist,
  checkMusicQrLogin,
  createMusicUserPlaylist,
  createMusicQrLogin,
  deleteMusicUserPlaylist,
  getMusicAuthStatus,
  addMusicUserPlaylistTrack,
  getMusicAlbumDetail,
  getMusicAlbumTracks,
  getMusicArtistAlbums,
  getMusicArtistDetail,
  getMusicArtistTracks,
  getMusicFavoriteCount,
  getMusicPlaylistTracks,
  getMusicPlaylists,
  getMusicRankTracks,
  getMusicRanks,
  getMusicLatestListenSongs,
  getMusicUserHistory,
  getMusicUserListenRank,
  getMusicUserPlaylistTracks,
  getMusicUserPlaylists,
  removeMusicUserPlaylistTracks,
  searchMusic,
  searchMusicAlbums,
  searchMusicArtists,
  type MusicAlbum,
  type MusicArtist,
  type MusicAuthStatus,
  type MusicPlaylist,
  type MusicQrLogin,
  type MusicRank,
  type MusicTrack,
  type MusicUserPlaylist,
} from '@/api/music'
import { useMusicPlayerStore } from '@/stores/musicPlayer'
import { Logger } from '@/utils/logger'

const store = useMusicPlayerStore()

type MusicMode = 'recommend' | 'rank' | 'playlist' | 'mine'
type TrackSource = 'recommend' | 'search' | 'rank' | 'playlist' | 'user_playlist' | 'history' | 'listen_rank' | 'latest_listen' | 'artist_detail' | 'album_detail'

const query = ref('')
const tracks = ref<MusicTrack[]>([])
const ranks = ref<MusicRank[]>([])
const playlists = ref<MusicPlaylist[]>([])
const userPlaylists = ref<MusicUserPlaylist[]>([])
const artistAlbums = ref<MusicAlbum[]>([])
const searchArtists = ref<MusicArtist[]>([])
const searchAlbums = ref<MusicAlbum[]>([])
const favoriteCounts = ref<Record<string, number>>({})
const loading = ref(false)
const discoveryLoading = ref(false)
const searched = ref(false)
const error = ref('')
const quality = ref(store.quality)
const activeMode = ref<MusicMode>('recommend')
const trackSource = ref<TrackSource>('recommend')
const selectedSourceTitle = ref('')
const selectedRank = ref<MusicRank | null>(null)
const selectedPlaylist = ref<MusicPlaylist | null>(null)
const selectedUserPlaylist = ref<MusicUserPlaylist | null>(null)
const selectedArtist = ref<MusicArtist | null>(null)
const selectedAlbum = ref<MusicAlbum | null>(null)
const targetUserPlaylistId = ref('')
const newPlaylistName = ref('')
const newPlaylistPrivate = ref(false)
const userHistoryBp = ref('')
const listenRankType = ref<0 | 1>(0)
const currentPage = ref(1)
const playlistPage = ref(1)
const playlistHasMore = ref(false)
const pageSize = 30
const loadMoreOffset = 240
const total = ref(0)
const authStatus = ref<MusicAuthStatus | null>(null)
const qrOpen = ref(false)
const qrLoading = ref(false)
const qrLogin = ref<MusicQrLogin | null>(null)
const qrStatus = ref(0)
let qrTimer: ReturnType<typeof setInterval> | null = null

const resultSummary = computed(() => {
  if (loading.value) return '搜索中'
  if (selectedSourceTitle.value) return `${selectedSourceTitle.value} · ${tracks.value.length} / ${total.value} 首`
  if (!searched.value) {
    if (tracks.value.length > 0) return `推荐 · ${total.value} 首`
    return '酷狗音乐 · 试试搜索吧'
  }
  return `共 ${total.value} 首`
})

const canStep = computed(() => store.queue.length > 1)
const hasMore = computed(() => {
  if (trackSource.value === 'history') return !!userHistoryBp.value
  return ['search', 'rank', 'playlist', 'user_playlist', 'artist_detail', 'album_detail'].includes(trackSource.value) && tracks.value.length < total.value
})

const repeatTitle = computed(() => {
  if (store.repeat === 'all') return '列表循环'
  if (store.repeat === 'one') return '单曲循环'
  return '顺序播放'
})

const volumeIcon = computed(() => {
  if (store.volume === 0) return 'volumeOff'
  if (store.volume < 0.4) return 'volumeLow'
  return 'volumeHigh'
})

const qrStatusText = computed(() => {
  if (qrLoading.value) return '二维码生成中'
  if (qrStatus.value === 4) return '登录成功'
  if (qrStatus.value === 2) return '已扫码，请在手机上确认'
  if (qrStatus.value === 0 && qrLogin.value) return '二维码已过期，请刷新'
  return '使用酷狗音乐 App 扫码'
})

const trackSourceText = computed(() => {
  if (trackSource.value === 'recommend') return '酷狗推荐'
  if (trackSource.value === 'search') return '搜索结果'
  if (trackSource.value === 'rank') return '酷狗音乐排行榜'
  if (trackSource.value === 'playlist') return '酷狗音乐热门歌单'
  if (trackSource.value === 'user_playlist') return '我的自建歌单'
  if (trackSource.value === 'history') return '我最近听过的歌'
  if (trackSource.value === 'listen_rank') return '听歌排行记录'
  if (trackSource.value === 'latest_listen') return '设备上次继续播放'
  if (trackSource.value === 'artist_detail') return '歌手详情'
  if (trackSource.value === 'album_detail') return '专辑详情'
  return '音乐库'
})

function selectRecommendNav() {
  selectedRank.value = null
  selectedPlaylist.value = null
  selectedUserPlaylist.value = null
  selectedArtist.value = null
  selectedAlbum.value = null
  artistAlbums.value = []
  setMusicMode('recommend')
}

let previousVolume = 0.7

onMounted(() => {
  void loadAuthStatus()
  void loadSuggestions()
  void loadRanks()
  void loadPlaylists(false)
  void loadUserPlaylists()
})

onUnmounted(() => {
  stopQrPolling()
})

function isCurrentTrack(track: MusicTrack): boolean {
  return store.currentTrack?.hash === track.hash
}

async function loadSuggestions() {
  loading.value = true
  error.value = ''
  const { data, error: err } = await searchMusic({ query: '新歌', page: 1, page_size: pageSize })
  loading.value = false
  if (err) {
    Logger.error('Failed to load music suggestions', err)
    return
  }
  if (data?.items?.length) {
    tracks.value = data.items
    total.value = data.total || data.items.length
    trackSource.value = 'recommend'
    selectedSourceTitle.value = ''
    void loadFavoriteCounts(tracks.value)
  }
}

const submitSearch = async () => {
  const keyword = query.value.trim()
  if (!keyword || loading.value) return

  activeMode.value = 'recommend'
  trackSource.value = 'search'
  selectedRank.value = null
  selectedPlaylist.value = null
  selectedUserPlaylist.value = null
  selectedArtist.value = null
  selectedAlbum.value = null
  artistAlbums.value = []
  searchArtists.value = []
  searchAlbums.value = []
  selectedSourceTitle.value = `搜索：${keyword}`
  currentPage.value = 1
  await Promise.all([
    searchPage(keyword, currentPage.value, false),
    loadSearchOverview(keyword),
  ])
}

async function loadSearchOverview(keyword: string) {
  const [artistResult, albumResult] = await Promise.all([
    searchMusicArtists({ query: keyword, page: 1, page_size: 6 }),
    searchMusicAlbums({ query: keyword, page: 1, page_size: 8 }),
  ])
  if (artistResult.error) {
    Logger.error('Failed to search music artists', artistResult.error)
    searchArtists.value = []
  } else {
    searchArtists.value = artistResult.data?.items || []
  }
  if (albumResult.error) {
    Logger.error('Failed to search music albums', albumResult.error)
    searchAlbums.value = []
  } else {
    searchAlbums.value = albumResult.data?.items || []
  }
}

async function loadMoreSearch() {
  if (loading.value || !hasMore.value) return
  currentPage.value += 1
  if (trackSource.value === 'search') {
    const keyword = query.value.trim()
    if (keyword) await searchPage(keyword, currentPage.value, true)
  } else if (trackSource.value === 'rank' && selectedRank.value) {
    await loadRankTracks(selectedRank.value, currentPage.value, true)
  } else if (trackSource.value === 'playlist' && selectedPlaylist.value) {
    await loadPlaylistTracks(selectedPlaylist.value, currentPage.value, true)
  } else if (trackSource.value === 'user_playlist' && selectedUserPlaylist.value) {
    await loadUserPlaylistTracks(selectedUserPlaylist.value, currentPage.value, true)
  } else if (trackSource.value === 'artist_detail' && selectedArtist.value) {
    await loadArtistTracks(selectedArtist.value.id, currentPage.value, true)
  } else if (trackSource.value === 'album_detail' && selectedAlbum.value) {
    await loadAlbumTracks(selectedAlbum.value.id, currentPage.value, true)
  } else if (trackSource.value === 'history') {
    await loadUserHistory(true)
  }
}

async function searchPage(keyword: string, page: number, append: boolean) {
  loading.value = true
  searched.value = true
  error.value = ''

  const { data, error: requestError } = await searchMusic({ query: keyword, page, page_size: pageSize })
  loading.value = false

  if (requestError) {
    error.value = requestError.message
    tracks.value = []
    total.value = 0
    Logger.error('Failed to search music', requestError)
    return
  }

  const items = data?.items || []
  tracks.value = append ? [...tracks.value, ...items] : items
  total.value = data?.total || tracks.value.length
  void loadFavoriteCounts(tracks.value)
}

async function setMusicMode(mode: MusicMode) {
  activeMode.value = mode
  if (mode === 'recommend') {
    selectedRank.value = null
    selectedPlaylist.value = null
    selectedUserPlaylist.value = null
    selectedArtist.value = null
    selectedAlbum.value = null
    artistAlbums.value = []
    selectedSourceTitle.value = ''
    await loadSuggestions()
  } else if (mode === 'rank' && ranks.value.length === 0) {
    await loadRanks()
  } else if (mode === 'playlist' && playlists.value.length === 0) {
    await loadPlaylists(false)
  } else if (mode === 'mine') {
    if (userPlaylists.value.length === 0) await loadUserPlaylists()
    if (trackSource.value !== 'user_playlist' && trackSource.value !== 'history') await loadUserHistory(false)
  }
}

async function loadRanks() {
  discoveryLoading.value = true
  const { data, error: requestError } = await getMusicRanks()
  discoveryLoading.value = false
  if (requestError) {
    Logger.error('Failed to load music ranks', requestError)
    return
  }
  ranks.value = data?.items || []
}

async function selectRank(rank: MusicRank) {
  selectedRank.value = rank
  selectedPlaylist.value = null
  selectedUserPlaylist.value = null
  selectedArtist.value = null
  selectedAlbum.value = null
  artistAlbums.value = []
  trackSource.value = 'rank'
  selectedSourceTitle.value = rank.name
  currentPage.value = 1
  await loadRankTracks(rank, currentPage.value, false)
}

async function loadRankTracks(rank: MusicRank, page: number, append: boolean) {
  loading.value = true
  error.value = ''
  const { data, error: requestError } = await getMusicRankTracks({
    rank_id: rank.id,
    rank_cid: rank.rank_cid || undefined,
    page,
    page_size: pageSize,
  })
  loading.value = false
  if (requestError) {
    error.value = requestError.message
    Logger.error('Failed to load music rank tracks', requestError)
    return
  }
  const items = data?.items || []
  tracks.value = append ? [...tracks.value, ...items] : items
  total.value = data?.total || tracks.value.length
  void loadFavoriteCounts(tracks.value)
}

async function loadPlaylists(append: boolean) {
  discoveryLoading.value = true
  const { data, error: requestError } = await getMusicPlaylists({
    category_id: 0,
    page: playlistPage.value,
    page_size: 12,
  })
  discoveryLoading.value = false
  if (requestError) {
    Logger.error('Failed to load music playlists', requestError)
    return
  }
  const items = data?.items || []
  playlists.value = append ? [...playlists.value, ...items] : items
  playlistHasMore.value = data?.has_more === true
}

async function loadMorePlaylists() {
  if (discoveryLoading.value || !playlistHasMore.value) return
  playlistPage.value += 1
  await loadPlaylists(true)
}

function handleContentScroll(event: Event) {
  const target = event.currentTarget
  if (!(target instanceof HTMLElement)) return
  const distanceToBottom = target.scrollHeight - target.scrollTop - target.clientHeight
  if (distanceToBottom > loadMoreOffset) return
  if (activeMode.value === 'playlist' && !selectedPlaylist.value) {
    void loadMorePlaylists()
    return
  }
  void loadMoreSearch()
}

async function selectPlaylist(playlist: MusicPlaylist) {
  selectedPlaylist.value = playlist
  selectedRank.value = null
  selectedUserPlaylist.value = null
  selectedArtist.value = null
  selectedAlbum.value = null
  artistAlbums.value = []
  trackSource.value = 'playlist'
  selectedSourceTitle.value = playlist.name
  currentPage.value = 1
  await loadPlaylistTracks(playlist, currentPage.value, false)
}

async function loadPlaylistTracks(playlist: MusicPlaylist, page: number, append: boolean) {
  loading.value = true
  error.value = ''
  const { data, error: requestError } = await getMusicPlaylistTracks({
    playlist_id: playlist.id,
    page,
    page_size: pageSize,
  })
  loading.value = false
  if (requestError) {
    error.value = requestError.message
    Logger.error('Failed to load music playlist tracks', requestError)
    return
  }
  const items = data?.items || []
  tracks.value = append ? [...tracks.value, ...items] : items
  total.value = data?.total || tracks.value.length
  void loadFavoriteCounts(tracks.value)
}

async function loadUserPlaylists() {
  const { data, error: requestError } = await getMusicUserPlaylists({ page: 1, page_size: 30 })
  if (requestError) {
    Logger.error('Failed to load music user playlists', requestError)
    return
  }
  userPlaylists.value = data?.items || []
  if (!targetUserPlaylistId.value && userPlaylists.value.length) {
    targetUserPlaylistId.value = userPlaylists.value[0].id
  }
}

async function createUserPlaylist() {
  const name = newPlaylistName.value.trim()
  if (!name) return
  const { error: requestError } = await createMusicUserPlaylist({
    name,
    is_private: newPlaylistPrivate.value,
  })
  if (requestError) {
    error.value = requestError.message
    Logger.error('Failed to create music user playlist', requestError)
    return
  }
  newPlaylistName.value = ''
  newPlaylistPrivate.value = false
  await loadUserPlaylists()
}

async function selectUserPlaylist(playlist: MusicUserPlaylist) {
  selectedUserPlaylist.value = playlist
  selectedRank.value = null
  selectedPlaylist.value = null
  selectedArtist.value = null
  selectedAlbum.value = null
  artistAlbums.value = []
  targetUserPlaylistId.value = playlist.id
  trackSource.value = 'user_playlist'
  selectedSourceTitle.value = playlist.name
  currentPage.value = 1
  await loadUserPlaylistTracks(playlist, currentPage.value, false)
}

async function collectSelectedPlaylist() {
  if (!selectedPlaylist.value?.id) return
  const { error: requestError } = await collectMusicPlaylist(selectedPlaylist.value.id)
  if (requestError) {
    error.value = requestError.message
    Logger.error('Failed to collect music playlist', requestError)
    return
  }
  await loadUserPlaylists()
}

async function deleteSelectedUserPlaylist() {
  if (!selectedUserPlaylist.value?.id) return
  if (!window.confirm(`删除歌单「${selectedUserPlaylist.value.name}」？`)) return
  const deletedId = selectedUserPlaylist.value.id
  const { error: requestError } = await deleteMusicUserPlaylist(deletedId)
  if (requestError) {
    error.value = requestError.message
    Logger.error('Failed to delete music user playlist', requestError)
    return
  }
  selectedUserPlaylist.value = null
  selectedArtist.value = null
  selectedAlbum.value = null
  artistAlbums.value = []
  if (targetUserPlaylistId.value === deletedId) {
    targetUserPlaylistId.value = ''
  }
  tracks.value = []
  total.value = 0
  selectedSourceTitle.value = ''
  await loadUserPlaylists()
}

async function loadUserPlaylistTracks(playlist: MusicUserPlaylist, page: number, append: boolean) {
  loading.value = true
  searched.value = true
  error.value = ''
  const { data, error: requestError } = await getMusicUserPlaylistTracks({
    list_id: playlist.id,
    page,
    page_size: pageSize,
  })
  loading.value = false
  if (requestError) {
    error.value = requestError.message
    Logger.error('Failed to load music user playlist tracks', requestError)
    return
  }
  const items = data?.items || []
  tracks.value = append ? [...tracks.value, ...items] : items
  total.value = data?.total || tracks.value.length
  void loadFavoriteCounts(tracks.value)
}

async function selectArtist(track: MusicTrack) {
  if (!track.artist_id) return
  loading.value = true
  searched.value = true
  error.value = ''
  const { data, error: requestError } = await getMusicArtistDetail(track.artist_id)
  if (requestError || !data) {
    loading.value = false
    error.value = requestError?.message || 'artist detail is empty'
    Logger.error('Failed to load music artist detail', requestError)
    return
  }
  selectedArtist.value = data
  selectedAlbum.value = null
  selectedRank.value = null
  selectedPlaylist.value = null
  selectedUserPlaylist.value = null
  activeMode.value = 'recommend'
  trackSource.value = 'artist_detail'
  selectedSourceTitle.value = data.name
  currentPage.value = 1
  await loadArtistAlbums(data.id)
  await loadArtistTracks(data.id, currentPage.value, false)
}

async function selectArtistSummary(artist: MusicArtist) {
  await selectArtist({
    id: '',
    title: '',
    artist: artist.name,
    artist_id: artist.id,
    album: '',
    hash: '',
    album_id: '',
    album_audio_id: '',
    duration: 0,
    cover: '',
  })
}

async function selectAlbumArtist() {
  if (!selectedAlbum.value?.artist_id) return
  await selectArtist({
    id: '',
    title: '',
    artist: selectedAlbum.value.artist,
    artist_id: selectedAlbum.value.artist_id,
    album: '',
    hash: '',
    album_id: '',
    album_audio_id: '',
    duration: 0,
    cover: '',
  })
}

async function loadArtistTracks(artistId: string, page: number, append: boolean) {
  loading.value = true
  error.value = ''
  const { data, error: requestError } = await getMusicArtistTracks({
    artist_id: artistId,
    page,
    page_size: pageSize,
  })
  loading.value = false
  if (requestError) {
    error.value = requestError.message
    Logger.error('Failed to load music artist tracks', requestError)
    return
  }
  const items = data?.items || []
  tracks.value = append ? [...tracks.value, ...items] : items
  total.value = data?.total || tracks.value.length
  void loadFavoriteCounts(tracks.value)
}

async function loadArtistAlbums(artistId: string) {
  const { data, error: requestError } = await getMusicArtistAlbums({
    artist_id: artistId,
    page: 1,
    page_size: 12,
  })
  if (requestError) {
    Logger.error('Failed to load music artist albums', requestError)
    artistAlbums.value = []
    return
  }
  artistAlbums.value = data?.items || []
}

async function selectAlbum(track: MusicTrack) {
  if (!track.album_id) return
  await loadAlbumDetail(track.album_id)
}

async function selectAlbumSummary(album: MusicAlbum) {
  await loadAlbumDetail(album.id)
}

async function loadAlbumDetail(albumId: string) {
  loading.value = true
  searched.value = true
  error.value = ''
  const { data, error: requestError } = await getMusicAlbumDetail(albumId)
  if (requestError || !data) {
    loading.value = false
    error.value = requestError?.message || 'album detail is empty'
    Logger.error('Failed to load music album detail', requestError)
    return
  }
  selectedAlbum.value = data
  selectedArtist.value = null
  artistAlbums.value = []
  selectedRank.value = null
  selectedPlaylist.value = null
  selectedUserPlaylist.value = null
  activeMode.value = 'recommend'
  trackSource.value = 'album_detail'
  selectedSourceTitle.value = data.name
  currentPage.value = 1
  await loadAlbumTracks(data.id, currentPage.value, false)
}

async function loadAlbumTracks(albumId: string, page: number, append: boolean) {
  loading.value = true
  error.value = ''
  const { data, error: requestError } = await getMusicAlbumTracks({
    album_id: albumId,
    page,
    page_size: pageSize,
  })
  loading.value = false
  if (requestError) {
    error.value = requestError.message
    Logger.error('Failed to load music album tracks', requestError)
    return
  }
  const items = data?.items || []
  tracks.value = append ? [...tracks.value, ...items] : items
  total.value = data?.total || tracks.value.length
  void loadFavoriteCounts(tracks.value)
}

async function loadUserHistory(append: boolean) {
  loading.value = true
  searched.value = true
  error.value = ''
  if (!append) currentPage.value = 1
  selectedSourceTitle.value = '最近播放'
  trackSource.value = 'history'
  selectedUserPlaylist.value = null
  selectedRank.value = null
  selectedPlaylist.value = null
  selectedArtist.value = null
  selectedAlbum.value = null
  artistAlbums.value = []
  const { data, error: requestError } = await getMusicUserHistory({ bp: append ? userHistoryBp.value : undefined })
  loading.value = false
  if (requestError) {
    error.value = requestError.message
    Logger.error('Failed to load music user history', requestError)
    return
  }
  const items = data?.items || []
  tracks.value = append ? [...tracks.value, ...items] : items
  total.value = tracks.value.length
  userHistoryBp.value = data?.bp || ''
  void loadFavoriteCounts(tracks.value)
}

async function loadUserListenRank(type: 0 | 1) {
  loading.value = true
  searched.value = true
  error.value = ''
  listenRankType.value = type
  selectedSourceTitle.value = type === 0 ? '一周排行' : '累计排行'
  trackSource.value = 'listen_rank'
  selectedUserPlaylist.value = null
  selectedRank.value = null
  selectedPlaylist.value = null
  selectedArtist.value = null
  selectedAlbum.value = null
  artistAlbums.value = []
  const { data, error: requestError } = await getMusicUserListenRank({ type })
  loading.value = false
  if (requestError) {
    error.value = requestError.message
    Logger.error('Failed to load music user listen rank', requestError)
    return
  }
  tracks.value = data?.items || []
  total.value = tracks.value.length
  void loadFavoriteCounts(tracks.value)
}

async function loadLatestListenSongs() {
  loading.value = true
  searched.value = true
  error.value = ''
  selectedSourceTitle.value = '继续播放'
  trackSource.value = 'latest_listen'
  selectedUserPlaylist.value = null
  selectedRank.value = null
  selectedPlaylist.value = null
  selectedArtist.value = null
  selectedAlbum.value = null
  artistAlbums.value = []
  const { data, error: requestError } = await getMusicLatestListenSongs({ page_size: pageSize })
  loading.value = false
  if (requestError) {
    error.value = requestError.message
    Logger.error('Failed to load latest music listen songs', requestError)
    return
  }
  tracks.value = data?.items || []
  total.value = tracks.value.length
  void loadFavoriteCounts(tracks.value)
}

async function addTrackToSelectedPlaylist(track: MusicTrack) {
  if (!targetUserPlaylistId.value || !track.hash) return
  const { error: requestError } = await addMusicUserPlaylistTrack({
    list_id: targetUserPlaylistId.value,
    track: {
      title: track.title,
      hash: track.hash,
      album_id: track.album_id,
      album_audio_id: track.album_audio_id,
    },
  })
  if (requestError) {
    error.value = requestError.message
    Logger.error('Failed to add music track to user playlist', requestError)
    return
  }
  if (selectedUserPlaylist.value?.id === targetUserPlaylistId.value) {
    await loadUserPlaylistTracks(selectedUserPlaylist.value, 1, false)
  }
  await loadUserPlaylists()
}

async function removeTrackFromSelectedPlaylist(track: MusicTrack) {
  if (!selectedUserPlaylist.value?.id || !track.file_id) return
  const { error: requestError } = await removeMusicUserPlaylistTracks({
    list_id: selectedUserPlaylist.value.id,
    file_ids: track.file_id,
  })
  if (requestError) {
    error.value = requestError.message
    Logger.error('Failed to remove music track from user playlist', requestError)
    return
  }
  await loadUserPlaylistTracks(selectedUserPlaylist.value, 1, false)
  await loadUserPlaylists()
}

async function loadFavoriteCounts(trackList: MusicTrack[]) {
  const ids = Array.from(new Set(trackList.map((track) => track.album_audio_id).filter(Boolean))).slice(0, 50)
  if (ids.length === 0) {
    favoriteCounts.value = {}
    return
  }
  const { data, error: requestError } = await getMusicFavoriteCount(ids.join(','))
  if (requestError) {
    Logger.error('Failed to load music favorite counts', requestError)
    return
  }
  const next: Record<string, number> = {}
  for (const item of data?.items || []) {
    next[item.mixsongid] = item.count
  }
  favoriteCounts.value = next
}

function playAll(shuffle: boolean) {
  if (tracks.value.length === 0) return
  store.shuffle = shuffle
  store.playQueue(tracks.value, 0)
}

const loadAuthStatus = async () => {
  const { data, error: requestError } = await getMusicAuthStatus()
  if (requestError) {
    Logger.error('Failed to load music auth status', requestError)
    return
  }
  authStatus.value = data
}

const openQrLogin = async () => {
  qrOpen.value = true
  qrLoading.value = true
  qrStatus.value = 1
  qrLogin.value = null
  stopQrPolling()

  const { data, error: requestError } = await createMusicQrLogin()
  qrLoading.value = false

  if (requestError || !data) {
    error.value = requestError?.message || '二维码生成失败'
    Logger.error('Failed to create music QR login', requestError)
    return
  }

  qrLogin.value = data
  startQrPolling()
}

const closeQrLogin = () => {
  qrOpen.value = false
  stopQrPolling()
}

const openQrUrl = () => {
  if (!qrLogin.value?.url) return
  window.open(qrLogin.value.url, '_blank', 'noopener,noreferrer')
}

const startQrPolling = () => {
  stopQrPolling()
  qrTimer = setInterval(() => {
    void pollQrLogin()
  }, 2000)
}

const stopQrPolling = () => {
  if (!qrTimer) return
  clearInterval(qrTimer)
  qrTimer = null
}

const pollQrLogin = async () => {
  if (!qrLogin.value?.key) return
  const { data, error: requestError } = await checkMusicQrLogin(qrLogin.value.key)
  if (requestError || !data) {
    Logger.error('Failed to check music QR login', requestError)
    return
  }

  qrStatus.value = data.status
  if (data.logged_in) {
    authStatus.value = data.auth
    stopQrPolling()
    setTimeout(() => {
      qrOpen.value = false
    }, 800)
  }
}

function onSeek(e: Event) {
  const val = Number((e.target as HTMLInputElement).value)
  store.seekTo(val)
}

function onVolume(e: Event) {
  const val = Number((e.target as HTMLInputElement).value)
  store.setVolume(val)
}

function toggleMute() {
  if (store.volume === 0) {
    store.setVolume(previousVolume || 0.7)
  } else {
    previousVolume = store.volume
    store.setVolume(0)
  }
}

function cycleRepeat() {
  if (store.repeat === 'none') store.repeat = 'all'
  else if (store.repeat === 'all') store.repeat = 'one'
  else store.repeat = 'none'
}

watch(quality, (val) => {
  store.setQuality(val)
})

const trackKey = (track: MusicTrack, index: number) => {
  return track.id || `${track.hash}-${index}`
}

const formatDuration = (seconds: number) => {
  if (!seconds || Number.isNaN(seconds)) return '00:00'
  const rounded = Math.floor(seconds)
  const minutes = Math.floor(rounded / 60)
  const rest = rounded % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

const formatCompactCount = (count: number) => {
  if (count >= 10000) return `${Math.floor(count / 10000)}w`
  return String(count)
}
</script>

<style scoped>
.music-page {
  display: grid;
  height: 100%;
  min-height: 0;
  grid-template-columns: 14.5rem minmax(0, 1fr);
  background: hsl(var(--background));
  color: hsl(var(--foreground));
}

.music-nav-sidebar {
  display: flex;
  flex-direction: column;
  background: hsl(var(--muted) / 0.15);
  border-right: 1px solid hsl(var(--border) / 0.35);
  padding: 1.5rem 0.875rem;
  gap: 1.25rem;
  overflow-y: auto;
  min-width: 0;
}

.music-nav-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: hsl(var(--foreground));
  margin-bottom: 0.25rem;
  padding-left: 0.5rem;
}

.music-nav-section {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.music-nav-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: hsl(var(--muted-foreground) / 0.7);
  font-weight: 600;
  margin-bottom: 0.375rem;
  padding-left: 0.5rem;
}

.music-nav-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  border: 0;
  background: transparent;
  border-radius: 0.375rem;
  padding: 0.45rem 0.5rem;
  text-align: left;
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-nav-item:hover {
  background: hsl(var(--muted) / 0.55);
  color: hsl(var(--foreground));
}

.music-nav-item.active {
  background: hsl(var(--primary) / 0.08);
  color: hsl(var(--primary));
  font-weight: 600;
}

.music-nav-sidebar .music-playlist-create {
  width: 100%;
  flex: none;
  background: transparent;
  border: none;
  padding: 0 0.5rem;
  gap: 0.375rem;
}

.music-discovery-grid {
  display: flex;
  flex-direction: column;
  margin: 0 auto;
  width: min(100%, 72rem);
}

.music-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr));
  gap: 1.25rem;
}

.music-grid-card {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  cursor: pointer;
  text-align: left;
}

.music-grid-card:hover {
  opacity: 0.85;
}

.music-grid-card-title {
  font-size: 0.8125rem;
  font-weight: 500;
  color: hsl(var(--foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.music-grid-card-subtitle {
  font-size: 0.7rem;
  color: hsl(var(--muted-foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.music-playlist-header {
  display: flex;
  gap: 1.5rem;
  align-items: center;
  border-bottom: 1px solid hsl(var(--border) / 0.25);
  padding-bottom: 1.5rem;
  margin-bottom: 1.5rem;
  width: min(100%, 72rem);
  margin-left: auto;
  margin-right: auto;
}

.music-playlist-header-cover {
  width: 6.5rem;
  height: 6.5rem;
  flex-shrink: 0;
  border-radius: 0.375rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
}

.music-playlist-header-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-playlist-header-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.music-playlist-header-info {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  flex: 1;
}

.music-playlist-header-actions {
  width: 100%;
}

.music-detail-intro {
  margin-top: 0.5rem;
  max-width: 48rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.music-detail-meta {
  margin-top: 0.5rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.music-link {
  border: 0;
  background: transparent;
  padding: 0;
  color: hsl(var(--muted-foreground));
  text-align: left;
}

.music-link:not(:disabled):hover {
  color: hsl(var(--primary));
}

.music-link:disabled {
  cursor: default;
}

.music-album-strip {
  margin: 0 auto 1rem;
  width: min(100%, 72rem);
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr));
  gap: 0.75rem;
}

.music-album-card {
  min-width: 0;
  border: 0;
  background: transparent;
  padding: 0;
  text-align: left;
  color: hsl(var(--foreground));
}

.music-album-card img,
.music-album-placeholder {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 0.375rem;
  object-fit: cover;
  background: hsl(var(--muted) / 0.4);
}

.music-album-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
}

.music-album-card span {
  display: block;
  margin-top: 0.375rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.75rem;
  font-weight: 500;
}

.music-album-card:hover span {
  color: hsl(var(--primary));
}

.music-search-sections {
  margin: 0 auto 1rem;
  width: min(100%, 72rem);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.music-search-section h2 {
  margin-bottom: 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 700;
}

.music-result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(7.5rem, 1fr));
  gap: 0.75rem;
}

.music-result-card {
  min-width: 0;
  border: 0;
  background: hsl(var(--muted) / 0.18);
  border-radius: 0.375rem;
  padding: 0.625rem;
  color: hsl(var(--foreground));
  text-align: left;
}

.music-result-card:hover {
  background: hsl(var(--muted) / 0.36);
}

.music-result-card img,
.music-result-placeholder {
  width: 3rem;
  height: 3rem;
  border-radius: 0.375rem;
  object-fit: cover;
  background: hsl(var(--muted) / 0.5);
}

.music-result-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
}

.music-result-card span,
.music-result-card small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-result-card span {
  margin-top: 0.5rem;
  font-size: 0.8125rem;
  font-weight: 600;
}

.music-result-card small {
  margin-top: 0.125rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
}

.music-main {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
}

.music-header {
  display: flex;
  min-height: 3.75rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border-bottom: 1px solid hsl(var(--border) / 0.35);
  padding: 0 1.5rem;
}

.music-search {
  display: flex;
  width: min(28rem, 50vw);
  align-items: center;
  gap: 0.5rem;
}

.music-search :deep(input) {
  background: hsl(var(--muted) / 0.35);
  border: 1px solid transparent;
  border-radius: 0.375rem;
  transition: all 0.2s ease;
}

.music-search :deep(input:focus-visible) {
  background: transparent;
  border-color: hsl(var(--primary) / 0.5);
  box-shadow: none;
}

.music-header-actions {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.75rem;
}

.music-content {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.music-list {
  margin: 0 auto;
  width: min(100%, 72rem);
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.music-discovery {
  margin: 0 auto 1.5rem;
  width: min(100%, 72rem);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.music-tabs {
  display: inline-flex;
  width: 100%;
  align-items: center;
  gap: 1.5rem;
  border-bottom: 1px solid hsl(var(--border) / 0.35);
  padding-bottom: 0.5rem;
}

.music-tab {
  position: relative;
  height: auto;
  border: 0;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  font-weight: 500;
  padding: 0.25rem 0;
  cursor: pointer;
  transition: color 0.15s ease;
}

.music-tab:hover {
  color: hsl(var(--foreground));
}

.music-tab--active {
  color: hsl(var(--foreground));
  font-weight: 600;
}

.music-tab--active::after {
  content: '';
  position: absolute;
  bottom: -0.5625rem;
  left: 0;
  right: 0;
  height: 2px;
  background: hsl(var(--primary));
  border-radius: 9999px;
}

.music-card-strip {
  display: flex;
  align-items: stretch;
  gap: 0.875rem;
  overflow-x: auto;
  padding-bottom: 0.5rem;
}

.music-playlist-create {
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 11rem;
  flex: 0 0 11rem;
  gap: 0.5rem;
  border: 1px solid hsl(var(--border) / 0.35);
  border-radius: 0.375rem;
  background: hsl(var(--muted) / 0.15);
  padding: 0.5rem;
}

.music-playlist-create :deep(input) {
  height: 1.75rem;
  border: 1px solid hsl(var(--border) / 0.45);
  background: hsl(var(--background));
}

.music-playlist-create-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.music-private-toggle {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.7rem;
}

.music-private-toggle input {
  width: 0.875rem;
  height: 0.875rem;
  accent-color: hsl(var(--primary));
  cursor: pointer;
}

.music-source-card {
  display: flex;
  flex-direction: column;
  width: 7.5rem;
  flex: 0 0 7.5rem;
  border: 0;
  border-radius: 0;
  background: transparent !important;
  padding: 0;
  text-align: left;
  cursor: pointer;
  gap: 0.375rem;
}

.music-source-card--playlist {
  width: 8rem;
  flex-basis: 8rem;
}

.music-source-card--compact {
  width: 6.5rem;
  flex-basis: 6.5rem;
  border-radius: 0.375rem;
  background: hsl(var(--muted) / 0.3) !important;
  padding: 0.75rem 0.5rem;
  align-items: center;
  justify-content: center;
  text-align: center;
  transition: background 0.15s ease, color 0.15s ease;
}

.music-source-card--compact:hover {
  background: hsl(var(--muted) / 0.6) !important;
}

.music-source-card--compact.music-source-card--active {
  background: hsl(var(--primary) / 0.08) !important;
  color: hsl(var(--primary));
}

.music-source-card:not(.music-source-card--compact):hover {
  opacity: 0.85;
}

.music-source-cover-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  border-radius: 0.375rem;
  background: hsl(var(--muted) / 0.3);
}

.music-source-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.music-source-card:hover .music-source-cover {
  transform: scale(1.04);
}

.music-source-play-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
  backdrop-filter: blur(2px);
}

.music-source-card:hover .music-source-play-overlay {
  opacity: 1;
}

.music-source-more {
  width: 4rem;
  flex: 0 0 4rem;
  border: 1px dashed hsl(var(--border) / 0.5);
  border-radius: 0.375rem;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease;
}

.music-source-more:hover {
  border-color: hsl(var(--primary) / 0.5);
  color: hsl(var(--foreground));
}

.music-source-loading {
  display: flex;
  align-items: center;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.music-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  height: 1.625rem;
  padding: 0 0.625rem;
  border-radius: 9999px;
  border: 1px solid hsl(var(--border) / 0.5);
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-chip:hover {
  background: hsl(var(--muted) / 0.4);
  color: hsl(var(--foreground));
  border-color: hsl(var(--border));
}

.music-chip--active {
  color: hsl(var(--primary));
  border-color: hsl(var(--primary) / 0.4);
  background: hsl(var(--primary) / 0.08);
}

.music-chip--danger {
  color: hsl(var(--destructive));
  border-color: hsl(var(--destructive) / 0.3);
}

.music-chip--danger:hover {
  background: hsl(var(--destructive) / 0.08);
  border-color: hsl(var(--destructive) / 0.5);
  color: hsl(var(--destructive));
}

.music-inline-select {
  height: 1.625rem;
  max-width: 10rem;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 0.375rem;
  background: hsl(var(--background));
  padding: 0 0.5rem;
  color: hsl(var(--foreground));
  font-size: 0.75rem;
  outline: none;
  cursor: pointer;
}

.music-row {
  display: grid;
  grid-template-columns: 2rem 3rem minmax(0, 1fr) minmax(8rem, 0.5fr) 5.25rem 4.75rem;
  align-items: center;
  gap: 0.75rem;
  min-height: 3.5rem;
  border-radius: 0.25rem;
  padding: 0.375rem 0.5rem;
  cursor: pointer;
  background: transparent;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.music-row--header {
  border-bottom: 1px solid hsl(var(--border) / 0.15);
  font-size: 0.6875rem;
  text-transform: uppercase;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: hsl(var(--muted-foreground) / 0.5);
  cursor: default;
  background: transparent !important;
  min-height: auto;
  padding-bottom: 0.625rem;
}

.music-row:hover {
  background: hsl(var(--muted) / 0.45);
}

.music-row--active {
  background: hsl(var(--primary) / 0.04);
  color: hsl(var(--primary));
}

.music-row-index {
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground) / 0.7);
  font-size: 0.8125rem;
}

.music-row-play {
  display: none;
}

.music-row:hover .music-row-number,
.music-row--active .music-row-number,
.music-row:hover .music-row-equalizer,
.music-row--active .music-row-equalizer {
  display: none;
}

.music-row:hover .music-row-play,
.music-row--active .music-row-play {
  display: block;
}

.music-row-equalizer {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 0.75rem;
  width: 0.75rem;
}

.eq-bar {
  display: block;
  width: 2px;
  background: hsl(var(--primary));
  border-radius: 9999px;
  animation: eqAnim 0.75s ease-in-out infinite alternate;
  transform-origin: bottom;
}

.eq-bar:nth-child(1) { height: 30%; animation-delay: 0s; }
.eq-bar:nth-child(2) { height: 95%; animation-delay: 0.2s; }
.eq-bar:nth-child(3) { height: 60%; animation-delay: 0.4s; }

@keyframes eqAnim {
  0% { transform: scaleY(0.3); }
  100% { transform: scaleY(1); }
}

.music-cover {
  display: flex;
  width: 2.25rem;
  height: 2.25rem;
  overflow: hidden;
  align-items: center;
  justify-content: center;
  border-radius: 0.25rem;
  background: hsl(var(--muted) / 0.4);
}

.music-row-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.25rem;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.music-row:hover .music-row-actions {
  opacity: 1;
}

.music-row-side {
  line-height: 1.2;
}

.music-row-side > span {
  display: block;
}

.music-row-side .music-favorite-count {
  display: inline-flex;
  justify-content: flex-end;
  gap: 0.125rem;
}

.music-favorite-count {
  align-items: center;
  gap: 0.2rem;
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground) / 0.75);
}

.music-row-action {
  display: flex;
  width: 1.75rem;
  height: 1.75rem;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 0.25rem;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-row-action:hover {
  background: hsl(var(--muted) / 0.6);
  color: hsl(var(--foreground));
}

.music-row-action:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.music-player {
  position: relative;
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  gap: 1.25rem;
  border-left: 1px solid hsl(var(--border) / 0.25);
  padding: 2.5rem 1.5rem;
  background: transparent;
  overflow: hidden;
}

.music-player-ambient-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  filter: blur(55px) saturate(2);
  opacity: 0.38;
  z-index: 0;
  transform: scale(1.2);
  transition: background-image 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

.music-player-ambient-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, transparent, hsl(var(--background)) 85%);
  z-index: 1;
  pointer-events: none;
}

.dark .music-player-ambient-overlay {
  background: linear-gradient(to bottom, transparent, hsl(var(--background)) 80%);
}

/* Ensure child content floats above ambient layers */
.music-player > *:not(.music-player-ambient-bg):not(.music-player-ambient-overlay) {
  position: relative;
  z-index: 2;
}

.music-player-art {
  display: flex;
  width: min(12.5rem, 100%);
  aspect-ratio: 1;
  overflow: hidden;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-xl, 12px);
  background: hsl(var(--muted) / 0.35);
  border: 1px solid hsl(var(--border) / 0.4);
  transition: transform 0.3s ease;
}

.music-player-art img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}

.music-player-art:hover img {
  transform: scale(1.05);
}

.music-player-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.music-player-btn {
  display: flex;
  width: 2.25rem;
  height: 2.25rem;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 0.375rem;
  background: none;
  color: hsl(var(--foreground));
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-player-btn:hover {
  background: hsl(var(--muted) / 0.6);
}

.music-player-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.music-player-main-btn {
  display: flex;
  width: 2.75rem;
  height: 2.75rem;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 9999px;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  cursor: pointer;
  transition: transform 0.15s ease, background 0.15s ease;
}

.music-player-main-btn:hover {
  transform: scale(1.05);
  background: hsl(var(--primary) / 0.9);
}

.music-player-main-btn:active {
  transform: scale(0.95);
}

.music-player-main-btn:disabled {
  opacity: 0.4;
  background: hsl(var(--muted-foreground));
}

.music-progress {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.music-progress-range {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 3px;
  border-radius: 9999px;
  background: linear-gradient(to right, hsl(var(--primary)) var(--slider-progress, 0%), hsl(var(--border) / 0.45) var(--slider-progress, 0%));
  outline: none;
  cursor: pointer;
  transition: height 0.1s ease;
}

.music-progress-range:hover {
  height: 5px;
}

.music-progress-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  background: hsl(var(--primary));
  border: none;
  opacity: 0;
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.music-progress-range:hover::-webkit-slider-thumb {
  opacity: 1;
  transform: scale(1.2);
}

.music-player-extras {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.music-quality {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.music-quality-select {
  height: 1.75rem;
  min-width: 5.5rem;
  border-radius: 0.375rem;
  border: 1px solid hsl(var(--border) / 0.5);
  background: hsl(var(--background));
  padding: 0 0.5rem;
  font-size: 0.8125rem;
  outline: none;
  cursor: pointer;
}

.music-volume {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.music-volume-range {
  -webkit-appearance: none;
  appearance: none;
  width: 5rem;
  height: 3px;
  border-radius: 9999px;
  background: linear-gradient(to right, hsl(var(--foreground)) var(--slider-progress, 0%), hsl(var(--border) / 0.45) var(--slider-progress, 0%));
  outline: none;
  cursor: pointer;
}

.music-volume-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: hsl(var(--foreground));
  opacity: 0;
  transition: opacity 0.15s ease;
}

.music-volume:hover .music-volume-range::-webkit-slider-thumb {
  opacity: 1;
}

.music-lyrics {
  position: relative;
  width: 100%;
  height: 12rem;
  overflow-y: auto;
  border-top: 1px solid hsl(var(--border) / 0.25);
  padding-top: 0.75rem;
  mask-image: linear-gradient(to bottom, transparent, white 20%, white 80%, transparent);
  -webkit-mask-image: linear-gradient(to bottom, transparent, white 20%, white 80%, transparent);
}

.music-lyric-state {
  display: flex;
  min-height: 8rem;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.music-lyric-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.25rem 0;
}

.music-lyric-line {
  margin: 0;
  text-align: center;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: hsl(var(--muted-foreground) / 0.55);
  transition: color 0.18s ease, font-size 0.18s ease, font-weight 0.18s ease;
}

.music-lyric-line--active {
  color: hsl(var(--foreground));
  font-weight: 600;
  font-size: 0.875rem;
}

.music-empty {
  display: flex;
  min-height: 24rem;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.music-skeleton {
  height: 3.5rem;
  border-radius: 0.25rem;
  background: hsl(var(--accent) / 0.35);
  animation: pulse 1.8s ease-in-out infinite;
}

.music-qr-modal {
  position: fixed;
  inset: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(0 0 0 / 0.45);
  padding: 1rem;
}

.music-qr-panel {
  width: min(100%, 20rem);
  overflow: hidden;
  border-radius: 0.375rem;
  border: 1px solid hsl(var(--border) / 0.6);
  background: hsl(var(--background));
}

.music-qr-image {
  display: flex;
  width: 12rem;
  height: 12rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  border: 1px solid hsl(var(--border) / 0.45);
  background: white;
  padding: 0.5rem;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.55;
  }
  50% {
    opacity: 1;
  }
}

@media (max-width: 1023px) {
  .music-page {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(0, 1fr) auto;
  }

  .music-player {
    border-left: 0;
    border-top: 1px solid hsl(var(--border) / 0.35);
    padding: 1.5rem;
  }

  .music-player-art {
    display: none;
  }
}

@media (max-width: 767px) {
  .music-header {
    min-height: 6rem;
    flex-direction: column;
    align-items: stretch;
    justify-content: center;
    padding: 0.75rem 1rem;
    gap: 0.75rem;
  }

  .music-search {
    width: 100%;
  }

  .music-header-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .music-row {
    grid-template-columns: 2rem 3rem minmax(0, 1fr) 4.75rem;
  }

  .music-row-actions {
    grid-column: 4;
  }
}
</style>
