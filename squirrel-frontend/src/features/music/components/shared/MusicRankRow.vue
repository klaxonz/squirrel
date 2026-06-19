<template>
  <section class="music-rank-row" aria-label="排行榜列表">
    <article
      v-for="(rank, index) in ranks"
      :key="rank.id"
      class="music-rank-card"
      :aria-label="`查看排行榜: ${rank.name}，${rank.update_frequency || '实时更新'}`"
      @click="$emit('select', rank)"
    >
      <div class="music-rank-cover">
        <img :src="rank.cover" :alt="rank.name" loading="lazy" />
        <span class="music-rank-badge" :class="`music-rank-badge--${badgeColor(index)}`" aria-hidden="true">
          {{ index + 1 }}
        </span>
      </div>
      <div class="music-rank-info">
        <h3 class="music-rank-name">{{ rank.name }}</h3>
        <p class="music-rank-meta">{{ rank.update_frequency || '实时更新' }}</p>
      </div>
      <div class="music-rank-play" aria-hidden="true">
        <AppIcon name="play" class="h-4 w-4" />
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { MusicRank } from '@/shared/api/music'

defineProps<{
  ranks: MusicRank[]
}>()

defineEmits<{
  select: [rank: MusicRank]
}>()

function badgeColor(index: number): string {
  const colors = ['red', 'orange', 'green', 'purple', 'blue', 'gray']
  return colors[index] || 'gray'
}
</script>

<style scoped>
.music-rank-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.625rem;
}

.music-rank-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-height: 3.75rem;
  padding: 0.5rem 0.625rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 0.625rem;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.music-rank-card::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0;
  background: radial-gradient(circle at 20% 50%, hsl(var(--foreground) / 0.03) 0%, transparent 60%);
  transition: opacity 0.25s ease;
}

.music-rank-card:hover {
  border-color: hsl(var(--border) / 0.5);
  background: hsl(var(--muted) / 0.26);
}

.music-rank-card:hover::before {
  opacity: 1;
}

.music-rank-cover {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 0.5rem;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: 0 3px 10px hsl(var(--foreground) / 0.1);
  position: relative;
  z-index: 1;
}

.music-rank-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-rank-badge {
  position: absolute;
  top: 0;
  left: 0;
  width: 1.25rem;
  height: 1.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6875rem;
  font-weight: 800;
  color: white;
  border-bottom-right-radius: 0.5rem;
  border-top-left-radius: 0.625rem;
}

.music-rank-badge--red { background: hsl(0, 75%, 55%); }
.music-rank-badge--orange { background: hsl(25, 90%, 52%); }
.music-rank-badge--green { background: hsl(150, 65%, 42%); }
.music-rank-badge--purple { background: hsl(270, 65%, 55%); }
.music-rank-badge--blue { background: hsl(210, 75%, 52%); }
.music-rank-badge--gray { background: hsl(var(--muted-foreground) / 0.5); }

.music-rank-info {
  flex: 1;
  min-width: 0;
  position: relative;
  z-index: 1;
}

.music-rank-name {
  font-size: 0.8125rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-rank-meta {
  font-size: 0.625rem;
  color: hsl(var(--muted-foreground) / 0.85);
  margin-top: 0.25rem;
  font-weight: 500;
}

.music-rank-play {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 9999px;
  background: hsl(var(--primary) / 0.08);
  color: hsl(var(--primary));
  opacity: 0;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.music-rank-card:hover .music-rank-play {
  opacity: 1;
}

@media (max-width: 768px) {
  .music-rank-row {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 769px) and (max-width: 1180px) {
  .music-rank-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
