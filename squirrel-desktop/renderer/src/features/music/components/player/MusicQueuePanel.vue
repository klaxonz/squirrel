<template>
  <Transition
    enter-active-class="transition-[transform,opacity] duration-200 ease-out"
    leave-active-class="transition-[transform,opacity] duration-150 ease-in"
    enter-from-class="opacity-0 translate-y-2"
    leave-to-class="opacity-0 translate-y-2"
  >
    <div
      v-if="visible"
      ref="panelRef"
      class="music-queue-panel"
      role="dialog"
      aria-label="播放队列"
      tabindex="-1"
    >
      <header class="music-queue-header">
        <h3>播放队列</h3>
        <span class="music-queue-count">{{ queue.length }} 首</span>
        <Button v-if="queue.length" text severity="secondary" size="sm" class="ml-auto text-muted-foreground hover:text-destructive" title="清空队列" @click="$emit('clear')">
          <AppIcon name="trash" class="h-3.5 w-3.5" />
          清空
        </Button>
        <Button text severity="secondary" size="sm" icon-only class="ml-2" aria-label="关闭播放队列" @click="$emit('close')">
          <AppIcon name="close" class="h-4 w-4" />
        </Button>
      </header>

      <div v-if="queue.length === 0" class="music-queue-empty">
        <AppIcon name="playlistMusic" class="h-8 w-8" />
        <p>播放队列为空</p>
      </div>

      <div v-else class="music-queue-list">
        <article
          v-for="(track, index) in queue"
          :key="track.hash"
          class="music-queue-item group"
          :class="{ 'music-queue-item--active': currentIndex === index }"
          draggable="true"
          @dragstart="$emit('drag-start', index, $event)"
          @dragover.prevent
          @drop="$emit('drop', index, $event)"
          @click="$emit('play', index)"
        >
          <div class="music-queue-item-index">
            <MusicPlayingIndicator v-if="currentIndex === index && playing" />
            <span v-else>{{ index + 1 }}</span>
          </div>
          <img v-if="track.cover" :src="track.cover" class="music-queue-item-cover" />
          <div v-else class="music-queue-item-cover music-queue-item-cover--placeholder">
            <AppIcon name="playlistMusic" class="h-3 w-3" />
          </div>
          <div class="music-queue-item-info">
            <p class="music-queue-item-title">{{ track.title || '未知歌曲' }}</p>
            <p class="music-queue-item-artist">{{ track.artist || '未知歌手' }}</p>
          </div>
          <Button
            text severity="secondary"
            size="sm" icon-only
            class="opacity-0 text-muted-foreground hover:text-destructive group-hover:opacity-100"
            title="从队列移除"
            aria-label="从队列移除"
            @click.stop="$emit('remove', index)"
          >
            <AppIcon name="close" class="h-3 w-3" />
          </Button>
        </article>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import MusicPlayingIndicator from '../shared/MusicPlayingIndicator.vue'
import { Button } from '@/shared/ui/button'
import type { MusicTrack } from '@/shared/api/music'

const props = defineProps<{
  visible: boolean
  queue: MusicTrack[]
  currentIndex: number
  playing: boolean
}>()

const emit = defineEmits<{
  close: []
  clear: []
  play: [index: number]
  remove: [index: number]
  'drag-start': [index: number, event: DragEvent]
  'drop': [index: number, event: DragEvent]
}>()

const panelRef = ref<HTMLElement | null>(null)

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
  }
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      window.addEventListener('keydown', onKeydown)
      queueMicrotask(() => panelRef.value?.focus())
      return
    }
    window.removeEventListener('keydown', onKeydown)
  },
  { immediate: true },
)

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.music-queue-panel {
  position: fixed;
  outline: none;
  bottom: calc(var(--app-music-player-height) + var(--space-2));
  right: 1.5rem;
  width: 24rem;
  max-height: 28rem;
  background: hsl(var(--popover));
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: var(--app-surface-radius);
  box-shadow: var(--app-floating-shadow);
  display: flex;
  flex-direction: column;
  z-index: var(--z-popover);
  overflow: hidden;
}

.music-queue-header {
  display: flex;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid hsl(var(--border) / 0.4);
  flex-shrink: 0;
}

.music-queue-header h3 {
  font-family: var(--app-heading-font);
  font-size: var(--app-h4-size);
  font-weight: var(--app-h4-weight);
  letter-spacing: var(--app-h4-tracking);
  color: hsl(var(--foreground));
}

.music-queue-count {
  font-size: var(--app-text-sm);
  color: hsl(var(--muted-foreground));
  margin-left: 0.625rem;
  font-weight: 500;
}

.music-queue-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.625rem;
  color: hsl(var(--muted-foreground) / 0.4);
  font-size: var(--app-text-base);
  padding: 2.5rem;
}

.music-queue-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 0;
}

.music-queue-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 1.25rem;
  cursor: pointer;
  transition: background 0.15s ease;
}

.music-queue-item:hover {
  background: hsl(var(--muted) / 0.4);
}

.music-queue-item--active {
  background: var(--app-selection-bg);
}

.music-queue-item-index {
  width: 1.75rem;
  font-size: var(--app-text-sm);
  color: hsl(var(--muted-foreground));
  text-align: center;
  flex-shrink: 0;
  font-weight: 500;
}

.music-queue-item-cover {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: var(--radius-sm);
  object-fit: cover;
  flex-shrink: 0;
}

.music-queue-item-cover--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--muted) / 0.3);
  color: hsl(var(--muted-foreground));
}

.music-queue-item-info {
  flex: 1;
  min-width: 0;
}

.music-queue-item-title {
  font-size: var(--app-text-base);
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-queue-item-artist {
  font-size: var(--app-text-sm);
  color: hsl(var(--muted-foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 0.125rem;
}

</style>
