<template>
  <Transition
    enter-active-class="transition-all duration-300 ease-out"
    leave-active-class="transition-all duration-200 ease-in"
    enter-from-class="translate-y-full opacity-0"
    leave-to-class="translate-y-full opacity-0"
  >
    <div
      v-if="store.currentTrack"
      class="music-bar"
      :class="{ 'music-bar--immersive': showImmersive }"
    >
      <audio
        ref="audioEl"
        preload="none"
        @play="store.syncPlayState()"
        @pause="store.syncPlayState()"
        @ended="store._onEnded()"
        @timeupdate="store.syncAudioState()"
        @loadedmetadata="store.syncAudioState()"
      />

      <div class="music-bar-inner">
        <button class="music-bar-track" @click="openImmersive" title="显示歌词面板">
          <div class="music-bar-cover">
            <img
              v-if="store.currentTrack.cover"
              :src="store.currentTrack.cover"
              alt=""
              class="h-full w-full object-cover"
            />
            <AppIcon v-else name="playlistMusic" class="h-4 w-4 text-muted-foreground" />
          </div>
          <div class="min-w-0">
            <div class="truncate text-sm font-medium leading-tight">
              {{ store.currentTrack.title || '未知歌曲' }}
            </div>
            <div class="mt-0.5 truncate text-xs text-muted-foreground leading-tight">
              {{ store.currentTrack.artist || '酷狗音乐' }}
            </div>
          </div>
        </button>

        <div class="music-bar-controls">
          <button
            class="music-bar-btn"
            :disabled="!canStep"
            title="上一首"
            @click="store.playPrevious()"
          >
            <AppIcon name="previous" class="h-4 w-4" />
          </button>
          <button
            class="music-bar-btn music-bar-btn--play"
            :disabled="store.resolvingUrl"
            title="播放/暂停"
            @click="store.togglePlayback()"
          >
            <AppIcon v-if="store.resolvingUrl" name="loadingSpinner" class="h-5 w-5 animate-spin" stroke-width="2.5" />
            <AppIcon v-else-if="store.playing" name="pause" class="h-5 w-5 fill-current" stroke-width="2.5" />
            <AppIcon v-else name="play" class="h-5 w-5 fill-current" stroke-width="2.5" />
          </button>
          <button
            class="music-bar-btn"
            :disabled="!canStep"
            title="下一首"
            @click="store.playNext()"
          >
            <AppIcon name="next" class="h-4 w-4" />
          </button>
        </div>

        <div class="music-bar-progress-wrap">
          <span class="music-bar-time">{{ formatDuration(store.currentTime) }}</span>
          <input
            class="music-bar-range"
            type="range"
            min="0"
            :max="store.duration || 0"
            :value="store.currentTime"
            :disabled="!store.audioSrc"
            @input="onSeek"
            :style="{ '--slider-progress': `${(store.currentTime / (store.duration || 1)) * 100}%` }"
          />
          <span class="music-bar-time">{{ formatDuration(store.duration) }}</span>
        </div>

        <div class="music-bar-actions">
          <button
            class="music-bar-btn"
            :class="{ 'text-primary': store.shuffle }"
            title="随机播放"
            @click="store.shuffle = !store.shuffle"
          >
            <AppIcon name="shuffle" class="h-4 w-4" />
          </button>
          <button
            class="music-bar-btn"
            :class="{ 'text-primary': store.repeat !== 'none' }"
            :title="repeatTitle"
            @click="cycleRepeat"
          >
            <AppIcon v-if="store.repeat === 'one'" name="repeatOne" class="h-4 w-4" />
            <AppIcon v-else name="refresh" class="h-4 w-4" />
          </button>
          <div class="music-bar-volume">
            <button class="music-bar-btn" title="音量" @click="toggleMute">
              <AppIcon :name="volumeIcon" class="h-4 w-4" />
            </button>
            <input
              class="music-bar-range music-bar-range--volume"
              type="range"
              min="0"
              max="1"
              step="0.05"
              :value="store.volume"
              @input="onVolume"
              :style="{ '--slider-progress': `${store.volume * 100}%` }"
            />
          </div>
        </div>
      </div>
    </div>
  </Transition>

  <!-- Immersive Fullscreen Player Modal -->
  <Transition
    enter-active-class="transition-all duration-500 ease-out"
    leave-active-class="transition-all duration-350 ease-in"
    enter-from-class="translate-y-full opacity-0 scale-95"
    leave-to-class="translate-y-full opacity-0 scale-95"
  >
    <div v-if="showImmersive" class="immersive-player">
      <!-- High-saturation ambient color background -->
      <div 
        class="immersive-bg" 
        v-if="store.currentTrack?.cover" 
        :style="{ backgroundImage: `url(${store.currentTrack.cover})` }"
      ></div>
      <div class="immersive-overlay"></div>

      <!-- Main Layout -->
      <div class="immersive-container">
        <!-- Top Toolbar -->
        <header class="immersive-header">
          <button class="immersive-close-btn" @click="closeImmersive" title="收起">
            <AppIcon name="chevronDown" class="h-5 w-5" />
          </button>
          <div class="immersive-header-title">正在播放</div>
          <div class="w-10"></div> <!-- Placeholder for layout balance -->
        </header>

        <!-- Dynamic Body -->
        <main class="immersive-body">
          <!-- Left Column: Album Art & Info -->
          <div class="immersive-left">
            <div class="immersive-art-wrapper" :class="{ 'immersive-art-wrapper--playing': store.playing }">
              <img
                v-if="store.currentTrack?.cover"
                :src="store.currentTrack.cover"
                alt=""
                class="immersive-cover"
              />
              <div v-else class="immersive-cover-fallback">
                <AppIcon name="playlistMusic" class="h-24 w-24 text-muted-foreground/30" />
              </div>
            </div>
            
            <div class="immersive-meta">
              <h2 class="immersive-title" :title="store.currentTrack?.title">{{ store.currentTrack?.title || '未知歌曲' }}</h2>
              <p class="immersive-artist">{{ store.currentTrack?.artist || '未知歌手' }}</p>
              <p v-if="store.currentTrack?.album" class="immersive-album">{{ store.currentTrack.album }}</p>
            </div>

            <!-- Controls (under cover on desktop/mobile) -->
            <div class="immersive-controls-section">
              <div class="immersive-progress-wrap">
                <span class="immersive-time">{{ formatDuration(store.currentTime) }}</span>
                <input
                  class="immersive-range immersive-range--seek"
                  type="range"
                  min="0"
                  :max="store.duration || 0"
                  :value="store.currentTime"
                  :disabled="!store.audioSrc"
                  @input="onSeek"
                  :style="{ '--slider-progress': `${(store.currentTime / (store.duration || 1)) * 100}%` }"
                />
                <span class="immersive-time">{{ formatDuration(store.duration) }}</span>
              </div>

              <div class="immersive-buttons">
                <button
                  class="immersive-btn"
                  :class="{ 'immersive-btn--active': store.shuffle }"
                  title="随机播放"
                  @click="store.shuffle = !store.shuffle"
                >
                  <AppIcon name="shuffle" class="h-5 w-5" />
                </button>
                <button
                  class="immersive-btn"
                  :disabled="!canStep"
                  title="上一首"
                  @click="store.playPrevious()"
                >
                  <AppIcon name="previous" class="h-5 w-5" />
                </button>
                <button
                  class="immersive-btn immersive-btn--play"
                  :disabled="store.resolvingUrl"
                  title="播放/暂停"
                  @click="store.togglePlayback()"
                >
                  <AppIcon v-if="store.resolvingUrl" name="loadingSpinner" class="h-6 w-6 animate-spin" stroke-width="2.5" />
                  <AppIcon v-else-if="store.playing" name="pause" class="h-6 w-6 fill-current" />
                  <AppIcon v-else name="play" class="h-6 w-6 fill-current" />
                </button>
                <button
                  class="immersive-btn"
                  :disabled="!canStep"
                  title="下一首"
                  @click="store.playNext()"
                >
                  <AppIcon name="next" class="h-5 w-5" />
                </button>
                <button
                  class="immersive-btn"
                  :class="{ 'immersive-btn--active': store.repeat !== 'none' }"
                  :title="repeatTitle"
                  @click="cycleRepeat"
                >
                  <AppIcon v-if="store.repeat === 'one'" name="repeatOne" class="h-5 w-5" />
                  <AppIcon v-else name="refresh" class="h-5 w-5" />
                </button>
              </div>

            </div>
          </div>

          <!-- Right Column: Scrollable Immersive Lyrics -->
          <div class="immersive-right">
            <div class="immersive-lyrics-box" ref="lyricsContainer">
              <div v-if="store.lyricLoading" class="immersive-lyric-state">
                <AppIcon name="loadingSpinner" class="h-6 w-6 animate-spin" />
                <span>歌词加载中...</span>
              </div>
              <div v-else-if="store.lyricError" class="immersive-lyric-state text-destructive">
                <span>{{ store.lyricError }}</span>
              </div>
              <div v-else-if="store.lyricLines.length === 0" class="immersive-lyric-state">
                <span>暂无歌词</span>
              </div>
              <div v-else class="immersive-lyric-scrollable">
                <p
                  v-for="(line, index) in store.lyricLines"
                  :key="`${line.time}-${index}`"
                  class="immersive-lyric-line"
                  :class="{ 'immersive-lyric-line--active': index === store.currentLyricIndex }"
                  @click="seekToLine(line.time)"
                >
                  {{ line.text || '·' }}
                </p>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/common/AppIcon.vue'
