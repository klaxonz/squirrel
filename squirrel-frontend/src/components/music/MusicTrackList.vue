<template>
  <div class="music-track-list">
    <header class="music-track-header">
      <span class="music-track-col music-track-col--num">#</span>
      <span class="music-track-col music-track-col--cover"></span>
      <span class="music-track-col music-track-col--title">标题</span>
      <span class="music-track-col music-track-col--album">专辑</span>
      <span class="music-track-col music-track-col--duration">时长</span>
      <span class="music-track-col music-track-col--actions"></span>
    </header>

    <article
      v-for="(track, index) in tracks"
      :key="track.hash || index"
      class="music-track-row"
      :class="{ 'music-track-row--playing': isPlaying(track) }"
      @click="handlePlay(track)"
      @dblclick="handlePlay(track)"
    >
      <div class="music-track-col music-track-col--num">
        <span v-if="isPlaying(track) && player.playing" class="music-track-playing">
          <i></i><i></i><i></i>
        </span>
        <span v-else class="music-track-num">{{ index + 1 }}</span>
      </div>

      <div class="music-track-col music-track-col--cover">
        <img v-if="track.cover" :src="track.cover" :alt="track.title" loading="lazy" />
        <div v-else class="music-track-cover-placeholder">
          <AppIcon name="playlistMusic" class="h-4 w-4" />
        </div>
      </div>

      <div class="music-track-col music-track-col--title">
        <div class="music-track-title-wrap">
          <span class="music-track-title">{{ track.title || '未知歌曲' }}</span>
          <span v-if="isPlaying(track)" class="music-track-playing-badge">正在播放</span>
        </div>
        <button
          class="music-track-artist"
          :disabled="!track.artist_id"
          @click.stop="$emit('select-artist', track)"
        >
          {{ track.artist || '未知歌手' }}
        </button>
      </div>

      <button
        class="music-track-col music-track-col--album"
        :disabled="!track.album_id"
        @click.stop="$emit('select-album', track)"
      >
        {{ track.album || '未知专辑' }}
      </button>

      <span class="music-track-col music-track-col--duration">
        {{ formatDuration(track.duration) }}
      </span>

      <div class="music-track-col music-track-col--actions">
        <button v-if="showMv" class="music-track-action" title="播放 MV" @click.stop="$emit('play-mv', track)">
          <AppIcon name="play" class="h-4 w-4" />
        </button>
        <button v-if="showRelated" class="music-track-action" title="相关歌曲" @click.stop="$emit('select-related', track)">
          <AppIcon name="list" class="h-4 w-4" />
        </button>
        <button v-if="showAddToPlaylist" class="music-track-action" title="添加到歌单" @click.stop="$emit('add-to-playlist', track)">
          <AppIcon name="addToPlaylist" class="h-4 w-4" />
        </button>
      </div>
    </article>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue'
import { useMusicPlayerStore } from '@/stores/musicPlayer'
import type { MusicTrack } from '@/api/music'

withDefaults(defineProps<{
  tracks: MusicTrack[]
  showMv?: boolean
  showRelated?: boolean
  showAddToPlaylist?: boolean
}>(), {
  showMv: true,
  showRelated: true,
  showAddToPlaylist: true,
})

defineEmits<{
  'select-artist': [track: MusicTrack]
  'select-album': [track: MusicTrack]
  'play-mv': [track: MusicTrack]
  'select-related': [track: MusicTrack]
  'add-to-playlist': [track: MusicTrack]
}>()

const player = useMusicPlayerStore()

function isPlaying(track: MusicTrack): boolean {
  return player.currentTrack?.hash === track.hash
}

function handlePlay(track: MusicTrack) {
  player.playTrack(track)
}

function formatDuration(seconds: number): string {
  if (!seconds || isNaN(seconds)) return '--:--'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}
</script>

<style scoped>
.music-track-list {
  display: flex;
  flex-direction: column;
}

.music-track-header {
  display: grid;
  grid-template-columns: 3rem 3rem 1fr minmax(0, 1fr) 4rem 4rem;
  gap: 1rem;
  align-items: center;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
  font-size: 0.6875rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.music-track-row {
  display: grid;
  grid-template-columns: 3rem 3rem 1fr minmax(0, 1fr) 4rem 4rem;
  gap: 1rem;
  align-items: center;
  padding: 0.625rem 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background 0.15s ease;
}

.music-track-row:hover {
  background: hsl(var(--muted) / 0.4);
}

.music-track-row--playing {
  background: hsl(var(--primary) / 0.08);
}

.music-track-col--num {
  text-align: center;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
}

.music-track-num {
  opacity: 0.6;
}

.music-track-row:hover .music-track-num {
  opacity: 0;
}

.music-track-playing {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 2px;
  height: 1rem;
}

.music-track-playing i {
  width: 3px;
  height: 100%;
  background: hsl(var(--primary));
  border-radius: 1px;
  animation: track-playing 0.6s ease-in-out infinite;
}

.music-track-playing i:nth-child(2) { animation-delay: 0.15s; }
.music-track-playing i:nth-child(3) { animation-delay: 0.3s; }

@keyframes track-playing {
  0%, 100% { transform: scaleY(0.4); }
  50% { transform: scaleY(1); }
}

.music-track-col--cover {
  width: 3rem;
  height: 3rem;
  border-radius: 0.375rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
}

.music-track-col--cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-track-cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
}

.music-track-col--title {
  min-width: 0;
}

.music-track-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.music-track-title {
  font-size: 0.9375rem;
  font-weight: 500;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-track-playing-badge {
  font-size: 0.625rem;
  padding: 0.125rem 0.375rem;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-radius: 0.25rem;
  flex-shrink: 0;
}

.music-track-artist {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-track-artist:hover:not(:disabled) {
  color: hsl(var(--foreground));
}

.music-track-artist:disabled {
  cursor: default;
}

.music-track-col--album {
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-track-col--album:hover:not(:disabled) {
  color: hsl(var(--foreground));
}

.music-track-col--duration {
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.music-track-col--actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.25rem;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.music-track-row:hover .music-track-col--actions {
  opacity: 1;
}

.music-track-action {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 0.375rem;
  background: none;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
}

.music-track-action:hover {
  background: hsl(var(--muted));
  color: hsl(var(--foreground));
}

@media (max-width: 768px) {
  .music-track-header,
  .music-track-row {
    grid-template-columns: 3rem 3rem 1fr 4rem;
  }

  .music-track-col--album {
    display: none;
  }

  .music-track-col--duration {
    display: none;
  }
}
</style>