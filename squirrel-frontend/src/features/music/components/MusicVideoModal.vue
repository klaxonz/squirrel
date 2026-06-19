<template>
  <Dialog :open="visible" @update:open="!$event && $emit('close')">
    <DialogContent class="music-video-container gap-0 overflow-hidden rounded-xl p-0">
      <DialogHeader class="music-video-header space-y-0">
        <DialogTitle class="music-video-title truncate text-sm font-semibold">
          {{ title }}
        </DialogTitle>
        <DialogClose as-child>
          <Button variant="ghost" size="icon" class="h-8 w-8" aria-label="关闭">
            <AppIcon name="close" class="h-5 w-5" />
          </Button>
        </DialogClose>
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
  DialogClose,
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
  width: min(90vw, 960px);
  background: hsl(var(--card));
  box-shadow: 0 16px 40px -12px rgba(0, 0, 0, 0.3);
}

.music-video-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid hsl(var(--border) / 0.3);
}

.music-video-title {
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