import { useMusicPlayerStore } from '@/stores/musicPlayer'
import { Logger } from '@/utils/logger'

const store = useMusicPlayerStore()
const router = useRouter()

const audioEl = ref<HTMLAudioElement | null>(null)

const canStep = computed(() => store.queue.length > 1)

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

let previousVolume = 0.7

function goToMusic() {
  router.push('/music')
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

const formatDuration = (seconds: number) => {
  if (!seconds || Number.isNaN(seconds)) return '00:00'
  const rounded = Math.floor(seconds)
  const minutes = Math.floor(rounded / 60)
  const rest = rounded % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

function cycleRepeat() {
  if (store.repeat === 'none') store.repeat = 'all'
  else if (store.repeat === 'all') store.repeat = 'one'
  else store.repeat = 'none'
}

const showImmersive = ref(false)
const lyricsContainer = ref<HTMLElement | null>(null)

function openImmersive() {
  showImmersive.value = true
  document.body.style.overflow = 'hidden' // Lock body scroll
}

function closeImmersive() {
  showImmersive.value = false
  document.body.style.overflow = '' // Restore body scroll
}

function seekToLine(time: number) {
  store.seekTo(time)
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape' && showImmersive.value) {
    closeImmersive()
  }
}

watch(() => store.currentLyricIndex, (idx) => {
  if (!showImmersive.value || idx === -1 || !lyricsContainer.value) return
  setTimeout(() => {
    const container = lyricsContainer.value
    const activeEl = container?.querySelector<HTMLElement>('.immersive-lyric-line--active')
    if (!container || !activeEl) return

    const containerRect = container.getBoundingClientRect()
    const activeRect = activeEl.getBoundingClientRect()
    const top = container.scrollTop
      + activeRect.top
      - containerRect.top
      - (container.clientHeight - activeRect.height) / 2

    container.scrollTo({ top: Math.max(0, top), behavior: 'smooth' })
  }, 50)
})

onMounted(() => {
  store.setAudioRef(audioEl.value)
  window.addEventListener('keydown', handleKeyDown)
})

watch(audioEl, (el) => {
  store.setAudioRef(el)
})

watch(() => store.audioSrc, (src) => {
  if (!audioEl.value) return
  if (src) {
    audioEl.value.src = src
    audioEl.value.volume = store.volume
    audioEl.value.play().catch((err) => Logger.error('Failed to play music audio', err))
  }
})

onUnmounted(() => {
  store.setAudioRef(null)
  window.removeEventListener('keydown', handleKeyDown)
  document.body.style.overflow = ''
})
</script>

<style scoped>
.music-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 60;
  height: 4rem;
  border-top: 1px solid hsl(var(--border) / 0.35);
  background: hsl(var(--background) / 0.85);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  padding: 0 1.5rem;
  transition: left 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.music-bar--immersive {
  visibility: hidden;
  pointer-events: none;
}

@media (min-width: 768px) {
  .music-bar {
    left: var(--sidebar-width, 240px);
  }
}

.music-bar-inner {
  display: flex;
  height: 100%;
  align-items: center;
  gap: 1.25rem;
  max-width: 1280px;
  margin: 0 auto;
}

.music-bar-track {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  border-radius: 0.375rem;
  padding: 0.375rem;
  border: none;
  background: none;
  color: inherit;
  text-align: left;
  transition: background-color 0.15s ease;
}

.music-bar-track:hover {
  background: hsl(var(--muted) / 0.5);
}

.music-bar-cover {
  display: flex;
  width: 2.5rem;
  height: 2.5rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 0.25rem;
  background: hsl(var(--muted) / 0.4);
}

.music-bar-controls {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-shrink: 0;
}

.music-bar-btn {
  display: flex;
  height: 2rem;
  width: 2rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  border: none;
  background: none;
  color: hsl(var(--foreground));
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
  position: relative;
}

.music-bar-btn:hover {
  background: hsl(var(--muted) / 0.6);
}

.music-bar-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.music-bar-btn--play {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 9999px;
  background: linear-gradient(135deg, hsl(var(--primary)), hsl(var(--primary) / 0.9));
  color: hsl(var(--primary-foreground));
  border: none;
  box-shadow:
    0 2px 8px hsl(var(--primary) / 0.18),
    0 0 0 3px hsl(var(--primary) / 0.06);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.music-bar-btn--play:hover {
  background: linear-gradient(135deg, hsl(var(--primary) / 0.92), hsl(var(--primary) / 0.82));
  box-shadow:
    0 4px 16px hsl(var(--primary) / 0.28),
    0 0 0 6px hsl(var(--primary) / 0.08);
  transform: scale(1.05);
}

.music-bar-btn--play:active {
  transform: scale(0.96);
}

.music-bar-btn--play:disabled {
  background: linear-gradient(135deg, hsl(var(--muted-foreground) / 0.25), hsl(var(--muted-foreground) / 0.18));
  color: hsl(var(--muted-foreground) / 0.4);
  box-shadow: none;
}

.music-bar-progress-wrap {
  display: flex;
  flex: 2;
  align-items: center;
  gap: 0.625rem;
  min-width: 8rem;
}

.music-bar-time {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground) / 0.85);
  tabular-nums: normal;
  flex-shrink: 0;
  min-width: 3ch;
}

