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
import AppIcon from '@/components/common/AppIcon.vue'
import type { MusicRank } from '@/api/music'

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
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}

.music-rank-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border) / 0.4);
  border-radius: 1rem;
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
  border-color: hsl(var(--primary) / 0.2);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px hsl(var(--foreground) / 0.1);
}

.music-rank-card:hover::before {
  opacity: 1;
}

.music-rank-cover {
  width: 4rem;
  height: 4rem;
  border-radius: 0.625rem;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: 0 4px 16px hsl(var(--foreground) / 0.12);
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
  width: 1.5rem;
  height: 1.5rem;
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
  font-size: 0.9375rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-rank-meta {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground) / 0.85);
  margin-top: 0.375rem;
  font-weight: 500;
}

.music-rank-play {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
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
</style>