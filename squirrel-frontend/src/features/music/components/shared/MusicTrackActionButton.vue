<template>
  <button class="music-track-action-btn" @click="$emit('click', $event)">
    <AppIcon :name="icon" class="h-4 w-4" />
  </button>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'

defineProps<{
  icon: AppIconName
  label?: string
}>()

defineEmits<{
  click: [event: MouseEvent]
}>()
</script>

<style scoped>
.music-track-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.375rem;
  background: none;
  border: none;
  color: hsl(var(--muted-foreground) / 0.6);
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-track-action-btn:hover {
  background: hsl(var(--muted) / 0.5);
  color: hsl(var(--foreground));
}
</style>
