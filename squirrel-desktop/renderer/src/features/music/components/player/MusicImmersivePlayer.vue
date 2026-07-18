<template>
  <Transition
    enter-active-class="transition-[transform,opacity] duration-300 ease-out"
    leave-active-class="transition-[transform,opacity] duration-200 ease-in"
    enter-from-class="translate-y-full opacity-0 scale-95"
    leave-to-class="translate-y-full opacity-0 scale-95"
  >
    <div v-if="visible" class="immersive-player">
      <div
        v-if="track?.cover"
        class="immersive-bg"
        :style="{ backgroundImage: `url(${track.cover})` }"
      />
      <div class="immersive-overlay" />

      <div class="immersive-container">
        <header class="immersive-header">
          <Button text severity="secondary" icon-only title="关闭" aria-label="关闭沉浸播放" @click="$emit('close')">
            <AppIcon name="chevronDown" class="h-5 w-5" />
          </Button>
          <div class="immersive-header-title">正在播放</div>
          <div class="w-10" />
        </header>

        <main class="immersive-body">
          <div class="immersive-content">
            <MusicLyricsPanel
              v-if="activeTab === 'lyrics'"
              :lines="lyricLines"
              :current-index="currentLyricIndex"
              :loading="lyricLoading"
              :error="lyricError"
              @seek="$emit('seek', $event)"
            />

            <MusicCommentsPanel
              v-if="activeTab === 'comments'"
              :comments="comments"
              :loading="commentsLoading"
              :error="commentsError"
              :has-more="commentsHasMore"
              @load-more="$emit('load-more-comments')"
            />
          </div>

          <div class="immersive-bottom">
            <div class="immersive-meta">
              <div class="immersive-art-wrapper" :class="{ 'immersive-art-wrapper--playing': playing }">
                <img v-if="track?.cover" :src="track.cover" :alt="track?.title || '封面'" class="immersive-cover" />
                <div v-else class="immersive-cover-fallback">
                  <AppIcon name="playlistMusic" class="h-12 w-12" />
                </div>
              </div>
              <div class="immersive-track-info">
                <h2 class="immersive-title">{{ track?.title || '未知歌曲' }}</h2>
                <p v-if="error" class="immersive-error" :title="error">{{ error }}</p>
                <p v-else class="immersive-artist">{{ track?.artist || '未知歌手' }}</p>
                <p v-if="track?.album" class="immersive-album">{{ track.album }}</p>
              </div>
            </div>

            <div class="immersive-controls">
              <div class="immersive-progress-wrap">
                <span class="immersive-time">{{ formatDuration(currentTime) }}</span>
                <input
                  class="immersive-range"
                  type="range"
                  min="0"
                  :max="duration || 0"
                  :value="currentTime"
                  :disabled="!audioSrc"
                  :style="{ '--slider-progress': `${(currentTime / (duration || 1)) * 100}%` }"
                  @input="$emit('seek-input', Number(($event.target as HTMLInputElement).value))"
                />
                <span class="immersive-time">{{ formatDuration(duration) }}</span>
              </div>

              <div class="immersive-buttons">
                <Button
                  text severity="secondary"
                  icon-only
                  :class="{ 'text-primary': shuffle }"
                  title="随机播放"
                  aria-label="随机播放"
                  :aria-pressed="shuffle"
                  @click="$emit('toggle-shuffle')"
                >
                  <AppIcon name="shuffle" class="h-5 w-5" />
                </Button>
                <Button text severity="secondary" icon-only :disabled="!canStep" title="上一首" aria-label="上一首" @click="$emit('previous')">
                  <AppIcon name="previous" class="h-5 w-5" />
                </Button>
                <Button size="lg" icon-only rounded :disabled="loading" :title="playing ? '暂停' : '播放'" :aria-label="playing ? '暂停' : '播放'" :aria-pressed="playing" @click="$emit('toggle')">
                  <AppSpinner v-if="loading" size="lg" />
                  <AppIcon v-else-if="playing" name="pause" class="h-6 w-6" />
                  <AppIcon v-else name="play" class="h-6 w-6" />
                </Button>
                <Button text severity="secondary" icon-only :disabled="!canStep" title="下一首" aria-label="下一首" @click="$emit('next')">
                  <AppIcon name="next" class="h-5 w-5" />
                </Button>
                <Button
                  text severity="secondary"
                  icon-only
                  :class="{ 'text-primary': repeat !== 'none' }"
                  :title="repeat === 'one' ? '单曲循环' : '列表循环'"
                  :aria-label="repeat === 'one' ? '单曲循环' : '列表循环'"
                  :aria-pressed="repeat !== 'none'"
                  @click="$emit('toggle-repeat')"
                >
                  <AppIcon v-if="repeat === 'one'" name="repeatOne" class="h-5 w-5" />
                  <AppIcon v-else name="refresh" class="h-5 w-5" />
                </Button>
              </div>
            </div>

            <div class="immersive-tabs">
              <AppSegmentedControl
                :model-value="activeTab"
                :options="tabOptions"
                aria-label="播放详情"
                size="sm"
                @update:model-value="handleTabChange"
              />
              <Badge v-if="commentCount > 0" class="immersive-tab-badge">
                {{ commentCount > 999 ? '999+' : commentCount }}
              </Badge>
            </div>
          </div>
        </main>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { formatPlaybackTime as formatDuration } from '@/features/music/lib/musicFormatters'
