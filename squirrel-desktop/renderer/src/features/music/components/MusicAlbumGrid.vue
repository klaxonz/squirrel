<template>
  <div class="music-discovery-grid">
    <h3 class="app-h3 music-discovery-grid__title">新碟上架</h3>
    <AppBlockLoader v-if="loading" />
    <AppEmptyState
      v-else-if="albums.length === 0"
      variant="plain"
      icon="disc"
      title="暂无专辑"
    />
    <MusicCardGrid v-else>
      <MusicCard
        v-for="album in albums"
        :key="album.id"
        :cover="album.cover"
        :title="album.name"
        :subtitle="album.artist"
        size="md"
        variant="album"
        playable
        @select="$emit('select', album)"
        @play="$emit('play', album)"
      />
    </MusicCardGrid>
    <div v-if="hasMore" class="music-load-more">
      <Button variant="secondary" outlined :loading="loadingMore" @click="$emit('load-more')">
        加载更多
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Button } from '@/shared/ui/button'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import type { MusicAlbum } from '@/shared/api/music'
import MusicCard from './shared/MusicCard.vue'
import MusicCardGrid from './shared/MusicCardGrid.vue'

defineProps<{
  albums: MusicAlbum[]
  loading: boolean
  loadingMore?: boolean
  hasMore?: boolean
}>()

defineEmits<{
  'select': [album: MusicAlbum]
  'play': [album: MusicAlbum]
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

.music-load-more {
  display: flex;
  justify-content: center;
  padding: 1rem 0;
}
</style>
