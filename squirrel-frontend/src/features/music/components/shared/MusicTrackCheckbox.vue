<template>
  <button
    class="music-track-checkbox"
    :class="{ 'music-track-checkbox--checked': checked }"
    @click="$emit('toggle')"
  >
    <AppIcon v-if="checked" name="check" class="h-4 w-4" />
    <AppIcon v-else name="circle" class="h-4 w-4" />
  </button>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'

defineProps<{
  checked?: boolean
}>()

defineEmits<{
  toggle: []
}>()
</script>

<style scoped>
.music-track-checkbox {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.375rem;
  height: 1.375rem;
  border: none;
  background: none;
  color: hsl(var(--muted-foreground) / 0.4);
  cursor: pointer;
  border-radius: 0.375rem;
  transition: all 0.15s ease;
}

.music-track-checkbox:hover {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
}

.music-track-checkbox--checked {
  color: hsl(var(--primary));
}
</style>