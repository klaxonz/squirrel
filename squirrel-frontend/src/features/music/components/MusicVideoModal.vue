<template>
  <Transition
    enter-active-class="transition-all duration-300 ease-out"
    leave-active-class="transition-all duration-200 ease-in"
    enter-from-class="opacity-0 scale-95"
    leave-to-class="opacity-0 scale-95"
  >
    <div v-if="visible" class="music-video-modal" @click.self="$emit('close')">
      <div class="music-video-container">
        <div class="music-video-header">
          <h3 class="music-video-title truncate">{{ title }}</h3>
          <button class="music-row-action" title="关闭" @click="$emit('close')">
            <AppIcon name="close" class="h-5 w-5" />
          </button>
        </div>
        <div class="music-video-player">
          <video
            v-if="url"
            :src="url"
            controls
            autoplay
            class="music-video-element"
          />
          <AppBlockLoader v-else size="lg" text="加载视频中..." />
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'

defineProps<{
  visible: boolean
  title: string
  url: string
}>()

defineEmits<{
  'close': []
}>()
</script>

<style scoped>
.music-video-modal {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--background) / 0.9);
  backdrop-filter: blur(8px);
}

.music-video-container {
  width: min(90vw, 960px);
  background: hsl(var(--card));
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 16px 40px -12px rgba(0, 0, 0, 0.3);
}

.music-video-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid hsl(var(--border) / 0.3);
}

.music-video-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.music-row-action {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.375rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-row-action:hover {
  background: hsl(var(--muted) / 0.6);
  color: hsl(var(--foreground));
}

.music-video-player {
  aspect-ratio: 16/9;
  background: hsl(var(--foreground) / 0.05);
}

.music-video-element {
  width: 100%;
  height: 100%;
}
</style>