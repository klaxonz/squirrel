<template>
  <div class="music-discovery-grid">
    <h3 class="text-sm font-semibold mb-3">热门精品歌单</h3>
    <div v-if="tags.length" class="music-tag-strip">
      <button
        class="music-tag-chip"
        :class="{ 'music-tag-chip--active': selectedCategory === 0 }"
        @click="$emit('select-category', 0)"
      >
        推荐
      </button>
      <button
        v-for="tag in tags"
        :key="tag.id"
        class="music-tag-chip"
        :class="{ 'music-tag-chip--active': selectedCategory === Number(tag.id) }"
        @click="$emit('select-category', Number(tag.id))"
      >
        {{ tag.name }}
      </button>
    </div>
    <div class="music-grid">
      <div
        v-for="playlist in playlists"
        :key="playlist.id"
        class="music-grid-card"
        @click="$emit('select', playlist)"
      >
        <div class="music-source-cover-wrap">
          <img v-if="playlist.cover" :src="playlist.cover" alt="" class="music-source-cover" />
          <div v-else class="music-source-cover">
            <AppIcon name="playlistMusic" class="h-6 w-6 text-muted-foreground" />
          </div>
          <div class="music-source-play-overlay">
            <AppIcon name="play" class="h-6 w-6 text-primary-foreground fill-current" />
          </div>
        </div>
        <span class="music-grid-card-title">{{ playlist.name }}</span>
        <span class="music-grid-card-subtitle">{{ playlist.creator || '歌单' }}</span>
      </div>
    </div>
    <div class="flex justify-center mt-6" v-if="hasMore">
      <Button variant="outline" class="h-8 text-xs px-4" :disabled="loading" @click="$emit('load-more')">
        <AppIcon v-if="loading" name="loadingSpinner" class="h-3.5 w-3.5 animate-spin" />
        加载更多歌单
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue'
import { Button } from '@/components/ui/button'
import type { MusicPlaylist, MusicPlaylistTag } from '@/api/music'

defineProps<{
  playlists: MusicPlaylist[]
  tags: MusicPlaylistTag[]
  selectedCategory: number
  hasMore: boolean
  loading: boolean
}>()

defineEmits<{
  'select': [playlist: MusicPlaylist]
  'select-category': [categoryId: number]
  'load-more': []
}>()
</script>

<style scoped>
.music-discovery-grid {
  padding: 1.5rem 2rem 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.music-tag-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.music-tag-chip {
  padding: 0.5rem 1rem;
  font-size: 0.8125rem;
  font-weight: 600;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 9999px;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.music-tag-chip:hover {
  border-color: hsl(var(--primary) / 0.5);
  color: hsl(var(--foreground));
  background: hsl(var(--muted) / 0.3);
}

.music-tag-chip--active {
  background: linear-gradient(135deg, hsl(var(--primary) / 0.15) 0%, hsl(var(--primary) / 0.08) 100%);
  border-color: hsl(var(--primary) / 0.5);
  color: hsl(var(--primary));
  box-shadow: 0 2px 8px hsl(var(--primary) / 0.15);
}

.music-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 1.5rem;
}

.music-grid-card {
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.music-grid-card:hover {
  transform: translateY(-6px);
}

.music-source-cover-wrap {
  position: relative;
  aspect-ratio: 1;
  border-radius: 0.75rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
  box-shadow: 0 4px 12px hsl(var(--foreground) / 0.06);
}

.music-source-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.music-grid-card:hover .music-source-cover {
  transform: scale(1.08);
}

.music-source-play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, transparent 0%, hsl(var(--foreground) / 0.6) 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.music-grid-card:hover .music-source-play-overlay {
  opacity: 1;
}

.music-grid-card-title {
  font-size: 0.875rem;
  font-weight: 600;
  margin-top: 0.75rem;
  color: hsl(var(--foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 0 0.125rem;
}

.music-grid-card-subtitle {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 0 0.125rem;
  margin-top: 0.25rem;
  font-weight: 500;
}
</style>
