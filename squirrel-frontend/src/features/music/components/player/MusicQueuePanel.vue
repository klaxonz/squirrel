<template>
  <Transition
    enter-active-class="transition-all duration-200 ease-out"
    leave-active-class="transition-all duration-150 ease-in"
    enter-from-class="opacity-0 translate-y-2"
    leave-to-class="opacity-0 translate-y-2"
  >
    <div v-if="visible" class="music-queue-panel">
      <header class="music-queue-header">
        <h3>播放队列</h3>
        <span class="music-queue-count">{{ queue.length }} 首</span>
        <button v-if="queue.length" class="music-queue-clear" title="清空队列" @click="$emit('clear')">
          <AppIcon name="trash" class="h-3.5 w-3.5" />
          清空
        </button>
        <button class="music-queue-close" @click="$emit('close')">
          <AppIcon name="close" class="h-4 w-4" />
        </button>
      </header>

      <div v-if="queue.length === 0" class="music-queue-empty">
        <AppIcon name="playlistMusic" class="h-8 w-8" />
        <p>播放队列为空</p>
      </div>

      <div v-else class="music-queue-list">
        <article
          v-for="(track, index) in queue"
          :key="track.hash"
          class="music-queue-item"
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
          <button class="music-queue-item-remove" @click.stop="$emit('remove', index)" title="从队列移除">
            <AppIcon name="close" class="h-3 w-3" />
          </button>
        </article>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import MusicPlayingIndicator from '../shared/MusicPlayingIndicator.vue'
import type { MusicTrack } from '@/shared/api/music'

defineProps<{
  visible: boolean
  queue: MusicTrack[]
  currentIndex: number
  playing: boolean
}>()

defineEmits<{
  close: []
  clear: []
  play: [index: number]
  remove: [index: number]
  'drag-start': [index: number, event: DragEvent]
  'drop': [index: number, event: DragEvent]
}>()
</script>

<style scoped>
.music-queue-panel {
  position: fixed;
  bottom: 4.5rem;
  right: 1.5rem;
  width: 24rem;
  max-height: 28rem;
  background: linear-gradient(180deg, hsl(var(--background)) 0%, hsl(var(--background) / 0.98) 100%);
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 1rem;
  box-shadow: 0 12px 40px hsl(var(--foreground) / 0.12);
  display: flex;
  flex-direction: column;
  z-index: 55;
  overflow: hidden;
  backdrop-filter: blur(20px);
}

.music-queue-header {
  display: flex;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid hsl(var(--border) / 0.4);
  flex-shrink: 0;
}

.music-queue-header h3 {
  font-size: 0.9375rem;
  font-weight: 700;
  color: hsl(var(--foreground));
}

.music-queue-count {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  margin-left: 0.625rem;
  font-weight: 500;
}

.music-queue-clear {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  margin-left: auto;
  padding: 0.375rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 500;
  border: none;
  border-radius: 0.5rem;
  background: none;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-queue-clear:hover {
  color: hsl(var(--destructive));
  background: hsl(var(--destructive) / 0.1);
}

.music-queue-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  border: none;
  background: none;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  margin-left: 0.5rem;
  transition: all 0.15s ease;
}

.music-queue-close:hover {
  background: hsl(var(--muted));
  color: hsl(var(--foreground));
}

.music-queue-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.625rem;
  color: hsl(var(--muted-foreground) / 0.4);
  font-size: 0.875rem;
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
  background: hsl(var(--primary) / 0.08);
}

.music-queue-item-index {
  width: 1.75rem;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  text-align: center;
  flex-shrink: 0;
  font-weight: 500;
}

.music-queue-item-cover {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.375rem;
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
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-queue-item-artist {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 0.125rem;
}

.music-queue-item-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.375rem;
  border: none;
  background: none;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  opacity: 0;
  transition: all 0.15s ease;
}

.music-queue-item:hover .music-queue-item-remove {
  opacity: 1;
}

.music-queue-item-remove:hover {
  background: hsl(var(--muted));
  color: hsl(var(--destructive));
}

@media (max-width: 768px) {
  .music-queue-panel {
    left: 1rem;
    right: 1rem;
    width: auto;
    max-width: 24rem;
    margin: 0 auto;
  }
}
</style>