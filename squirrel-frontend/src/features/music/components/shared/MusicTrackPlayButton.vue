<template>
  <button
    class="music-track-play-btn"
    :class="{ 'music-track-play-btn--playing': isPlaying }"
    @click="$emit('click')"
  >
    <AppIcon v-if="loading" name="loadingSpinner" class="h-4 w-4 animate-spin" />
    <AppIcon v-else-if="isPlaying" name="pause" class="h-4 w-4" />
    <AppIcon v-else name="play" class="h-4 w-4" />
  </button>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'

withDefaults(defineProps<{
  isPlaying?: boolean
  loading?: boolean
}>(), {
  isPlaying: false,
  loading: false,
})

defineEmits<{
  click: []
}>()
</script>

<style scoped>
.music-track-play-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 9999px;
  background: none;
  border: none;
  color: hsl(var(--muted-foreground) / 0.6);
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.music-track-play-btn:hover {
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
}

.music-track-play-btn--playing {
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
}
</style>