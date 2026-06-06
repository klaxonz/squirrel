<template>
  <section class="music-greeting">
    <div class="music-greeting-header">
      <div class="music-greeting-left">
        <div class="music-greeting-avatar">
          <img v-if="user?.avatar" :src="user.avatar" alt="" />
          <AppIcon v-else name="user" class="h-5 w-5" />
        </div>
        <div class="music-greeting-text">
          <h1 class="music-greeting-title">{{ greetingText }}</h1>
          <p class="music-greeting-subtitle">{{ subtitleText }}</p>
        </div>
      </div>
      <button
        v-if="recentTrack && !hasCurrentTrack"
        class="music-continue-button"
        @click="$emit('continue-play', recentTrack)"
      >
        <AppIcon name="play" class="h-3.5 w-3.5" />
        <span>继续播放</span>
        <strong>{{ recentTrack.title }}</strong>
      </button>
    </div>

    <div class="music-greeting-actions">
      <div class="music-fm-entry">
        <button class="music-fm-main" :class="{ 'music-fm-main--active': fmActive }" @click="$emit('fm-play')">
          <div class="music-fm-icon">
            <AppIcon v-if="fmPlaying" name="playlistMusic" class="h-5 w-5" />
            <AppIcon v-else name="star" class="h-5 w-5" />
          </div>
          <div class="music-fm-content">
            <span class="music-fm-label">私人FM</span>
            <span class="music-fm-meta">{{ fmStateText }}</span>
          </div>
          <span class="music-fm-play" :class="{ 'music-fm-play--active': fmPlaying }" :title="fmButtonTitle">
            <AppIcon v-if="fmLoading" name="loadingSpinner" class="h-4 w-4 animate-spin" />
            <AppIcon v-else-if="fmPlaying" name="pause" class="h-4 w-4" />
            <AppIcon v-else name="play" class="h-4 w-4" />
          </span>
        </button>

        <div class="music-fm-controls">
          <div class="music-fm-segment">
            <button
              v-for="modeOption in fmModes"
              :key="modeOption.value"
              class="music-fm-chip"
              :class="{ 'music-fm-chip--active': fmMode === modeOption.value }"
              @click="$emit('switch-fm-mode', modeOption.value)"
            >
              {{ modeOption.label }}
            </button>
          </div>
          <div class="music-fm-segment">
            <button
              v-for="poolOption in fmPools"
              :key="poolOption.value"
              class="music-fm-chip"
              :class="{ 'music-fm-chip--active': fmPoolId === poolOption.value }"
              @click="$emit('switch-fm-pool', poolOption.value)"
            >
              {{ poolOption.label }}
            </button>
          </div>
        </div>
      </div>
      <MusicActionButton
        icon="time"
        label="每日推荐"
        variant="daily"
        @click="$emit('everyday')"
      />
      <MusicActionButton
        icon="playlists"
        label="新歌速递"
        variant="rank"
        @click="$emit('new-songs')"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import MusicActionButton from './MusicActionButton.vue'
import type { MusicUserProfile, MusicTrack } from '@/api/music'

type FmMode = 'normal' | 'small' | 'peak'

const props = defineProps<{
  user?: MusicUserProfile | null
  recentTrack?: MusicTrack | null
  hasCurrentTrack?: boolean
  fmMode: FmMode
  fmPoolId: string
  fmLoading?: boolean
  fmActive?: boolean
  fmPlaying?: boolean
}>()

defineEmits<{
  'continue-play': [track: MusicTrack]
  'fm-play': []
  'everyday': []
  'new-songs': []
  'switch-fm-mode': [mode: FmMode]
  'switch-fm-pool': [poolId: string]
}>()

const fmModes = [
  { value: 'normal' as const, label: '发现' },
  { value: 'small' as const, label: '小众' },
  { value: 'peak' as const, label: '30s' },
]

const fmPools = [
  { value: '0', label: '口味' },
  { value: '1', label: '风格' },
  { value: '2', label: 'Gamma' },
]

