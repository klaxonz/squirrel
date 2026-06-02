<template>
  <div class="music-playlist-detail">
    <header class="music-detail-header">
      <div class="music-detail-cover">
        <img :src="playlist.cover" :alt="playlist.name" loading="lazy" />
      </div>
      <div class="music-detail-info">
        <span class="music-detail-type">歌单</span>
        <h1 class="music-detail-name">{{ playlist.name }}</h1>
        <div class="music-detail-meta">
          <span v-if="playlist.creator">{{ playlist.creator }}</span>
          <span>{{ total }} 首歌</span>
          <span v-if="playlist.play_count">{{ formatCount(playlist.play_count) }}次播放</span>
        </div>
        <div class="music-detail-actions">
          <button class="music-action-btn music-action-btn--primary" @click="playAll">
            <AppIcon name="play" class="h-5 w-5" />
            播放全部
          </button>
          <button class="music-action-btn" :class="{ 'music-action-btn--active': shuffle }" @click="shuffleAll">
            <AppIcon name="shuffle" class="h-5 w-5" />
            随机
          </button>
          <button v-if="showCollect" class="music-action-btn" :class="{ 'music-action-btn--active': collected }" @click="$emit('collect')">
            <AppIcon name="heart" class="h-5 w-5" :class="{ 'fill-current': collected }" />
            {{ collected ? '已收藏' : '收藏' }}
          </button>
        </div>
      </div>
    </header>

    <div v-if="loading" class="music-detail-loading">
      <AppIcon name="loadingSpinner" class="h-6 w-6 animate-spin text-primary" />
      <span>加载中...</span>
    </div>

    <MusicTrackList
      v-else
      :tracks="tracks"
      :show-add-to-playlist="false"
      @select-artist="$emit('select-artist', $event)"
      @select-album="$emit('select-album', $event)"
      @play-mv="$emit('play-mv', $event)"
      @select-related="$emit('select-related', $event)"
    />

    <div v-if="hasMore" class="music-detail-load-more">
      <button class="music-load-more-btn" :disabled="loadingMore" @click="$emit('load-more')">
        <AppIcon v-if="loadingMore" name="loadingSpinner" class="h-4 w-4 animate-spin" />
        <span>加载更多</span>
      </button>
    </div>

    <section v-if="similar.length" class="music-similar-section">
      <h2 class="music-section-title">相似歌单</h2>
      <div class="music-similar-grid">
        <article
          v-for="item in similar"
          :key="item.id"
          class="music-similar-card"
          @click="$emit('change', item)"
        >
          <img :src="item.cover" :alt="item.name" loading="lazy" />
          <h3 class="music-similar-name">{{ item.name }}</h3>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import MusicTrackList from './MusicTrackList.vue'
import { useMusicPlayerStore } from '@/stores/musicPlayer'
import type { MusicPlaylist, MusicTrack } from '@/api/music'

const props = defineProps<{
  playlist: MusicPlaylist
  tracks: MusicTrack[]
  total: number
  loading: boolean
  loadingMore: boolean
  hasMore: boolean
  similar: MusicPlaylist[]
  showCollect: boolean
  collected: boolean
}>()

defineEmits<{
  'play-all': [shuffle: boolean]
  'collect': []
  'load-more': []
  'select-artist': [track: MusicTrack]
  'select-album': [track: MusicTrack]
  'play-mv': [track: MusicTrack]
  'select-related': [track: MusicTrack]
  'change': [playlist: MusicPlaylist]
}>()

const player = useMusicPlayerStore()
const shuffle = computed(() => player.shuffle)

function playAll() {
  player.shuffle = false
  player.playQueue(props.tracks, 0)
}

function shuffleAll() {
  player.shuffle = true
  player.playQueue(props.tracks, 0)
}

function formatCount(count: number): string {
  if (count >= 100000000) return (count / 100000000).toFixed(1) + '亿'
  if (count >= 10000) return (count / 10000).toFixed(1) + '万'
  return String(count)
}
</script>

<style scoped>
.music-playlist-detail {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.music-detail-header {
  display: flex;
  gap: 2rem;
  margin-bottom: 2rem;
}

.music-detail-cover {
  width: 200px;
  height: 200px;
  border-radius: 0.75rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
}

.music-detail-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-detail-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.music-detail-type {
  font-size: 0.6875rem;
  font-weight: 600;
  color: hsl(var(--primary));
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.music-detail-name {
  font-size: 1.5rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  margin-top: 0.5rem;
  line-height: 1.3;
}

.music-detail-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
  margin-top: 0.5rem;
}

.music-detail-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}

.music-action-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: hsl(var(--foreground));
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-action-btn:hover {
  background: hsl(var(--muted));
}

.music-action-btn--primary {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-color: hsl(var(--primary));
}

.music-action-btn--active {
  color: hsl(var(--primary));
  border-color: hsl(var(--primary));
}

.music-detail-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem;
  color: hsl(var(--muted-foreground));
}

.music-detail-load-more {
  display: flex;
  justify-content: center;
  padding: 1rem 0;
}

.music-load-more-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
  background: none;
  border: 1px solid hsl(var(--border));
  border-radius: 9999px;
  cursor: pointer;
}

.music-load-more-btn:hover:not(:disabled) {
  color: hsl(var(--foreground));
  border-color: hsl(var(--primary));
}

.music-load-more-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.music-similar-section {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid hsl(var(--border));
}

.music-section-title {
  font-size: 1rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin-bottom: 1rem;
}

.music-similar-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 1rem;
}

.music-similar-card {
  cursor: pointer;
}

.music-similar-card img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 0.5rem;
}

.music-similar-name {
  font-size: 0.8125rem;
  font-weight: 500;
  color: hsl(var(--foreground));
  margin-top: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .music-playlist-detail {
    padding: 1rem;
  }

  .music-detail-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .music-detail-cover {
    width: 160px;
    height: 160px;
  }

  .music-detail-actions {
    justify-content: center;
  }
}
</style>