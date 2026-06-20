<template>
  <div
    v-if="src"
    class="fixed inset-0 z-sidebar flex items-center justify-center bg-background/95 backdrop-blur-md transition-all duration-300 animate-fade-in"
    @click="$emit('close')"
  >
    <!-- Close Button -->
    <button
      class="absolute top-5 right-5 h-10 w-10 rounded-full bg-accent/20 hover:bg-accent/40 text-foreground flex items-center justify-center backdrop-blur-md border border-border/10 transition-all cursor-pointer"
      @click.stop="$emit('close')"
    >
      <AppIcon name="close" class="h-5 w-5" />
    </button>

    <!-- Interactive Image -->
    <div class="relative max-w-[90vw] max-h-[90vh] overflow-hidden select-none">
      <img
        :src="src"
        class="max-w-full max-h-[90vh] object-contain rounded-lg shadow-2xl transition-transform duration-300 cursor-zoom-out"
        :style="{ transform: `scale(${scale})` }"
        @click.stop="$emit('close')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Full-screen image lightbox for the RSS reader. Extracted from RssSources.vue
 * (was an inline ~25-line block). Pure presentational: shows when `src` is
 * truthy, emits `close` on backdrop/button/image click. The zoom scale is
 * passed in (owned by useRssReader).
 */
import AppIcon from '@/shared/icons/AppIcon.vue'

defineProps<{
  src: string | null
  scale: number
}>()

defineEmits<{
  close: []
}>()
</script>
