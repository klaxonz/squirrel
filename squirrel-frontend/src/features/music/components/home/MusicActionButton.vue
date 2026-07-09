<template>
  <Button variant="secondary" class="music-action-button" :class="variantClass" @click="$emit('click')">
    <div class="music-action-icon" :class="variantClass">
      <AppIcon :name="icon" class="h-5 w-5" />
    </div>
    <div class="music-action-content">
      <span class="music-action-label">{{ label }}</span>
      <span v-if="track" class="music-action-track">{{ track.title }}</span>
    </div>
    <AppIcon name="chevronRight" class="h-4 w-4 music-action-arrow" />
  </Button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import type { AppIconName } from '@/shared/icons/app-icons'
import type { MusicTrack } from '@/shared/api/music'

const props = withDefaults(defineProps<{
  icon: AppIconName
  label: string
  track?: MusicTrack | null
  variant?: 'primary' | 'fm' | 'daily' | 'rank'
}>(), {
  variant: 'primary',
})

defineEmits<{
  click: []
}>()

const variantClass = computed(() => `music-action-button--${props.variant}`)
</script>

<style scoped>
.music-action-button {
  justify-content: flex-start;
  gap: 0.875rem;
  min-height: 4.5rem;
  height: 100%;
  padding: 0.625rem 0.75rem;
  background: hsl(var(--card) / 0.62);
  border: 1px solid hsl(var(--border) / 0.55);
  border-radius: 0.625rem;
  text-align: left;
  position: relative;
  overflow: hidden;
  flex: 1;
}

.music-action-button:hover {
  border-color: hsl(var(--primary) / 0.28);
  background: hsl(var(--muted) / 0.34);
}

.music-action-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.music-action-icon--primary {
  background: hsl(var(--primary) / 0.08);
  color: hsl(var(--primary));
}

.music-action-icon--fm {
  background: hsl(var(--accent));
  color: hsl(var(--foreground) / 0.7);
}

.music-action-icon--daily {
  background: hsl(var(--warning) / 0.12);
  color: hsl(var(--warning));
}

.music-action-icon--rank {
  background: hsl(var(--info) / 0.12);
  color: hsl(var(--info));
}

.music-action-content {
  flex: 1;
  min-width: 0;
  position: relative;
  z-index: 1;
}

.music-action-label {
  display: block;
  font-size: 0.8125rem;
  font-weight: 700;
  color: hsl(var(--foreground));
}

.music-action-track {
  display: block;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground) / 0.85);
  margin-top: 0.25rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-action-arrow {
  color: hsl(var(--muted-foreground) / 0.4);
  flex-shrink: 0;
  transition: transform 0.16s ease, color 0.16s ease;
  position: relative;
  z-index: 1;
}

.music-action-button:hover .music-action-arrow {
  transform: translateX(3px);
  color: hsl(var(--foreground) / 0.6);
}

@media (prefers-reduced-motion: reduce) {
  .music-action-button,
  .music-action-arrow {
    transition: none;
  }
}

@media (max-width: 1100px) {
  .music-action-button {
    min-height: 4rem;
    height: auto;
  }
}
</style>
