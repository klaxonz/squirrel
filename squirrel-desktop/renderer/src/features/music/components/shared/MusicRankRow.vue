<template>
  <div class="music-rank-list" aria-label="排行榜列表">
    <button type="button"
      v-for="(rank, index) in ranks"
      :key="rank.id"

      class="music-rank-item"
      :aria-label="`查看排行榜：${rank.name}`"
      @click="$emit('select', rank)"
    >
      <span class="music-rank-index">{{ String(index + 1).padStart(2, '0') }}</span>
      <span class="music-rank-cover">
        <img v-if="rank.cover" :src="rank.cover" :alt="rank.name" loading="lazy" />
        <AppIcon v-else name="list" class="h-4 w-4" />
      </span>
      <span class="music-rank-info">
        <span class="music-rank-name">{{ rank.name }}</span>
        <span class="music-rank-meta">{{ rank.update_frequency || '实时更新' }}</span>
      </span>
      <AppIcon name="chevronRight" class="music-rank-arrow h-4 w-4" />
    </button>
  </div>
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
</script>

<style scoped>
.music-rank-list {
  overflow: hidden;
  border-block: 1px solid var(--app-surface-border-subtle);
}

.music-rank-item {
  display: grid;
  width: 100%;
  min-width: 0;
  grid-template-columns: 1.5rem 2.5rem minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  padding: 0.625rem var(--space-3);
  color: hsl(var(--foreground));
  text-align: left;
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-default);
}

.music-rank-item + .music-rank-item {
  border-top: 1px solid var(--app-surface-border-subtle);
}

.music-rank-item:hover {
  background: hsl(var(--muted) / 0.36);
}

.music-rank-item:focus-visible {
  position: relative;
  z-index: 1;
  outline: 2px solid hsl(var(--ring));
  outline-offset: -2px;
}

.music-rank-index {
  color: hsl(var(--muted-foreground) / 0.62);
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  font-weight: 650;
}

.music-rank-cover {
  display: flex;
  width: 2.5rem;
  height: 2.5rem;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.42);
  color: hsl(var(--muted-foreground) / 0.5);
}

.music-rank-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-rank-info {
  display: block;
  min-width: 0;
}

.music-rank-name,
.music-rank-meta {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-rank-name {
  font-size: 0.75rem;
  font-weight: 650;
}

.music-rank-meta {
  margin-top: 0.2rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
}

.music-rank-arrow {
  color: hsl(var(--muted-foreground) / 0.5);
  transition:
    color var(--duration-fast) var(--ease-default),
    transform var(--duration-fast) var(--ease-default);
}

.music-rank-item:hover .music-rank-arrow {
  color: hsl(var(--foreground));
  transform: translateX(0.125rem);
}

@media (prefers-reduced-motion: reduce) {
  .music-rank-item,
  .music-rank-arrow {
    transition: none;
  }
}
</style>