const currentModeLabel = computed(() => fmModes.find(item => item.value === props.fmMode)!.label)
const currentPoolLabel = computed(() => fmPools.find(item => item.value === props.fmPoolId)!.label)
const fmStateText = computed(() => {
  const base = `${currentModeLabel.value} · ${currentPoolLabel.value}`
  if (props.fmLoading) return `加载中 · ${base}`
  if (props.fmPlaying) return `正在播放 · ${base}`
  if (props.fmActive) return `已暂停 · ${base}`
  return base
})
const fmButtonTitle = computed(() => {
  if (props.fmLoading) return '正在加载私人 FM'
  if (props.fmPlaying) return '暂停私人 FM'
  if (props.fmActive) return '继续私人 FM'
  return '播放私人 FM'
})

const greetingText = computed(() => {
  const hour = new Date().getHours()
  const name = props.user?.nickname || ''
  if (hour < 6) return name ? `${name}，夜深了` : '夜深了，还在听歌吗'
  if (hour < 12) return name ? `${name}，早上好` : '早上好'
  if (hour < 14) return name ? `${name}，中午好` : '中午好'
  if (hour < 18) return name ? `${name}，下午好` : '下午好'
  if (hour < 22) return name ? `${name}，晚上好` : '晚上好'
  return name ? `${name}，夜深了` : '夜深了'
})

const subtitleText = computed(() => {
  if (props.recentTrack && !props.hasCurrentTrack) {
    return `上次播放: ${props.recentTrack.title}`
  }
  return '今天想听点什么？'
})
</script>

<style scoped>
.music-greeting {
  padding: 1.5rem 0 2rem;
}

.music-greeting-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.music-greeting-left {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 0;
}

.music-greeting-avatar {
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 9999px;
  background: hsl(var(--muted) / 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: hsl(var(--muted-foreground));
}

.music-greeting-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-greeting-text {
  flex: 1;
  min-width: 0;
}

.music-greeting-title {
  font-size: 1.5rem;
  font-weight: 800;
  color: hsl(var(--foreground));
  letter-spacing: -0.03em;
  line-height: 1.2;
}

.music-greeting-subtitle {
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground) / 0.85);
  margin-top: 0.25rem;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-continue-button {
  display: flex;
  align-items: center;
  max-width: 22rem;
  min-width: 0;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 0.5rem;
  background: hsl(var(--card));
  color: hsl(var(--foreground) / 0.7);
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-continue-button:hover {
  border-color: hsl(var(--primary) / 0.3);
  color: hsl(var(--foreground));
  background: hsl(var(--muted) / 0.35);
}

.music-continue-button span {
  flex: 0 0 auto;
  font-size: 0.8125rem;
  font-weight: 650;
}

.music-continue-button strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.75rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
}

.music-greeting-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  gap: 1rem;
}

.music-fm-entry {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  padding: 1rem;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 1rem;
  background: hsl(var(--card));
}

.music-fm-main {
  display: flex;
  align-items: center;
  gap: 1rem;
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  color: hsl(var(--foreground));
  text-align: left;
  cursor: pointer;
}

.music-fm-main--active .music-fm-icon {
  background: hsl(var(--primary) / 0.12);
  color: hsl(var(--primary));
}

.music-fm-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 0.75rem;
  background: hsl(var(--accent));
  color: hsl(var(--foreground) / 0.7);
  flex-shrink: 0;
}

.music-fm-content {
  flex: 1;
  min-width: 0;
}

.music-fm-label {
  display: block;
  font-size: 0.9375rem;
  font-weight: 700;
}

.music-fm-meta {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground) / 0.8);
}

.music-fm-play {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 9999px;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  flex-shrink: 0;
}

.music-fm-main:hover .music-fm-play {
  background: hsl(var(--primary) / 0.9);
}

.music-fm-play--active {
  background: hsl(var(--foreground));
  color: hsl(var(--background));
}

.music-fm-main:hover .music-fm-play--active {
  background: hsl(var(--foreground) / 0.86);
}

.music-fm-controls {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.music-fm-segment {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.25rem;
}

.music-fm-chip {
  height: 1.75rem;
  border: none;
  border-radius: 0.375rem;
  background: hsl(var(--muted) / 0.35);
  color: hsl(var(--foreground) / 0.68);
  font-size: 0.6875rem;
  font-weight: 600;
  cursor: pointer;
}

.music-fm-chip:hover {
  background: hsl(var(--muted) / 0.55);
  color: hsl(var(--foreground));
}

.music-fm-chip--active {
  background: hsl(var(--primary) / 0.12);
  color: hsl(var(--primary));
}

@media (max-width: 768px) {
  .music-greeting-actions {
    grid-template-columns: 1fr;
  }
}
</style>
