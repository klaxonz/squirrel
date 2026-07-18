<template>
  <button type="button" class="music-action-button" @click="$emit('click')">
    <span class="music-action-icon">
      <AppIcon :name="icon" class="h-4 w-4" />
    </span>
    <span class="music-action-content">
      <span class="music-action-label">{{ label }}</span>
      <span class="music-action-description">{{ description }}</span>
    </span>
    <AppIcon name="chevronRight" class="music-action-arrow h-4 w-4" />
  </button>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'

defineProps<{
  icon: AppIconName
  label: string
  description: string
}>()

defineEmits<{
  click: []
}>()
</script>

<style scoped>
.music-action-button {
  display: flex;
  min-width: 0;
  min-height: 3.5rem;
  align-items: center;
  gap: var(--space-2);
  border: 0;
  border-radius: 0;
  padding: 0.5rem var(--space-3);
  background: transparent;
  color: hsl(var(--foreground));
  text-align: left;
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.music-action-button:hover {
  background: hsl(var(--muted) / 0.34);
}

.music-action-button:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}

.music-action-icon {
  display: flex;
  width: 1.75rem;
  height: 1.75rem;
  flex: none;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.52);
  color: hsl(var(--foreground) / 0.72);
}

.music-action-content {
  display: block;
  min-width: 0;
  flex: 1;
}

.music-action-label,
.music-action-description {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-action-label {
  font-size: 0.8125rem;
  font-weight: 700;
}

.music-action-description {
  margin-top: 0.125rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-badge-size);
}

.music-action-arrow {
  flex: none;
  color: hsl(var(--muted-foreground) / 0.58);
  transition:
    color var(--duration-fast) var(--ease-default),
    transform var(--duration-fast) var(--ease-default);
}

.music-action-button:hover .music-action-arrow {
  color: hsl(var(--foreground));
  transform: translateX(0.125rem);
}

@media (prefers-reduced-motion: reduce) {
  .music-action-button,
  .music-action-arrow {
    transition: none;
  }
}
</style>