.music-bar-range {
  -webkit-appearance: none;
  appearance: none;
  flex: 1;
  height: 3px;
  border-radius: 9999px;
  background: linear-gradient(to right, hsl(var(--primary)) var(--slider-progress, 0%), hsl(var(--border) / 0.45) var(--slider-progress, 0%));
  outline: none;
  cursor: pointer;
  min-width: 0;
  transition: height 0.1s ease;
}

.music-bar-range:hover {
  height: 5px;
}

.music-bar-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 9px;
  height: 9px;
  border-radius: 9999px;
  background: hsl(var(--primary));
  border: none;
  opacity: 0;
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.music-bar-range:hover::-webkit-slider-thumb {
  opacity: 1;
  transform: scale(1.1);
}

.music-bar-range--volume {
  width: 4.5rem;
  flex: none;
  background: linear-gradient(to right, hsl(var(--foreground)) var(--slider-progress, 0%), hsl(var(--border) / 0.45) var(--slider-progress, 0%));
}

.music-bar-range--volume::-webkit-slider-thumb {
  background: hsl(var(--foreground));
}

.music-bar-actions {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-shrink: 0;
}

.music-bar-volume {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.music-bar-badge {
  position: absolute;
  top: 0.15rem;
  right: 0.15rem;
  font-size: 0.55rem;
  line-height: 1;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  padding: 1px 3px;
  border-radius: 9999px;
}

@media (max-width: 767px) {
  .music-bar {
    bottom: var(--mobile-nav-height);
    left: 0 !important;
  }

  .music-bar-progress-wrap,
  .music-bar-actions {
    display: none;
  }
}

/* Immersive Player Fullscreen Overlay */
.immersive-player {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100dvh;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  overflow: hidden;
  overscroll-behavior: contain;
}

/* Ambient Backlight Blur */
.immersive-bg {
  position: absolute;
  top: -20%;
  left: -20%;
  width: 140%;
  height: 140%;
  background-size: cover;
  background-position: center;
  filter: blur(90px) saturate(2.5) brightness(0.95);
  opacity: 0.65;
  transform: translateZ(0);
  pointer-events: none;
  z-index: 1;
}

.immersive-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(
    circle at 50% 50%,
    transparent 0%,
    hsl(var(--background) / 0.5) 60%,
    hsl(var(--background) / 0.95) 100%
  );
  pointer-events: none;
  z-index: 2;
}

