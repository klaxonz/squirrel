<template>
  <Dialog :open="visible" @update:open="!$event && $emit('close')">
    <DialogContent class="app-dialog-surface music-video-container">
      <DialogHeader class="app-dialog-form-header music-video-header">
        <DialogTitle class="app-dialog-form-title music-video-title">
          {{ title }}
        </DialogTitle>
        <Button text variant="secondary" size="sm" icon-only aria-label="关闭" @click="$emit('close')">
          <AppIcon name="close" class="h-5 w-5" />
        </Button>
      </DialogHeader>
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
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'
import { Button } from '@/shared/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog'

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
.music-video-container {
  width: min(90vw, 60rem);
  box-shadow: var(--app-overlay-shadow);
}

.music-video-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.music-video-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
