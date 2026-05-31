<template>
  <AppPageShell variant="compact">
    <div class="music-page">
      <section class="music-main">
        <header class="music-header">
          <div class="min-w-0">
            <h1 class="truncate text-base font-semibold">音乐</h1>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ resultSummary }}</p>
          </div>
          <div class="music-header-actions">
            <Button variant="outline" class="h-9 rounded-md px-3" @click="openQrLogin">
              <AppIcon name="user" class="h-4 w-4" />
              {{ authStatus?.logged_in ? '已登录' : '扫码登录' }}
            </Button>
            <form class="music-search" @submit.prevent="submitSearch">
              <Input
                v-model="query"
                class="h-9 border-none bg-muted/50 text-sm focus-visible:ring-1"
                placeholder="搜索歌曲、歌手、专辑"
              />
              <Button type="submit" class="h-9 rounded-md px-3" :disabled="loading || !query.trim()">
                <AppIcon v-if="loading" name="loadingSpinner" class="h-4 w-4 animate-spin" />
                <AppIcon v-else name="search" class="h-4 w-4" />
                搜索
              </Button>
            </form>
          </div>
        </header>

        <div class="music-content custom-scrollbar">
          <div class="music-discovery">
            <div class="music-tabs">
              <button
                class="music-tab"
                :class="{ 'music-tab--active': activeMode === 'recommend' }"
                @click="setMusicMode('recommend')"
              >
                推荐
              </button>
              <button
                class="music-tab"
                :class="{ 'music-tab--active': activeMode === 'rank' }"
                @click="setMusicMode('rank')"
              >
                排行榜
              </button>
              <button
                class="music-tab"
                :class="{ 'music-tab--active': activeMode === 'playlist' }"
                @click="setMusicMode('playlist')"
              >
                歌单
              </button>
            </div>

            <div v-if="activeMode === 'rank'" class="music-card-strip custom-scrollbar">
              <button
                v-for="rank in ranks"
                :key="rank.id"
                class="music-source-card"
                :class="{ 'music-source-card--active': selectedRank?.id === rank.id }"
                @click="selectRank(rank)"
              >
                <img v-if="rank.cover" :src="rank.cover" alt="" class="music-source-cover" />
                <div v-else class="music-source-cover">
                  <AppIcon name="playlistMusic" class="h-5 w-5 text-muted-foreground" />
                </div>
                <span class="truncate text-xs font-medium">{{ rank.name }}</span>
                <span class="truncate text-[0.7rem] text-muted-foreground">{{ rank.update_frequency || '排行榜' }}</span>
              </button>
              <span v-if="discoveryLoading" class="music-source-loading">加载中</span>
            </div>

            <div v-else-if="activeMode === 'playlist'" class="music-card-strip custom-scrollbar">
              <button
                v-for="playlist in playlists"
                :key="playlist.id"
                class="music-source-card music-source-card--playlist"
                :class="{ 'music-source-card--active': selectedPlaylist?.id === playlist.id }"
                @click="selectPlaylist(playlist)"
              >
                <img v-if="playlist.cover" :src="playlist.cover" alt="" class="music-source-cover" />
                <div v-else class="music-source-cover">
                  <AppIcon name="playlistMusic" class="h-5 w-5 text-muted-foreground" />
                </div>
                <span class="truncate text-xs font-medium">{{ playlist.name }}</span>
                <span class="truncate text-[0.7rem] text-muted-foreground">{{ playlist.creator || '歌单' }}</span>
              </button>
              <button v-if="playlistHasMore" class="music-source-more" :disabled="discoveryLoading" @click="loadMorePlaylists">
                更多
              </button>
              <span v-if="discoveryLoading" class="music-source-loading">加载中</span>
            </div>
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
            <div class="flex items-center justify-between px-1 pb-2">
              <span class="text-xs text-muted-foreground">{{ tracks.length }} / {{ total }} 首歌曲</span>
              <div class="flex items-center gap-1">
                <button
                  class="music-chip"
                  title="播放全部"
                  @click="playAll(false)"
                >
                  <AppIcon name="play" class="h-3.5 w-3.5" />
                  播放全部
                </button>
                <button
                  class="music-chip"
                  :class="{ 'music-chip--active': store.shuffle }"
                  title="随机播放"
                  @click="playAll(true)"
                >
                  <AppIcon name="shuffle" class="h-3.5 w-3.5" />
                  随机
                </button>
              </div>
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
                <div class="mt-1 truncate text-xs text-muted-foreground">{{ track.artist || '未知歌手' }}</div>
              </div>
              <div class="hidden truncate text-sm text-muted-foreground md:block">{{ track.album || '未知专辑' }}</div>
              <div class="hidden text-right text-sm tabular-nums text-muted-foreground sm:block">
                {{ formatDuration(track.duration) }}
              </div>
            </article>

            <div v-if="hasMore" class="flex justify-center pt-3">
              <Button variant="outline" class="h-9 rounded-md px-4" :disabled="loading" @click="loadMoreSearch">
                <AppIcon v-if="loading" name="loadingSpinner" class="h-4 w-4 animate-spin" />
                加载更多
              </Button>
            </div>
          </div>
        </div>
      </section>

      <aside class="music-player">
        <div class="music-player-art">
          <img
            v-if="store.currentTrack?.cover"
            :src="store.currentTrack.cover"
            alt=""
            class="h-full w-full object-cover"
            :class="{ 'music-player-art--spin': store.playing }"
          />
          <AppIcon v-else name="playlistMusic" class="h-16 w-16 text-muted-foreground/40" />
        </div>

        <div class="min-w-0 text-center">
          <h2 class="truncate text-base font-semibold">{{ store.currentTrack?.title || '未选择歌曲' }}</h2>
          <p class="mt-1 truncate text-sm text-muted-foreground">{{ store.currentTrack?.artist || '酷狗音乐' }}</p>
          <p v-if="store.currentTrack?.album" class="mt-0.5 truncate text-xs text-muted-foreground/60">
            {{ store.currentTrack.album }}
          </p>
        </div>

        <div class="music-player-controls">
          <button class="music-player-btn" :class="{ 'text-primary': store.shuffle }" title="随机" @click="store.shuffle = !store.shuffle">
            <AppIcon name="shuffle" class="h-4 w-4" />
          </button>
          <button class="music-player-btn" :disabled="!canStep" @click="store.playPrevious()">
            <AppIcon name="previous" class="h-4 w-4" />
          </button>
          <button class="music-player-main-btn" :disabled="!store.currentTrack || store.resolvingUrl" @click="store.togglePlayback()">
            <AppIcon v-if="store.resolvingUrl" name="loadingSpinner" class="h-5 w-5 animate-spin" />
            <AppIcon v-else-if="store.playing" name="pause" class="h-5 w-5 fill-current" />
            <AppIcon v-else name="play" class="h-5 w-5 fill-current" />
          </button>
          <button class="music-player-btn" :disabled="!canStep" @click="store.playNext()">
            <AppIcon name="next" class="h-4 w-4" />
          </button>
          <button
            class="music-player-btn relative"
            :class="{ 'text-primary': store.repeat !== 'none' }"
            :title="repeatTitle"
            @click="cycleRepeat"
          >
            <AppIcon v-if="store.repeat === 'one'" name="loop" class="h-4 w-4" />
            <AppIcon v-else name="refresh" class="h-4 w-4" />
            <sup v-if="store.repeat === 'one'" class="absolute -top-0.5 -right-0.5 text-[0.6rem]">1</sup>
          </button>
        </div>

        <div class="music-progress">
          <input
            class="music-progress-range"
            type="range"
            min="0"
            :max="store.duration || 0"
            :value="store.currentTime"
            :disabled="!store.audioSrc"
            @input="onSeek"
          />
          <div class="flex justify-between text-xs tabular-nums text-muted-foreground">
            <span>{{ formatDuration(store.currentTime) }}</span>
            <span>{{ formatDuration(store.duration) }}</span>
          </div>
        </div>

        <div class="music-player-extras">
          <div class="music-quality">
            <span class="text-xs text-muted-foreground">音质</span>
            <select v-model="quality" class="music-quality-select">
              <option value="128">128k</option>
              <option value="320">320k</option>
              <option value="flac">FLAC</option>
              <option value="high">无损</option>
            </select>
          </div>

          <div class="music-volume">
            <span class="text-xs text-muted-foreground">音量</span>
            <div class="flex items-center gap-1.5">
              <button class="music-player-btn" @click="toggleMute">
                <AppIcon :name="volumeIcon" class="h-3.5 w-3.5" />
              </button>
              <input
                class="music-volume-range"
                type="range"
                min="0"
                max="1"
                step="0.05"
                :value="store.volume"
                @input="onVolume"
              />
            </div>
          </div>
        </div>

        <div v-if="store.error" class="text-xs text-destructive text-center px-2">
          {{ store.error }}
        </div>

        <div class="music-lyrics custom-scrollbar">
          <div v-if="store.lyricLoading" class="music-lyric-state">歌词加载中</div>
          <div v-else-if="store.lyricError" class="music-lyric-state text-destructive">{{ store.lyricError }}</div>
          <div v-else-if="store.lyricLines.length === 0" class="music-lyric-state">暂无歌词</div>
          <div v-else class="music-lyric-list">
            <p
              v-for="(line, index) in store.lyricLines"
              :key="`${line.time}-${index}`"
              class="music-lyric-line"
              :class="{ 'music-lyric-line--active': index === store.currentLyricIndex }"
            >
              {{ line.text || '·' }}
            </p>
          </div>
        </div>
      </aside>

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
  checkMusicQrLogin,
  createMusicQrLogin,
  getMusicAuthStatus,
  getMusicPlaylistTracks,
  getMusicPlaylists,
  getMusicRankTracks,
  getMusicRanks,
  searchMusic,
  type MusicAuthStatus,
  type MusicPlaylist,
  type MusicQrLogin,
  type MusicRank,
  type MusicTrack,
} from '@/api/music'
import { useMusicPlayerStore } from '@/stores/musicPlayer'
import { Logger } from '@/utils/logger'

