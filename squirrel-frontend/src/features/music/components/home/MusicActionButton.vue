<template>
  <button class="music-action-button" :class="variantClass" @click="$emit('click')">
    <div class="music-action-icon" :class="variantClass">
      <AppIcon :name="icon" class="h-5 w-5" />
    </div>
    <div class="music-action-content">
      <span class="music-action-label">{{ label }}</span>
      <span v-if="track" class="music-action-track">{{ track.title }}</span>
    </div>
    <AppIcon name="chevronRight" class="h-4 w-4 music-action-arrow" />
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
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
  display: flex;
  align-items: center;
  gap: 0.875rem;
  min-height: 4.75rem;
  height: 100%;
  padding: 0.625rem 0.875rem;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  text-align: left;
  position: relative;
  overflow: hidden;
  flex: 1;
}

.music-action-button::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity 0.25s ease;
}

.music-action-button--primary::before {
  background: radial-gradient(circle at top right, hsl(var(--primary) / 0.06) 0%, transparent 70%);
}

.music-action-button--fm::before {
  background: radial-gradient(circle at top right, hsl(var(--foreground) / 0.04) 0%, transparent 70%);
}

.music-action-button--daily::before {
  background: radial-gradient(circle at top right, hsl(25, 95%, 53% / 0.08) 0%, transparent 70%);
}

.music-action-button--rank::before {
  background: radial-gradient(circle at top right, hsl(199, 89%, 48% / 0.08) 0%, transparent 70%);
}

.music-action-button:hover {
  border-color: hsl(var(--primary) / 0.2);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px hsl(var(--foreground) / 0.08);
}

.music-action-button:hover::before {
  opacity: 1;
}

.music-action-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.625rem;
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
  background: hsl(25, 95%, 53% / 0.12);
  color: hsl(25, 95%, 52%);
}

.music-action-icon--rank {
  background: hsl(199, 89%, 48% / 0.12);
  color: hsl(199, 89%, 46%);
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
  transition: transform 0.2s ease;
  position: relative;
  z-index: 1;
}

.music-action-button:hover .music-action-arrow {
  transform: translateX(3px);
  color: hsl(var(--foreground) / 0.6);
}

@media (max-width: 1100px) {
  .music-action-button {
    min-height: 4rem;
    height: auto;
  }
}

@media (max-width: 768px) {
  .music-action-button {
    min-height: 3.75rem;
    height: auto;
    padding: 0.875rem 1rem;
  }

  .music-action-icon {
    width: 2.25rem;
    height: 2.25rem;
  }
}
</style>
