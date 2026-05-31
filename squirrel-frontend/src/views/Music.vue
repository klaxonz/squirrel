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
            <article
              v-for="(track, index) in tracks"
              :key="trackKey(track, index)"
              class="music-row"
              :class="{ 'music-row--active': currentTrack && trackKey(currentTrack, 0) === trackKey(track, index) }"
              @click="playTrack(track)"
            >
              <div class="music-row-index">
                <span class="music-row-number">{{ index + 1 }}</span>
                <AppIcon name="play" class="music-row-play h-4 w-4 fill-current" />
              </div>
              <div class="music-cover">
                <img v-if="track.cover" :src="track.cover" alt="" class="h-full w-full object-cover" />
                <AppIcon v-else name="playlistMusic" class="h-5 w-5 text-muted-foreground" />
              </div>
              <div class="min-w-0">
                <div class="truncate text-sm font-medium text-foreground">{{ track.title || '未知歌曲' }}</div>
                <div class="mt-1 truncate text-xs text-muted-foreground">{{ track.artist || '未知歌手' }}</div>
              </div>
              <div class="hidden truncate text-sm text-muted-foreground md:block">{{ track.album || '未知专辑' }}</div>
              <div class="hidden text-right text-sm tabular-nums text-muted-foreground sm:block">
                {{ formatDuration(track.duration) }}
              </div>
            </article>
          </div>
        </div>
      </section>

      <aside class="music-player">
        <div class="music-player-art">
          <img v-if="currentTrack?.cover" :src="currentTrack.cover" alt="" class="h-full w-full object-cover" />
          <AppIcon v-else name="playlistMusic" class="h-16 w-16 text-muted-foreground/40" />
        </div>

        <div class="min-w-0 text-center">
          <h2 class="truncate text-base font-semibold">{{ currentTrack?.title || '未选择歌曲' }}</h2>
          <p class="mt-1 truncate text-sm text-muted-foreground">{{ currentTrack?.artist || '酷狗音乐' }}</p>
        </div>

        <div class="music-player-controls">
          <Button variant="ghost" size="icon" class="h-9 w-9 rounded-md" :disabled="!canStep" @click="playPrevious">
            <AppIcon name="previous" class="h-4 w-4" />
          </Button>
          <Button class="h-11 w-11 rounded-full" size="icon" :disabled="!currentTrack || resolvingUrl" @click="togglePlayback">
            <AppIcon v-if="resolvingUrl" name="loadingSpinner" class="h-5 w-5 animate-spin" />
            <AppIcon v-else-if="playing" name="pause" class="h-5 w-5 fill-current" />
            <AppIcon v-else name="play" class="h-5 w-5 fill-current" />
          </Button>
          <Button variant="ghost" size="icon" class="h-9 w-9 rounded-md" :disabled="!canStep" @click="playNext">
            <AppIcon name="next" class="h-4 w-4" />
          </Button>
        </div>

        <div class="music-progress">
          <input
            class="music-progress-range"
            type="range"
            min="0"
            :max="duration || 0"
            :value="currentTime"
            :disabled="!audioSrc"
            @input="seekTo"
          />
          <div class="flex justify-between text-xs tabular-nums text-muted-foreground">
            <span>{{ formatDuration(currentTime) }}</span>
            <span>{{ formatDuration(duration) }}</span>
          </div>
        </div>

        <div class="music-quality">
          <span class="text-xs text-muted-foreground">音质</span>
          <select v-model="quality" class="music-quality-select">
            <option value="128">128</option>
            <option value="320">320</option>
            <option value="flac">FLAC</option>
            <option value="high">无损</option>
          </select>
        </div>

        <audio
          ref="audioRef"
          :src="audioSrc"
          preload="none"
          @play="playing = true"
          @pause="playing = false"
          @ended="playNext"
          @timeupdate="syncAudioState"
          @loadedmetadata="syncAudioState"
        />
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
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  checkMusicQrLogin,
  createMusicQrLogin,
  getMusicAuthStatus,
  getMusicPlayUrl,
  searchMusic,
  type MusicAuthStatus,
  type MusicQrLogin,
  type MusicTrack,
} from '@/api/music'
import { Logger } from '@/utils/logger'