import MusicLyricsPanel from './MusicLyricsPanel.vue'
import MusicCommentsPanel from './MusicCommentsPanel.vue'
import type { MusicTrack, MusicLyricLine, MusicComment } from '@/shared/api/music'

withDefaults(defineProps<{
  visible: boolean
  track?: MusicTrack | null
  playing?: boolean
  loading?: boolean
  shuffle?: boolean
  repeat?: 'none' | 'all' | 'one'
  canStep?: boolean
  currentTime?: number
  duration?: number
  audioSrc?: string
  error?: string
  lyricLines?: MusicLyricLine[]
  currentLyricIndex?: number
  lyricLoading?: boolean
  lyricError?: string
  comments?: MusicComment[]
  commentsLoading?: boolean
  commentsError?: string
  commentsHasMore?: boolean
  commentCount?: number
}>(), {
  track: null,
  playing: false,
  loading: false,
  shuffle: false,
  repeat: 'none',
  canStep: false,
  currentTime: 0,
  duration: 0,
  audioSrc: '',
  error: '',
  lyricLines: () => [],
  currentLyricIndex: -1,
  lyricLoading: false,
  lyricError: '',
  comments: () => [],
  commentsLoading: false,
  commentsError: '',
  commentsHasMore: false,
  commentCount: 0,
})

const activeTab = ref<'lyrics' | 'comments'>('lyrics')
const tabOptions = [
  { label: '歌词', value: 'lyrics' },
  { label: '评论', value: 'comments' },
]

const emit = defineEmits<{
  close: []
  seek: [time: number]
  'seek-input': [time: number]
  toggle: []
  previous: []
  next: []
  'toggle-shuffle': []
  'toggle-repeat': []
  'switch-comments': []
  'load-more-comments': []
}>()

const handleTabChange = (value: string | number) => {
  activeTab.value = value as 'lyrics' | 'comments'
  if (value === 'comments') emit('switch-comments')
}

// ponytail: formatDuration is the player-surface variant (zero-padded mm:ss)
// from the shared musicFormatters lib, deduped from 5 components.
</script>

<style scoped>
.immersive-player {
  position: fixed;
  inset: 0;
  z-index: var(--z-player-overlay);
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  overflow: hidden;
  overscroll-behavior: contain;
}

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
  inset: 0;
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
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem;
}

.immersive-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 3rem;
  margin-bottom: 1.5rem;
  flex-shrink: 0;
}

.immersive-header-title {
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.2;
  color: hsl(var(--muted-foreground));
}

.immersive-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.immersive-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.immersive-bottom {
  flex-shrink: 0;
  padding-top: 1.5rem;
}

.immersive-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.immersive-art-wrapper {
  width: 4.5rem;
  height: 4.5rem;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: hsl(var(--muted) / 0.2);
  box-shadow: var(--app-floating-shadow);
  flex-shrink: 0;
}

.immersive-art-wrapper--playing {
  animation: coverFloat 6s ease-in-out infinite;
}

@keyframes coverFloat {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-4px) scale(1.02); }
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
  color: hsl(var(--muted-foreground) / 0.3);
}

.immersive-track-info {
  flex: 1;
  min-width: 0;
}

.immersive-title {
  font-size: 1.125rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.immersive-artist {
  font-size: 0.875rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  margin-top: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.immersive-error {
  margin-top: 0.25rem;
  overflow: hidden;
  color: hsl(var(--destructive));
  font-size: 0.8125rem;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.immersive-album {
  font-size: 0.75rem;
  color: hsl(var(--foreground) / 0.45);
  margin-top: 0.125rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.immersive-controls {
  margin-bottom: 1rem;
}

.immersive-progress-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.immersive-time {
  font-size: 0.6875rem;
  font-family: monospace;
  color: hsl(var(--foreground) / 0.45);
  min-width: 2.5rem;
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
  flex: 1;
  background: linear-gradient(
    to right,
    hsl(var(--primary)) var(--slider-progress, 0%),
    hsl(var(--foreground) / 0.15) var(--slider-progress, 0%)
  );
}

.immersive-range:hover {
  height: 6px;
}

.immersive-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  background: hsl(var(--primary));
  opacity: 0;
  transition: opacity 0.15s ease;
}

.immersive-range:hover::-webkit-slider-thumb {
  opacity: 1;
}

.immersive-buttons {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
}

.immersive-tabs {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
}

.immersive-tab-badge {
  margin-left: 0.375rem;
}
</style>
