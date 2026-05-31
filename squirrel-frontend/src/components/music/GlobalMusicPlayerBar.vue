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
        <button class="music-bar-track" @click="goToMusic">
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
            <AppIcon v-if="store.resolvingUrl" name="loadingSpinner" class="h-5 w-5 animate-spin" />
            <AppIcon v-else-if="store.playing" name="pause" class="h-5 w-5 fill-current" />
            <AppIcon v-else name="play" class="h-5 w-5 fill-current" />
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
            <AppIcon v-if="store.repeat === 'one'" name="loop" class="h-4 w-4" />
            <AppIcon v-else name="refresh" class="h-4 w-4" />
            <sup v-if="store.repeat === 'one'" class="music-bar-badge">1</sup>
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
            />
          </div>
        </div>
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

onMounted(() => {
  store.setAudioRef(audioEl.value)
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
  border-top: 1px solid hsl(var(--border) / 0.5);
  background: hsl(var(--background) / 0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 0 1rem;
}

.music-bar-inner {
  display: flex;
  height: 100%;
  align-items: center;
  gap: 0.75rem;
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
  padding: 0.25rem;
  border: none;
  background: none;
  color: inherit;
  text-align: left;
  transition: background 160ms ease;
}

.music-bar-track:hover {
  background: hsl(var(--accent) / 0.5);
}

.music-bar-cover {
  display: flex;
  width: 2.5rem;
  height: 2.5rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 0.375rem;
  background: hsl(var(--muted));
}

.music-bar-controls {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
}

.music-bar-btn {
  display: flex;
  height: 2.25rem;
  width: 2.25rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  border: none;
  background: none;
  color: hsl(var(--foreground));
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease;
  flex-shrink: 0;
}

.music-bar-btn:hover {
  background: hsl(var(--accent) / 0.6);
}

.music-bar-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.music-bar-btn--play {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 9999px;
  background: hsl(var(--foreground));
  color: hsl(var(--background));
}

.music-bar-btn--play:hover {
  background: hsl(var(--foreground) / 0.85);
}

.music-bar-btn--play:disabled {
  background: hsl(var(--muted-foreground));
}

.music-bar-progress-wrap {
  display: flex;
  flex: 2;
  align-items: center;
  gap: 0.5rem;
  min-width: 8rem;
}

.music-bar-time {
  font-size: 0.75rem;
  line-height: 1;
  color: hsl(var(--muted-foreground));
  tabular-nums: normal;
  flex-shrink: 0;
  min-width: 3ch;
}

.music-bar-range {
  flex: 1;
  height: 0.375rem;
  accent-color: hsl(var(--primary));
  cursor: pointer;
  min-width: 0;
}

.music-bar-range--volume {
  width: 4rem;
  flex: none;
}

.music-bar-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
}

.music-bar-volume {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.music-bar-badge {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  font-size: 0.625rem;
  line-height: 1;
}

@media (max-width: 767px) {
  .music-bar {
    bottom: var(--mobile-nav-height);
  }

  .music-bar-progress-wrap,
  .music-bar-actions {
    display: none;
  }
}
</style>