.immersive-container {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem;
}

/* Header */
.immersive-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 3.5rem;
  margin-bottom: 2rem;
  flex-shrink: 0;
}

.immersive-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 9999px;
  border: none;
  background: hsl(var(--foreground) / 0.05);
  color: hsl(var(--foreground));
  cursor: pointer;
  transition: all 0.2s ease;
}

.immersive-close-btn:hover {
  background: hsl(var(--foreground) / 0.1);
  transform: translateY(2px);
}

.immersive-header-title {
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: hsl(var(--foreground) / 0.5);
}

/* Body Split */
.immersive-body {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 4rem;
  flex: 1;
  min-height: 0;
  align-items: center;
}

/* Left Side */
.immersive-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 0;
  height: 100%;
  gap: 2rem;
}

@keyframes coverFloat {
  0% {
    transform: translateY(0) scale(1);
    box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.2);
  }
  50% {
    transform: translateY(-8px) scale(1.015);
    box-shadow: 0 30px 50px -8px rgba(0, 0, 0, 0.25);
  }
  100% {
    transform: translateY(0) scale(1);
    box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.2);
  }
}

.immersive-art-wrapper {
  position: relative;
  width: min(24rem, 80vw);
  aspect-ratio: 1;
  border-radius: 1rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.2);
  box-shadow: 0 20px 40px -10px rgba(0,0,0,0.2);
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.immersive-art-wrapper--playing {
  animation: coverFloat 6s ease-in-out infinite;
}

