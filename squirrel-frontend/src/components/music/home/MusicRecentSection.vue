<template>
  <section v-if="tracks.length" class="music-recent-section">
    <header class="music-recent-header">
      <h2 class="music-recent-title">最近播放</h2>
      <button class="music-recent-more" @click="$emit('view-all')">
        查看全部
      </button>
    </header>

    <div class="music-recent-list">
      <article
        v-for="(track, index) in tracks"
        :key="track.hash"
        class="music-recent-item"
        :class="{ 'music-recent-item--playing': isPlaying(track) }"
        @click="$emit('play-track', track)"
      >
        <div class="music-recent-cover">
          <img v-if="track.cover" :src="track.cover" alt="" loading="lazy" />
          <AppIcon v-else name="playlistMusic" class="h-4 w-4" />
        </div>
        <div class="music-recent-info">
          <span class="music-recent-name">{{ track.title || '未知歌曲' }}</span>
          <span class="music-recent-artist">{{ track.artist || '未知歌手' }}</span>
        </div>
        <span class="music-recent-index">{{ index + 1 }}</span>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue'
import { useMusicPlayerStore } from '@/stores/musicPlayer'
import type { MusicTrack } from '@/api/music'

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
  margin-bottom: 2rem;
}

.music-recent-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.music-recent-title {
  font-size: 0.9375rem;
  font-weight: 700;
  color: hsl(var(--foreground));
}

.music-recent-more {
  font-size: 0.75rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  transition: all 0.15s ease;
}

.music-recent-more:hover {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.06);
}

.music-recent-list {
  display: flex;
  gap: 0.75rem;
}

.music-recent-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.875rem;
  background: hsl(var(--card) / 0.6);
  border: 1px solid hsl(var(--border) / 0.4);
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.2s ease;
  flex: 1;
  min-width: 0;
}

.music-recent-item:hover {
  border-color: hsl(var(--primary) / 0.2);
  background: hsl(var(--card));
  box-shadow: 0 4px 16px hsl(var(--foreground) / 0.06);
}

.music-recent-item--playing {
  border-color: hsl(var(--primary) / 0.25);
  background: hsl(var(--primary) / 0.04);
}

.music-recent-cover {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.5rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: hsl(var(--muted-foreground) / 0.5);
  box-shadow: 0 2px 8px hsl(var(--foreground) / 0.06);
}

.music-recent-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-recent-info {
  flex: 1;
  min-width: 0;
}

.music-recent-name {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-recent-item--playing .music-recent-name {
  color: hsl(var(--primary));
}

.music-recent-artist {
  display: block;
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
  margin-top: 0.125rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-recent-index {
  font-size: 0.625rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground) / 0.5);
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .music-recent-list {
    flex-direction: column;
  }

  .music-recent-item {
    flex: none;
  }
}
</style>