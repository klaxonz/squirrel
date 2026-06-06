<template>
  <button
    class="music-bar-track-info"
    :class="{ 'music-bar-track-info--clickable': clickable }"
    @click="clickable && $emit('click')"
  >
    <div class="music-bar-cover">
      <img
        v-if="track?.cover"
        :src="track.cover"
        alt=""
        class="h-full w-full object-cover"
      />
      <AppIcon v-else name="playlistMusic" class="h-4 w-4" />
    </div>
    <div class="music-bar-text">
      <span class="music-bar-title">{{ track?.title || '未在播放' }}</span>
      <span v-if="error" class="music-bar-error" :title="error">{{ error }}</span>
      <span v-else class="music-bar-artist">{{ track?.artist || '酷狗音乐' }}</span>
    </div>
  </button>
</template>

<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue'
import type { MusicTrack } from '@/api/music'

withDefaults(defineProps<{
  track?: MusicTrack | null
  clickable?: boolean
  error?: string
}>(), {
  clickable: false,
  error: '',
})

defineEmits<{
  click: []
}>()
</script>

<style scoped>
.music-bar-track-info {
  display: flex;
  min-width: 0;
  width: 220px;
  flex-shrink: 0;
  align-items: center;
  gap: 0.625rem;
  border-radius: 0.375rem;
  padding: 0.25rem;
  border: none;
  background: none;
  color: inherit;
  text-align: left;
  cursor: default;
}

.music-bar-track-info--clickable {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.music-bar-track-info--clickable:hover {
  background: hsl(var(--muted) / 0.5);
}

.music-bar-cover {
  display: flex;
  width: 2rem;
  height: 2rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 0.3125rem;
  background: hsl(var(--muted) / 0.4);
  box-shadow: 0 2px 8px hsl(var(--foreground) / 0.08);
  color: hsl(var(--muted-foreground));
}

.music-bar-text {
  flex: 1;
  min-width: 0;
}

.music-bar-title {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-bar-artist {
  display: block;
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
  margin-top: 0.125rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-bar-error {
  display: block;
  margin-top: 0.125rem;
  overflow: hidden;
  color: hsl(var(--destructive));
  font-size: 0.6875rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .music-bar-track-info {
    width: 220px;
  }
}
</style>
