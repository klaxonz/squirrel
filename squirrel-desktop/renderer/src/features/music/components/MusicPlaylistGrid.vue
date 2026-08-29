<template>
  <div class="music-discovery-grid">
    <h3 class="app-h3 music-discovery-grid__title">热门精品歌单</h3>
    <div v-if="tags.length" class="music-tag-strip">
      <Button
        variant="secondary"
        size="sm"
        :class="selectedCategory === 0 && 'app-selection-active'"
        @click="$emit('select-category', 0)"
      >
        推荐
      </Button>
      <Button
        v-for="tag in tags"
        :key="tag.id"
        variant="secondary"
        size="sm"
        :class="selectedCategory === Number(tag.id) && 'app-selection-active'"
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
    <div v-else class="app-music-grid">
      <MusicCard
        v-for="playlist in playlists"
        :key="playlist.specialid"
        :cover="playlist.imgurl"
        :title="playlist.specialname || playlist.name || '未命名歌单'"
        :subtitle="playlist.nickname || '歌单'"
        variant="playlist"
        playable
        @select="$emit('select', playlist)"
        @play="$emit('play', playlist)"
      />
    </div>
    <div class="app-page-actions mt-6" v-if="hasMore">
      <Button variant="outline" size="sm" :loading="loading" @click="$emit('load-more')">
        加载更多歌单
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Button } from '@/shared/ui/button'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import type { MusicPlaylist, MusicPlaylistTag } from '@/shared/api/music'
import MusicCard from './shared/MusicCard.vue'

defineProps<{
  playlists: MusicPlaylist[]
  tags: MusicPlaylistTag[]
  selectedCategory: number
  hasMore: boolean
  loading: boolean
}>()

defineEmits<{
  'select': [playlist: MusicPlaylist]
  'play': [playlist: MusicPlaylist]
  'select-category': [categoryId: number]
  'load-more': []
}>()
</script>

<style scoped>
.music-discovery-grid {
  width: 100%;
  min-width: 0;
}

.music-discovery-grid__title {
  margin-bottom: var(--space-3);
}

.music-tag-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

</style>
