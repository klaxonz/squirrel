<template>
  <div class="music-discovery-grid">
    <header class="music-rank-header">
      <div>
        <h2 class="music-rank-heading">官方排行榜</h2>
        <p class="music-rank-subtitle">{{ ranks.length }} 个榜单，按更新频率浏览</p>
      </div>
    </header>

    <section v-if="featuredRanks.length" class="music-rank-featured" aria-label="重点排行榜">
      <div
        v-for="rank in featuredRanks"
        :key="rank.id"
        class="music-rank-featured-card"
        @click="$emit('select', rank)"
      >
        <img v-if="rank.cover" :src="rank.cover" alt="" class="music-rank-featured-cover" />
        <div v-else class="music-rank-featured-cover">
          <AppIcon name="playlistMusic" class="h-7 w-7 text-muted-foreground" />
        </div>
        <div class="music-rank-featured-info">
          <span class="music-rank-featured-kicker">榜单</span>
          <h3 class="music-rank-featured-title">{{ rank.name }}</h3>
          <p class="music-rank-featured-meta">{{ rank.update_frequency || '排行榜' }}</p>
        </div>
        <div class="music-rank-featured-action" aria-hidden="true">
          <AppIcon name="play" class="h-4 w-4" />
        </div>
      </div>
    </section>

    <section class="music-rank-all">
      <header class="music-rank-section-header">
        <h3 class="music-rank-section-title">全部榜单</h3>
      </header>

      <div class="music-grid">
        <div
          v-for="rank in restRanks"
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
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { MusicRank } from '@/shared/api/music'

const props = defineProps<{
  ranks: MusicRank[]
}>()

defineEmits<{
  'select': [rank: MusicRank]
}>()

const featuredRanks = computed(() => props.ranks.slice(0, 4))
const restRanks = computed(() => props.ranks.slice(4))
</script>

<style scoped>
.music-discovery-grid {
  width: 100%;
  max-width: 1480px;
  padding: 1rem 2rem 2.5rem;
}

.music-rank-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.music-rank-heading {
  font-size: 1rem;
  font-weight: 800;
  color: hsl(var(--foreground));
}

.music-rank-subtitle {
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.music-rank-featured {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.875rem;
  margin-bottom: 1.5rem;
}

.music-rank-featured-card {
  position: relative;
  min-height: 8.25rem;
  border-radius: 0.875rem;
  overflow: hidden;
  cursor: pointer;
  background: hsl(var(--muted) / 0.35);
  box-shadow: 0 8px 28px hsl(var(--foreground) / 0.1);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.music-rank-featured-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 34px hsl(var(--foreground) / 0.14);
}

.music-rank-featured-cover {
  width: 100%;
  height: 100%;
  min-height: 8.25rem;
  object-fit: cover;
  display: flex;
  align-items: center;
  justify-content: center;
}

.music-rank-featured-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, hsl(var(--foreground) / 0.08) 0%, hsl(var(--foreground) / 0.66) 100%);
}

.music-rank-featured-info {
  position: absolute;
  left: 1rem;
  right: 3rem;
  bottom: 0.875rem;
  z-index: 1;
  color: white;
}

.music-rank-featured-kicker {
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.6875rem;
  font-weight: 700;
  opacity: 0.78;
}

.music-rank-featured-title {
  font-size: 1rem;
  font-weight: 800;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-rank-featured-meta {
  margin-top: 0.25rem;
  font-size: 0.75rem;
  opacity: 0.82;
}

.music-rank-featured-action {
  position: absolute;
  right: 0.875rem;
  bottom: 0.875rem;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 9999px;
  background: hsl(var(--background) / 0.92);
  color: hsl(var(--foreground));
}

.music-rank-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 0.625rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid hsl(var(--border) / 0.25);
}

.music-rank-section-title {
  font-size: 0.9375rem;
  font-weight: 800;
  color: hsl(var(--foreground));
}

.music-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(7.75rem, 1fr));
  gap: 1rem 0.875rem;
}

.music-grid-card {
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.music-grid-card:hover {
  transform: translateY(-3px);
}

.music-source-cover-wrap {
  position: relative;
  aspect-ratio: 1;
  border-radius: 0.625rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
  box-shadow: 0 4px 14px hsl(var(--foreground) / 0.08);
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
  background: hsl(var(--foreground) / 0.32);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.music-grid-card:hover .music-source-play-overlay {
  opacity: 1;
}

.music-grid-card-title {
  font-size: 0.8125rem;
  font-weight: 700;
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
  margin-top: 0.125rem;
}

@media (max-width: 768px) {
  .music-discovery-grid {
    padding: 1rem 1rem 2rem;
  }

  .music-rank-featured {
    grid-template-columns: 1fr;
  }

  .music-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }
}

@media (min-width: 769px) and (max-width: 1180px) {
  .music-rank-featured {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
