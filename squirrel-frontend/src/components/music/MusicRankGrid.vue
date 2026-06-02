<template>
  <div class="music-discovery-grid">
    <h3 class="text-sm font-semibold mb-3">官方排行榜</h3>
    <div class="music-grid">
      <div
        v-for="rank in ranks"
        :key="rank.id"
        class="music-grid-card"
        @click="$emit('select', rank)"
      >
        <div class="music-source-cover-wrap">
          <img v-if="rank.cover" :src="rank.cover" alt="" class="music-source-cover" />
          <div v-else class="music-source-cover">
            <AppIcon name="playlistMusic" class="h-6 w-6 text-muted-foreground" />
          </div>
          <div class="music-source-play-overlay">
            <AppIcon name="play" class="h-6 w-6 text-primary-foreground fill-current" />
          </div>
        </div>
        <span class="music-grid-card-title">{{ rank.name }}</span>
        <span class="music-grid-card-subtitle">{{ rank.update_frequency || '排行榜' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue'
import type { MusicRank } from '@/api/music'

defineProps<{
  ranks: MusicRank[]
}>()

defineEmits<{
  'select': [rank: MusicRank]
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
  font-size: 0.8125rem;
  font-weight: 500;
  margin-top: 0.5rem;
  color: hsl(var(--foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.music-grid-card-subtitle {
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