.immersive-art-wrapper:hover {
  transform: scale(1.02);
}

.immersive-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.immersive-cover-fallback {
  display: flex;
  width: 100%;
  height: 100%;
  align-items: center;
  justify-content: center;
}

.immersive-meta {
  width: min(24rem, 80vw);
  text-align: left;
}

.immersive-title {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.immersive-artist {
  font-size: 1rem;
  font-weight: 500;
  color: hsl(var(--primary));
  margin-top: 0.375rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.immersive-album {
  font-size: 0.8125rem;
  color: hsl(var(--foreground) / 0.45);
  margin-top: 0.125rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Controls inside Immersive */
.immersive-controls-section {
  width: min(24rem, 80vw);
}

.immersive-progress-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.immersive-time {
  font-size: 0.75rem;
  font-family: monospace;
  color: hsl(var(--foreground) / 0.45);
  min-width: 4ch;
  text-align: center;
}

.immersive-range {
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  border-radius: 9999px;
  outline: none;
  cursor: pointer;
  transition: height 0.15s ease;
}

.immersive-range:hover {
  height: 6px;
}

.immersive-range--seek {
  flex: 1;
  background: linear-gradient(
    to right,
    hsl(var(--primary)) var(--slider-progress, 0%),
    hsl(var(--foreground) / 0.15) var(--slider-progress, 0%)
  );
}

.immersive-range--seek::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  background: hsl(var(--primary));
  opacity: 0;
  transition: opacity 0.15s ease;
}

.immersive-range--seek:hover::-webkit-slider-thumb {
  opacity: 1;
}

.immersive-buttons {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 1.25rem;
  padding: 0 0.5rem;
}

.immersive-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 9999px;
  border: none;
  background: none;
  color: hsl(var(--foreground) / 0.65);
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.immersive-btn:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--foreground) / 0.05);
}

