<template>
  <div class="music-discovery-grid">
    <h3 class="text-sm font-semibold mb-3">新碟上架</h3>
    <AppBlockLoader v-if="loading" />
    <div v-else class="music-grid">
      <div
        v-for="album in albums"
        :key="album.id"
        class="music-grid-card"
        @click="$emit('select', album)"
      >
        <div class="music-source-cover-wrap">
          <img v-if="album.cover" :src="album.cover" alt="" class="music-source-cover" />
          <div v-else class="music-source-cover">
            <AppIcon name="playlistMusic" class="h-6 w-6 text-muted-foreground" />
          </div>
          <div class="music-source-play-overlay">
            <AppIcon name="play" class="h-6 w-6 text-primary-foreground fill-current" />
          </div>
        </div>
        <span class="music-grid-card-title">{{ album.name }}</span>
        <span class="music-grid-card-subtitle">{{ album.artist }}</span>
      </div>
    </div>
    <div v-if="hasMore" class="music-load-more">
      <Button variant="outline" :loading="loadingMore" @click="$emit('load-more')">
        加载更多
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'
import type { MusicAlbum } from '@/shared/api/music'

defineProps<{
  albums: MusicAlbum[]
  loading: boolean
  loadingMore?: boolean
  hasMore?: boolean
}>()

defineEmits<{
  'select': [album: MusicAlbum]
  'load-more': []
}>()
</script>

<style scoped>
.music-discovery-grid {
  padding: 1rem;
}

.music-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 1rem;
}

.music-grid-card {
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.music-grid-card:hover {
  transform: translateY(-2px);
}

.music-source-cover-wrap {
  position: relative;
  aspect-ratio: 1;
  border-radius: 0.5rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
}

.music-source-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: flex;
  align-items: center;
  justify-content: center;
}

.music-source-play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--foreground) / 0.3);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.music-grid-card:hover .music-source-play-overlay {
  opacity: 1;
}

.music-grid-card-title {
  font-size: 0.875rem;
  font-weight: 500;
  margin-top: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-grid-card-subtitle {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-load-more {
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
</style>
