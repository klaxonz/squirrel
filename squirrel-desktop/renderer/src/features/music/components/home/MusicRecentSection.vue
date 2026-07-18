<template>
  <section v-if="tracks.length" class="music-recent-section">
    <header class="music-recent-header">
      <div>
        <h2 class="music-recent-title">最近播放</h2>
        <p class="music-recent-description">继续刚才的收听</p>
      </div>
      <Button text severity="secondary" size="sm" @click="$emit('view-all')">
        查看全部
        <AppIcon name="chevronRight" class="h-3.5 w-3.5" />
      </Button>
    </header>

    <div class="music-recent-list">
      <button type="button"
        v-for="(track, index) in tracks"
        :key="track.hash"

        class="music-recent-item"
        :class="{ 'music-recent-item--playing': isPlaying(track) }"
        @click="$emit('play-track', track)"
      >
        <span class="music-recent-cover">
          <img v-if="track.cover" :src="track.cover" :alt="track.title || '封面'" loading="lazy" />
          <AppIcon v-else name="playlistMusic" class="h-4 w-4" />
        </span>
        <span class="music-recent-info">
          <span class="music-recent-name">{{ track.title || '未知歌曲' }}</span>
          <span class="music-recent-artist">{{ track.artist || '未知歌手' }}</span>
        </span>
        <MusicPlayingIndicator v-if="isPlaying(track)" />
        <span v-else class="music-recent-index">{{ String(index + 1).padStart(2, '0') }}</span>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import MusicPlayingIndicator from '../shared/MusicPlayingIndicator.vue'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import type { MusicTrack } from '@/shared/api/music'

defineProps<{
  tracks: MusicTrack[]
}>()

defineEmits<{
  'view-all': []
  'play-track': [track: MusicTrack]
}>()

const player = useMusicPlayerStore()

function isPlaying(track: MusicTrack): boolean {
  return player.currentTrack?.hash === track.hash
}
</script>

<style scoped>
.music-recent-section {
  margin-bottom: var(--space-7);
}

.music-recent-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-3);
}

.music-recent-title {
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: var(--app-h3-size);
  font-weight: var(--app-h3-weight);
  letter-spacing: 0;
  line-height: var(--app-h3-leading);
}

.music-recent-description {
  margin: 0.2rem 0 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.music-recent-list {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-lg);
  background: hsl(var(--card) / 0.38);
}

.music-recent-item {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-right: 1px solid var(--app-surface-border-subtle);
  color: hsl(var(--foreground));
  text-align: left;
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-default);
}

.music-recent-item:last-child {
  border-right: 0;
}

.music-recent-item:hover {
  background: hsl(var(--muted) / 0.36);
}

.music-recent-item:focus-visible {
  position: relative;
  z-index: 1;
  outline: 2px solid hsl(var(--ring));
  outline-offset: -2px;
}

.music-recent-cover {
  display: flex;
  width: 2.5rem;
  height: 2.5rem;
  flex: none;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.42);
  color: hsl(var(--muted-foreground) / 0.52);
}

.music-recent-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-recent-info {
  display: block;
  min-width: 0;
  flex: 1;
}

.music-recent-name,
.music-recent-artist {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-recent-name {
  font-size: 0.75rem;
  font-weight: 650;
}

.music-recent-item--playing .music-recent-name {
  color: hsl(var(--primary));
}

.music-recent-artist {
  margin-top: 0.125rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
}

.music-recent-index {
  flex: none;
  color: hsl(var(--muted-foreground) / 0.52);
  font-family: var(--font-mono);
  font-size: var(--app-text-badge-size);
}

@media (max-width: 1180px) {
  .music-recent-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .music-recent-item:nth-child(3) {
    border-right: 0;
  }

  .music-recent-item:nth-child(n + 4) {
    border-top: 1px solid var(--app-surface-border-subtle);
  }
}

@media (prefers-reduced-motion: reduce) {
  .music-recent-item {
    transition: none;
  }
}
</style>