.immersive-btn:disabled {
  opacity: 0.25;
  cursor: not-allowed;
}

.immersive-btn--active {
  color: hsl(var(--primary)) !important;
}

.immersive-btn--play {
  width: 3.5rem;
  height: 3.5rem;
  background: linear-gradient(135deg, hsl(var(--primary)), hsl(var(--primary) / 0.88));
  color: hsl(var(--primary-foreground));
  border: none;
  box-shadow:
    0 4px 20px hsl(var(--primary) / 0.22),
    0 0 0 5px hsl(var(--primary) / 0.05);
}

.immersive-btn--play:hover {
  background: linear-gradient(135deg, hsl(var(--primary) / 0.92), hsl(var(--primary) / 0.8));
  color: hsl(var(--primary-foreground));
  transform: scale(1.05);
  box-shadow:
    0 6px 32px hsl(var(--primary) / 0.32),
    0 0 0 10px hsl(var(--primary) / 0.07);
}

.immersive-btn--play:active {
  transform: scale(0.95);
}

.immersive-btn--play:disabled {
  background: linear-gradient(135deg, hsl(var(--muted-foreground) / 0.22), hsl(var(--muted-foreground) / 0.15));
  color: hsl(var(--muted-foreground) / 0.3);
  box-shadow: none;
}

.immersive-badge {
  position: absolute;
  top: 0.4rem;
  right: 0.4rem;
  font-size: 0.55rem;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  padding: 1px 3px;
  border-radius: 9999px;
}

/* Right Side: Lyrics Box */
.immersive-right {
  height: 100%;
  display: flex;
  align-items: center;
  min-width: 0;
}

.immersive-lyrics-box {
  width: 100%;
  height: min(34rem, 75vh);
  overflow-y: auto;
  mask-image: linear-gradient(
    to bottom,
    transparent 0%,
    black 15%,
    black 85%,
    transparent 100%
  );
  -webkit-mask-image: linear-gradient(
    to bottom,
    transparent 0%,
    black 15%,
    black 85%,
    transparent 100%
  );
  padding: 4rem 1rem;
}

/* Hide scrollbar but keep scroll behavior */
.immersive-lyrics-box::-webkit-scrollbar {
  display: none;
}

.immersive-lyrics-box {
  scrollbar-width: none;
}

.immersive-lyric-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 0.75rem;
  color: hsl(var(--foreground) / 0.45);
  font-size: 1.125rem;
}

.immersive-lyric-scrollable {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
  padding: 2rem 0;
}

.immersive-lyric-line {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.5;
  color: hsl(var(--foreground) / 0.38);
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  text-align: left;
  transform-origin: left center;
  padding: 0.5rem 0;
}

.immersive-lyric-line:hover {
  color: hsl(var(--foreground) / 0.75);
}

.immersive-lyric-line--active {
  color: hsl(var(--foreground)) !important;
  font-size: 2rem;
  font-weight: 800;
  transform: scale(1.03);
  text-shadow: 0 4px 24px hsl(var(--foreground) / 0.08);
}

/* Responsive Stacking */
@media (max-width: 868px) {
  .immersive-body {
    grid-template-columns: 1fr;
    gap: 2rem;
    overflow-y: auto;
    align-items: start;
    padding-bottom: 2rem;
  }
  
  .immersive-left {
    height: auto;
    padding-top: 1rem;
  }
  
  .immersive-art-wrapper {
    width: min(15rem, 60vw);
  }
  
  .immersive-meta {
    width: 100%;
    text-align: center;
  }
  
  .immersive-controls-section {
    width: 100%;
  }
  
  .immersive-right {
    height: auto;
  }
  
  .immersive-lyrics-box {
    height: 18rem;
    padding: 2rem 0.5rem;
  }
  
  .immersive-lyric-line {
    font-size: 1.125rem;
    text-align: center;
    transform-origin: center center;
  }
  
  .immersive-lyric-line--active {
    font-size: 1.375rem;
  }
}
</style>
