<template>
  <div class="music-discovery-grid">
    <header class="music-rank-header">
      <div>
        <h2 class="music-rank-heading">官方排行榜</h2>
        <p class="music-rank-subtitle">{{ ranks.length }} 个榜单，按更新频率浏览</p>
      </div>
    </header>

    <section v-if="ranks.length" aria-label="全部排行榜">
      <div class="app-music-grid">
        <MusicCard
          v-for="rank in ranks"
          :key="rank.id"
          :cover="rank.cover"
          :title="rank.name"
          :subtitle="rank.update_frequency || '排行榜'"
          variant="rank"
          @select="$emit('select', rank)"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { MusicRank } from '@/shared/api/music'
import MusicCard from './shared/MusicCard.vue'

defineProps<{
  ranks: MusicRank[]
}>()

defineEmits<{
  'select': [rank: MusicRank]
}>()

</script>

<style scoped>
.music-discovery-grid {
  width: 100%;
  min-width: 0;
}

.music-rank-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.music-rank-heading {
  font-size: var(--app-text-lg);
  font-weight: 800;
  color: hsl(var(--foreground));
}

.music-rank-subtitle {
  margin-top: 0.25rem;
  font-size: var(--app-text-sm);
  color: hsl(var(--muted-foreground));
}

</style>