const store = useMusicPlayerStore()

type MusicMode = 'recommend' | 'rank' | 'playlist'
type TrackSource = 'recommend' | 'search' | 'rank' | 'playlist'

const query = ref('')
const tracks = ref<MusicTrack[]>([])
const ranks = ref<MusicRank[]>([])
const playlists = ref<MusicPlaylist[]>([])
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
const currentPage = ref(1)
const playlistPage = ref(1)
const playlistHasMore = ref(false)
const pageSize = 30
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
const hasMore = computed(() => trackSource.value !== 'recommend' && tracks.value.length < total.value)

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

let previousVolume = 0.7

onMounted(() => {
  void loadAuthStatus()
  void loadSuggestions()
  void loadRanks()
  void loadPlaylists(false)
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
  }
}

const submitSearch = async () => {
  const keyword = query.value.trim()
  if (!keyword || loading.value) return

  activeMode.value = 'recommend'
  trackSource.value = 'search'
  selectedRank.value = null
  selectedPlaylist.value = null
  selectedSourceTitle.value = `搜索：${keyword}`
  currentPage.value = 1
  await searchPage(keyword, currentPage.value, false)
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
}

async function setMusicMode(mode: MusicMode) {
  activeMode.value = mode
  if (mode === 'recommend') {
    selectedRank.value = null
    selectedPlaylist.value = null
    selectedSourceTitle.value = ''
    await loadSuggestions()
  } else if (mode === 'rank' && ranks.value.length === 0) {
    await loadRanks()
  } else if (mode === 'playlist' && playlists.value.length === 0) {
    await loadPlaylists(false)
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

async function selectPlaylist(playlist: MusicPlaylist) {
  selectedPlaylist.value = playlist
  selectedRank.value = null
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
</script>

<style scoped>
.music-page {
  display: grid;
  height: 100%;
  min-height: 0;
  grid-template-columns: minmax(0, 1fr) 22rem;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
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
  border-bottom: 1px solid hsl(var(--border) / 0.5);
  padding: 0 1rem;
}

.music-search {
  display: flex;
  width: min(32rem, 55vw);
  align-items: center;
  gap: 0.5rem;
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
  padding: 1rem;
}

.music-list {
  margin: 0 auto;
  width: min(100%, 72rem);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.music-discovery {
  margin: 0 auto 0.75rem;
  width: min(100%, 72rem);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.music-tabs {
  display: inline-flex;
  width: fit-content;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.6);
  border-radius: 0.5rem;
  background: hsl(var(--muted) / 0.25);
}

.music-tab {
  height: 2rem;
  min-width: 4.25rem;
  border: 0;
  border-right: 1px solid hsl(var(--border) / 0.45);
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  cursor: pointer;
}

.music-tab:last-child {
  border-right: 0;
}

.music-tab--active {
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  font-weight: 600;
}

.music-card-strip {
  display: flex;
  gap: 0.625rem;
  overflow-x: auto;
  padding-bottom: 0.25rem;
}

.music-source-card {
  display: grid;
  width: 8rem;
  flex: 0 0 8rem;
  grid-template-rows: 5rem auto auto;
  gap: 0.35rem;
  border: 1px solid hsl(var(--border) / 0.55);
  border-radius: 0.5rem;
  background: hsl(var(--background));
  padding: 0.45rem;
  text-align: left;
  cursor: pointer;
  transition: border-color 160ms ease, background 160ms ease;
}

.music-source-card--playlist {
  width: 8.75rem;
  flex-basis: 8.75rem;
}

.music-source-card:hover,
.music-source-card--active {
  border-color: hsl(var(--primary) / 0.5);
  background: hsl(var(--accent) / 0.35);
}

.music-source-cover {
  display: flex;
  width: 100%;
  height: 5rem;
  overflow: hidden;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  background: hsl(var(--muted));
  object-fit: cover;
}

.music-source-more {
  width: 4rem;
  flex: 0 0 4rem;
  border: 1px dashed hsl(var(--border));
  border-radius: 0.5rem;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  cursor: pointer;
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
  height: 1.75rem;
  padding: 0 0.625rem;
  border-radius: 9999px;
  border: 1px solid hsl(var(--border) / 0.6);
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease, border-color 160ms ease;
}

.music-chip:hover {
  background: hsl(var(--accent) / 0.4);
  color: hsl(var(--foreground));
  border-color: hsl(var(--border));
}

.music-chip--active {
  color: hsl(var(--primary));
  border-color: hsl(var(--primary) / 0.4);
  background: hsl(var(--primary) / 0.08);
}

.music-row {
  display: grid;
  grid-template-columns: 2rem 3rem minmax(0, 1fr) minmax(8rem, 0.5fr) 4rem;
  align-items: center;
  gap: 0.75rem;
  min-height: 4rem;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  padding: 0.5rem;
  cursor: pointer;
  transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease;
}

.music-row:hover,
.music-row--active {
  border-color: hsl(var(--border) / 0.6);
  background: hsl(var(--accent) / 0.5);
}

.music-row--active {
  color: hsl(var(--primary));
}

.music-row-index {
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
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
  align-items: center;
  gap: 2px;
  height: 1rem;
}

.eq-bar {
  display: block;
  width: 3px;
  background: hsl(var(--primary));
  border-radius: 1px;
  animation: eqAnim 0.7s ease-in-out infinite alternate;
}

.eq-bar:nth-child(1) { height: 8px; animation-delay: 0s; }
.eq-bar:nth-child(2) { height: 14px; animation-delay: 0.15s; }
.eq-bar:nth-child(3) { height: 10px; animation-delay: 0.3s; }

@keyframes eqAnim {
  0% { transform: scaleY(0.5); }
  100% { transform: scaleY(1); }
}

.music-cover {
  display: flex;
  width: 3rem;
  height: 3rem;
  overflow: hidden;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  background: hsl(var(--muted));
}

.music-player {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  gap: 1.25rem;
  border-left: 1px solid hsl(var(--border) / 0.5);
  padding: 2rem 1.25rem;
  background: hsl(var(--muted) / 0.2);
}

.music-player-art {
  display: flex;
  width: min(18rem, 100%);
  aspect-ratio: 1;
  overflow: hidden;
  align-items: center;
  justify-content: center;
  border-radius: 0.75rem;
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border) / 0.6);
  transition: transform 0.3s ease;
}

.music-player-art--spin {
  animation: spin 20s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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
  transition: background 160ms ease, color 160ms ease;
}

.music-player-btn:hover {
  background: hsl(var(--accent) / 0.6);
}

.music-player-btn:disabled {
  opacity: 0.35;
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
  background: hsl(var(--foreground));
  color: hsl(var(--background));
  cursor: pointer;
  transition: background 160ms ease, opacity 160ms ease;
}

.music-player-main-btn:hover {
  background: hsl(var(--foreground) / 0.85);
}

.music-player-main-btn:disabled {
  opacity: 0.4;
  background: hsl(var(--muted-foreground));
}

.music-progress {
  width: min(18rem, 100%);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.music-progress-range {
  width: 100%;
  accent-color: hsl(var(--primary));
}

.music-player-extras {
  width: min(18rem, 100%);
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
  height: 2rem;
  min-width: 6rem;
  border-radius: 0.375rem;
  border: 1px solid hsl(var(--border));
  background: hsl(var(--background));
  padding: 0 0.5rem;
  font-size: 0.875rem;
}

.music-volume {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.music-volume-range {
  width: 7rem;
  accent-color: hsl(var(--primary));
}

.music-lyrics {
  width: min(18rem, 100%);
  min-height: 8rem;
  max-height: 14rem;
  overflow-y: auto;
  border-top: 1px solid hsl(var(--border) / 0.5);
  padding-top: 0.75rem;
}

.music-lyric-state {
  display: flex;
  min-height: 6rem;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.music-lyric-list {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding: 0.25rem 0;
}

.music-lyric-line {
  margin: 0;
  text-align: center;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: hsl(var(--muted-foreground));
  transition: color 160ms ease, font-weight 160ms ease;
}

.music-lyric-line--active {
  color: hsl(var(--foreground));
  font-weight: 600;
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
  height: 4rem;
  border-radius: 0.5rem;
  background: hsl(var(--accent) / 0.35);
  animation: pulse 1.8s ease-in-out infinite;
}

.music-qr-modal {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(0 0 0 / 0.42);
  padding: 1rem;
}

.music-qr-panel {
  width: min(100%, 22rem);
  overflow: hidden;
  border-radius: 0.75rem;
  border: 1px solid hsl(var(--border));
  background: hsl(var(--background));
  box-shadow: 0 18px 60px rgb(0 0 0 / 0.24);
}

.music-qr-image {
  display: flex;
  width: 13rem;
  height: 13rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.75rem;
  border: 1px solid hsl(var(--border) / 0.65);
  background: white;
  padding: 0.75rem;
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
    border-top: 1px solid hsl(var(--border) / 0.5);
    padding: 1rem;
  }

  .music-player-art {
    display: none;
  }
}

@media (max-width: 767px) {
  .music-header {
    min-height: 6.5rem;
    flex-direction: column;
    align-items: stretch;
    justify-content: center;
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
    grid-template-columns: 2rem 3rem minmax(0, 1fr);
  }
}
</style>
