<template>
  <div class="music-album-detail">
    <header class="music-detail-header">
      <div class="music-detail-cover">
        <img v-if="album.cover" :src="album.cover" :alt="album.name" loading="lazy" />
        <div v-else class="music-detail-cover-placeholder">
          <AppIcon name="playlistMusic" class="h-12 w-12 text-muted-foreground" />
        </div>
      </div>
      <div class="music-detail-info">
        <span class="music-detail-type">专辑</span>
        <h1 class="music-detail-name">{{ album.name }}</h1>
        <div class="music-detail-meta">
          <button v-if="album.artist_id" class="music-meta-link" @click="$emit('select-artist')">
            {{ album.artist }}
          </button>
          <span v-else>{{ album.artist }}</span>
          <span v-if="album.publish_date">{{ album.publish_date }}</span>
          <span v-if="total">{{ total }} 首歌</span>
        </div>
        <p v-if="album.intro" class="music-detail-intro">{{ album.intro }}</p>
        <div class="music-detail-actions">
          <button class="music-action-btn music-action-btn--primary" @click="playAll">
            <AppIcon name="play" class="h-5 w-5" />
            播放全部
          </button>
          <button class="music-action-btn" :class="{ 'music-action-btn--active': shuffle }" @click="shuffleAll">
            <AppIcon name="shuffle" class="h-5 w-5" />
            随机
          </button>
        </div>
      </div>
    </header>

    <div v-if="loading" class="music-detail-loading">
      <AppIcon name="loadingSpinner" class="h-6 w-6 animate-spin text-primary" />
      <span>加载歌曲中...</span>
    </div>

    <MusicTrackList
      v-else
      :tracks="tracks"
      :show-add-to-playlist="false"
      @select-artist="$emit('select-artist-track', $event)"
      @play-mv="$emit('play-mv', $event)"
    />

    <div v-if="hasMore" class="music-detail-load-more">
      <button class="music-load-more-btn" :disabled="loadingMore" @click="$emit('load-more')">
        <AppIcon v-if="loadingMore" name="loadingSpinner" class="h-4 w-4 animate-spin" />
        <span>加载更多</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import MusicTrackList from './MusicTrackList.vue'
import { useMusicPlayerStore } from '@/stores/musicPlayer'
import type { MusicAlbum, MusicTrack } from '@/api/music'

const props = defineProps<{
  album: MusicAlbum
  tracks: MusicTrack[]
  total: number
  loading: boolean
  loadingMore: boolean
  hasMore: boolean
}>()

defineEmits<{
  'play-all': [shuffle: boolean]
  'load-more': []
  'select-artist': []
  'select-artist-track': [track: MusicTrack]
  'play-mv': [track: MusicTrack]
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
</script>

<style scoped>
.music-album-detail {
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
  flex-shrink: 0;
}

.music-detail-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-detail-cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
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
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
  margin-top: 0.5rem;
}

.music-meta-link {
  color: hsl(var(--primary));
  background: none;
  border: none;
  padding: 0;
  font-size: inherit;
  cursor: pointer;
}

.music-meta-link:hover {
  text-decoration: underline;
}

.music-detail-intro {
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground) / 0.8);
  margin-top: 0.75rem;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
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

@media (max-width: 768px) {
  .music-album-detail {
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