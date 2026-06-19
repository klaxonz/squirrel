<template>
  <div class="music-playlist-detail">
    <div class="music-playlist-topbar">
      <div class="music-playlist-topbar-left">
        <h1 class="music-playlist-topbar-title">{{ playlist.name }}</h1>
        <span class="music-playlist-topbar-meta">{{ total }} 首</span>
      </div>
      <div class="music-playlist-topbar-actions">
        <button class="music-playlist-icon-btn" :class="{ 'music-playlist-icon-btn--active': shuffle }" title="随机播放" @click="shuffleAll">
          <AppIcon name="shuffle" class="h-4 w-4" />
        </button>
        <button v-if="showCollect" class="music-playlist-icon-btn" :class="{ 'music-playlist-icon-btn--active': collected }" title="收藏" @click="$emit('collect')">
          <AppIcon name="heart" class="h-4 w-4" :class="{ 'fill-current': collected }" />
        </button>
        <button class="music-playlist-play-btn" title="播放全部" @click="playAll">
          <AppIcon name="play" class="h-4 w-4" />
        </button>
      </div>
    </div>

    <div v-if="loading" class="music-playlist-loading">
      <AppIcon name="loadingSpinner" class="h-5 w-5 animate-spin text-primary" />
      <span>加载中...</span>
    </div>

    <div v-else class="music-playlist-tracks">
      <MusicTrackList
        :tracks="tracks"
        :show-mv="false"
        :show-related="false"
        @select-artist="$emit('select-artist', $event)"
        @select-album="$emit('select-album', $event)"
        @add-to-playlist="$emit('add-to-playlist', $event)"
      />
    </div>

    <div v-if="hasMore" class="music-playlist-load-more">
      <button class="music-playlist-load-more-btn" :disabled="loadingMore" @click="$emit('load-more')">
        <AppIcon v-if="loadingMore" name="loadingSpinner" class="h-4 w-4 animate-spin" />
        <span>加载更多</span>
      </button>
    </div>

    <section v-if="similar.length" class="music-playlist-similar">
      <h2 class="music-playlist-similar-title">相似歌单</h2>
      <div class="music-playlist-similar-grid">
        <article
          v-for="item in similar"
          :key="item.id"
          class="music-playlist-similar-card"
          @click="$emit('change', item)"
        >
          <img :src="item.cover" :alt="item.name" loading="lazy" />
          <h3>{{ item.name }}</h3>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import MusicTrackList from './MusicTrackList.vue'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import type { MusicPlaylist, MusicTrack } from '@/shared/api/music'

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
  'add-to-playlist': [track: MusicTrack]
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
</script>

<style scoped>
.music-playlist-detail {
  width: 100%;
  max-width: 1480px;
  padding: 1.25rem 2rem 2.5rem;
}

.music-playlist-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 0 1.125rem;
  border-bottom: 1px solid hsl(var(--border) / 0.3);
  margin-bottom: 0.75rem;
}

.music-playlist-topbar-left {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  min-width: 0;
}

.music-playlist-topbar-title {
  font-size: 1.5rem;
  font-weight: 800;
  color: hsl(var(--foreground));
  letter-spacing: -0.02em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-playlist-topbar-meta {
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
  flex-shrink: 0;
  font-weight: 500;
}

.music-playlist-topbar-actions {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-shrink: 0;
}

.music-playlist-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border: none;
  border-radius: 0.5rem;
  background: none;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.2s ease;
}

.music-playlist-icon-btn:hover {
  background: hsl(var(--muted) / 0.5);
  color: hsl(var(--foreground));
}

.music-playlist-icon-btn--active {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
}

.music-playlist-play-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.75rem;
  height: 2.75rem;
  border: none;
  border-radius: 9999px;
  background: linear-gradient(135deg, hsl(var(--primary)) 0%, hsl(var(--primary) / 0.85) 100%);
  color: hsl(var(--primary-foreground));
  cursor: pointer;
  box-shadow: 0 4px 12px hsl(var(--primary) / 0.3);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.music-playlist-play-btn:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 16px hsl(var(--primary) / 0.35);
}

.music-playlist-play-btn:active {
  transform: scale(0.95);
}

.music-playlist-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.625rem;
  padding: 4rem 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.9375rem;
  font-weight: 500;
}

.music-playlist-tracks {
  margin: 0 -1.5rem;
}

.music-playlist-load-more {
  display: flex;
  justify-content: center;
  padding: 1.5rem 0;
}

.music-playlist-load-more-btn {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.625rem 1.25rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  background: none;
  border: 1px solid hsl(var(--border) / 0.6);
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.music-playlist-load-more-btn:hover:not(:disabled) {
  color: hsl(var(--primary));
  border-color: hsl(var(--primary) / 0.5);
  background: hsl(var(--primary) / 0.05);
}

.music-playlist-load-more-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.music-playlist-similar {
  margin-top: 2.5rem;
  padding-top: 2rem;
  border-top: 1px solid hsl(var(--border) / 0.3);
}

.music-playlist-similar-title {
  font-size: 1rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  margin-bottom: 1rem;
  letter-spacing: -0.01em;
}

.music-playlist-similar-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr));
  gap: 1rem;
}

.music-playlist-similar-card {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.music-playlist-similar-card:hover {
  transform: translateY(-4px);
}

.music-playlist-similar-card img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 0.625rem;
  box-shadow: 0 4px 12px hsl(var(--foreground) / 0.08);
}

.music-playlist-similar-card h3 {
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin-top: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .music-playlist-detail {
    padding: 1rem 1rem 2rem;
  }

  .music-playlist-topbar {
    align-items: flex-start;
    gap: 1rem;
  }

  .music-playlist-tracks {
    margin: 0 -1rem;
  }
}
</style>
