<template>
  <div class="music-discovery-grid">
    <h3 class="text-sm font-semibold mb-3">热门精品歌单</h3>
    <div v-if="tags.length" class="music-tag-strip">
      <Button
        variant="secondary"
        size="sm"
        :class="selectedCategory === 0 && 'border-primary/50 bg-primary/10 text-primary hover:bg-primary/15 hover:text-primary'"
        @click="$emit('select-category', 0)"
      >
        推荐
      </Button>
      <Button
        v-for="tag in tags"
        :key="tag.id"
        variant="secondary"
        size="sm"
        :class="selectedCategory === Number(tag.id) && 'border-primary/50 bg-primary/10 text-primary hover:bg-primary/15 hover:text-primary'"
        @click="$emit('select-category', Number(tag.id))"
      >
        {{ tag.name }}
      </Button>
    </div>
    <AppBlockLoader v-if="loading" />
    <AppEmptyState
      v-else-if="playlists.length === 0"
      variant="plain"
      icon="playlistMusic"
      title="暂无歌单"
    />
    <div v-else class="music-grid">
      <div
        v-for="playlist in playlists"
        :key="playlist.specialid"
        class="music-grid-card"
        role="button"
        tabindex="0"
        @click="$emit('select', playlist)"
        @keydown.enter.prevent="$emit('select', playlist)"
        @keydown.space.prevent="$emit('select', playlist)"
      >
        <div class="music-source-cover-wrap">
          <img v-if="playlist.imgurl" :src="playlist.imgurl" :alt="playlist.specialname" class="music-source-cover" />
          <div v-else class="music-source-cover">
            <AppIcon name="playlistMusic" class="h-6 w-6 text-muted-foreground" />
          </div>
          <div class="music-source-play-overlay">
            <AppIcon name="play" class="h-6 w-6 text-primary-foreground fill-current" />
          </div>
        </div>
        <span class="music-grid-card-title">{{ playlist.specialname }}</span>
        <span class="music-grid-card-subtitle">{{ playlist.nickname || '歌单' }}</span>
      </div>
    </div>
    <div class="app-page-actions mt-6" v-if="hasMore">
      <Button variant="outline" size="sm" :loading="loading" @click="$emit('load-more')">
        加载更多歌单
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import type { MusicPlaylist, MusicPlaylistTag } from '@/shared/api/music'

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