const query = ref('')
const tracks = ref<MusicTrack[]>([])
const currentTrack = ref<MusicTrack | null>(null)
const loading = ref(false)
const resolvingUrl = ref(false)
const searched = ref(false)
const error = ref('')
const quality = ref('128')
const audioRef = ref<HTMLAudioElement | null>(null)
const audioSrc = ref('')
const playing = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const total = ref(0)
const authStatus = ref<MusicAuthStatus | null>(null)
const qrOpen = ref(false)
const qrLoading = ref(false)
const qrLogin = ref<MusicQrLogin | null>(null)
const qrStatus = ref(0)
let qrTimer: ReturnType<typeof setInterval> | null = null

const resultSummary = computed(() => {
  if (loading.value) return '搜索中'
  if (!searched.value) return '本地酷狗服务'
  return `共 ${total.value} 首`
})

const canStep = computed(() => tracks.value.length > 1)

const qrStatusText = computed(() => {
  if (qrLoading.value) return '二维码生成中'
  if (qrStatus.value === 4) return '登录成功'
  if (qrStatus.value === 2) return '已扫码，请在手机上确认'
  if (qrStatus.value === 0 && qrLogin.value) return '二维码已过期，请刷新'
  return '使用酷狗音乐 App 扫码'
})

onMounted(() => {
  void loadAuthStatus()
})

onUnmounted(() => {
  stopQrPolling()
})

const submitSearch = async () => {
  const keyword = query.value.trim()
  if (!keyword || loading.value) return

  loading.value = true
  searched.value = true
  error.value = ''

  const { data, error: requestError } = await searchMusic({ query: keyword, page: 1, page_size: 30 })
  loading.value = false

  if (requestError) {
    error.value = requestError.message
    tracks.value = []
    total.value = 0
    Logger.error('Failed to search music', requestError)
    return
  }

  tracks.value = data?.items || []
  total.value = data?.total || tracks.value.length
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

const playTrack = async (track: MusicTrack) => {
  currentTrack.value = track
  await resolveAndPlay(track)
}

const resolveAndPlay = async (track: MusicTrack) => {
  if (!track.hash || resolvingUrl.value) return

  resolvingUrl.value = true
  error.value = ''

  const { data, error: requestError } = await getMusicPlayUrl({
    hash: track.hash,
    album_audio_id: track.album_audio_id || undefined,
    quality: quality.value,
  })

  resolvingUrl.value = false

  if (requestError || !data?.url) {
    error.value = requestError?.message || '当前歌曲没有可播放地址'
    Logger.error('Failed to resolve music play url', requestError || data)
    return
  }

  audioSrc.value = data.url
  await nextTick()
  await audioRef.value?.play()
}

const togglePlayback = async () => {
  if (!currentTrack.value) return
  if (!audioSrc.value) {
    await resolveAndPlay(currentTrack.value)
    return
  }

  if (audioRef.value?.paused) {
    await audioRef.value.play()
  } else {
    audioRef.value?.pause()
  }
}

const playPrevious = () => {
  playOffset(-1)
}

const playNext = () => {
  playOffset(1)
}

const playOffset = (offset: number) => {
  if (!currentTrack.value || tracks.value.length === 0) return
  const index = tracks.value.findIndex((track) => trackKey(track, 0) === trackKey(currentTrack.value as MusicTrack, 0))
  const nextIndex = (index + offset + tracks.value.length) % tracks.value.length
  void playTrack(tracks.value[nextIndex])
}

const seekTo = (event: Event) => {
  const value = Number((event.target as HTMLInputElement).value)
  if (!audioRef.value || Number.isNaN(value)) return
  audioRef.value.currentTime = value
  currentTime.value = value
}

const syncAudioState = () => {
  currentTime.value = audioRef.value?.currentTime || 0
  duration.value = audioRef.value?.duration || currentTrack.value?.duration || 0
}

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
.music-row--active .music-row-number {
  display: none;
}

.music-row:hover .music-row-play,
.music-row--active .music-row-play {
  display: block;
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
}

.music-player-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
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

.music-quality {
  display: flex;
  width: min(18rem, 100%);
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
