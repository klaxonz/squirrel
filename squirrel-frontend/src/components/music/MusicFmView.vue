<template>
  <div class="music-fm-view">
    <div class="music-fm-layout">
      <div class="music-fm-left">
        <div class="music-fm-cover-container">
          <img
            v-if="store.currentTrack?.cover || batch[0]?.cover"
            :src="store.currentTrack?.cover || batch[0]?.cover"
            alt=""
            class="music-fm-cover-img"
          />
          <AppIcon v-else name="playlistMusic" class="h-24 w-24 text-muted-foreground/30" />
          <div v-if="!store.currentTrack && batch.length" class="music-fm-play-overlay-large" @click="playFirst">
            <AppIcon name="play" class="h-14 w-14 text-white drop-shadow-xl" />
          </div>
        </div>
      </div>

      <div class="music-fm-right">
        <div class="music-fm-meta" v-if="store.currentTrack || batch.length">
          <h1 class="music-fm-title">{{ store.currentTrack?.title || batch[0]?.title || '未知歌曲' }}</h1>
          <button
            class="music-fm-artist"
            :disabled="!store.currentTrack ? !batch[0]?.artist_id : !store.currentTrack.artist_id"
            @click="store.currentTrack ? $emit('select-artist', store.currentTrack) : null"
          >
            {{ store.currentTrack?.artist || batch[0]?.artist || '未知歌手' }}
          </button>
        </div>
        <div class="music-fm-meta" v-else-if="loading">
          <div class="h-12 bg-muted/30 rounded w-3/4 animate-pulse mb-2"></div>
          <div class="h-6 bg-muted/30 rounded w-1/3 animate-pulse"></div>
        </div>

        <div class="music-fm-actions">
          <template v-if="store.currentTrack">
            <button class="music-fm-btn-primary" title="下一首" @click="$emit('next')" :disabled="loading">
              <AppIcon name="next" class="h-6 w-6 mr-1.5" />
              下一首
            </button>
            <button class="music-fm-btn-circle" :class="{ 'text-rose-500': hearted[store.currentTrack.hash] }" title="喜欢" @click="$emit('like', store.currentTrack)" :disabled="liking">
              <AppIcon v-if="liking" name="loadingSpinner" class="h-6 w-6 animate-spin" />
              <AppIcon v-else name="heart" class="h-6 w-6" :class="{ 'fill-current': hearted[store.currentTrack.hash] }" />
            </button>
            <button class="music-fm-btn-circle" title="不喜欢" @click="$emit('dislike')" :disabled="loading">
              <AppIcon name="trash" class="h-6 w-6" />
            </button>
          </template>
          <template v-else-if="batch.length">
            <button class="music-fm-btn-primary" @click="playFirst">
              <AppIcon name="play" class="h-6 w-6 mr-1.5" />
              点击播放推荐电台
            </button>
          </template>
        </div>

        <div class="music-fm-divider"></div>

        <div class="music-fm-controls-bottom">
          <div class="music-fm-tabs">
            <button class="music-fm-tab" :class="{ 'music-fm-tab--active': mode === 'normal' }" @click="$emit('switch-mode', 'normal')">发现</button>
            <button class="music-fm-tab" :class="{ 'music-fm-tab--active': mode === 'small' }" @click="$emit('switch-mode', 'small')">小众</button>
            <button class="music-fm-tab" :class="{ 'music-fm-tab--active': mode === 'peak' }" @click="$emit('switch-mode', 'peak')">30s</button>
          </div>
          <div class="music-fm-pool">
            <button class="music-fm-chip" :class="{ 'music-fm-chip--active': poolId === '0' }" @click="$emit('switch-pool', '0')">口味推荐</button>
            <button class="music-fm-chip" :class="{ 'music-fm-chip--active': poolId === '1' }" @click="$emit('switch-pool', '1')">风格推荐</button>
            <button class="music-fm-chip" :class="{ 'music-fm-chip--active': poolId === '2' }" @click="$emit('switch-pool', '2')">Gamma</button>
          </div>
        </div>

        <p v-if="error" class="music-fm-error">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue'
import { useMusicPlayerStore } from '@/stores/musicPlayer'
import type { MusicTrack } from '@/api/music'

const props = defineProps<{
  batch: MusicTrack[]
  mode: string
  poolId: string
  hearted: Record<string, boolean>
  loading: boolean
  liking: boolean
  error: string
}>()

const emit = defineEmits<{
  'next': []
  'like': [track: MusicTrack]
  'dislike': []
  'switch-mode': [mode: string]
  'switch-pool': [poolId: string]
  'play-first': []
  'select-artist': [track: MusicTrack]
}>()

const store = useMusicPlayerStore()

function playFirst() {
  emit('play-first')
}
</script>

<style scoped>
.music-fm-view {
  padding: 1.5rem;
}

.music-fm-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3rem;
  max-width: 900px;
  margin: 0 auto;
}

.music-fm-left {
  display: flex;
  align-items: center;
  justify-content: center;
}

.music-fm-cover-container {
  position: relative;
  width: min(18rem, 70vw);
  aspect-ratio: 1;
}

.music-fm-cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 0.75rem;
  box-shadow: 0 16px 40px -12px rgba(0, 0, 0, 0.25);
}

.music-fm-play-overlay-large {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--foreground) / 0.2);
  border-radius: 0.75rem;
  cursor: pointer;
}

.music-fm-right {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1.5rem;
}

.music-fm-meta {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.music-fm-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: hsl(var(--foreground));
}

.music-fm-artist {
  font-size: 1rem;
  color: hsl(var(--primary));
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  transition: opacity 0.15s ease;
}

.music-fm-artist:hover:not(:disabled) {
  opacity: 0.8;
}

.music-fm-artist:disabled {
  opacity: 0.5;
  cursor: default;
}

.music-fm-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.music-fm-btn-primary {
  display: flex;
  align-items: center;
  padding: 0.75rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--primary-foreground));
  background: linear-gradient(135deg, hsl(var(--primary)), hsl(var(--primary) / 0.9));
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.music-fm-btn-primary:hover:not(:disabled) {
  transform: scale(1.05);
}

.music-fm-btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.music-fm-btn-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 9999px;
  border: 1px solid hsl(var(--border) / 0.5);
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.2s ease;
}

.music-fm-btn-circle:hover:not(:disabled) {
  background: hsl(var(--muted) / 0.5);
  color: hsl(var(--foreground));
}

.music-fm-btn-circle:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.music-fm-divider {
  width: 100%;
  height: 1px;
  background: hsl(var(--border) / 0.3);
}

.music-fm-controls-bottom {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}

.music-fm-tabs {
  display: flex;
  gap: 0.5rem;
}

.music-fm-tab {
  padding: 0.5rem 1rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  background: transparent;
  border: 1px solid hsl(var(--border) / 0.4);
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-fm-tab:hover {
  color: hsl(var(--foreground));
}

.music-fm-tab--active {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
  border-color: hsl(var(--primary) / 0.3);
}

.music-fm-pool {
  display: flex;
  gap: 0.375rem;
}

.music-fm-chip {
  padding: 0.375rem 0.75rem;
  font-size: 0.6875rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  background: transparent;
  border: 1px solid hsl(var(--border) / 0.3);
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-fm-chip:hover {
  color: hsl(var(--foreground));
}

.music-fm-chip--active {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
  border-color: hsl(var(--primary) / 0.3);
}

.music-fm-error {
  font-size: 0.8125rem;
  color: hsl(var(--destructive));
}

@media (max-width: 768px) {
  .music-fm-layout {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .music-fm-cover-container {
    width: min(12rem, 50vw);
  }
}
</style>