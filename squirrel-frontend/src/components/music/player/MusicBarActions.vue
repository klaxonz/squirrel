<template>
  <div class="music-bar-actions">
    <button
      v-if="track?.album_audio_id"
      class="music-bar-btn"
      :class="{ 'music-bar-btn--liked': liked }"
      :title="liked ? '取消喜欢' : '喜欢'"
      @click="$emit('like')"
    >
      <AppIcon name="heart" class="h-4 w-4" :class="{ 'fill-primary text-primary': liked }" />
    </button>

    <div class="music-bar-volume">
      <button class="music-bar-btn" title="音量" @click="$emit('toggle-mute')">
        <AppIcon :name="volumeIcon" class="h-4 w-4" />
      </button>
      <input
        class="music-bar-range"
        type="range"
        min="0"
        max="1"
        step="0.05"
        :value="volume"
        :style="{ '--slider-progress': `${volume * 100}%` }"
        @input="$emit('volume', Number(($event.target as HTMLInputElement).value))"
      />
    </div>

    <button class="music-bar-btn" title="播放队列" @click="$emit('queue')">
      <AppIcon name="playlistMusic" class="h-4 w-4" />
      <span v-if="queueCount" class="music-bar-badge">
        {{ queueCount > 99 ? '99+' : queueCount }}
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import type { MusicTrack } from '@/api/music'

const props = withDefaults(defineProps<{
  track?: MusicTrack | null
  liked?: boolean
  volume?: number
  queueCount?: number
}>(), {
  liked: false,
  volume: 0.7,
  queueCount: 0,
})

defineEmits<{
  like: []
  'toggle-mute': []
  volume: [value: number]
  queue: []
}>()

const volumeIcon = computed(() => {
  if (props.volume === 0) return 'volumeOff'
  if (props.volume < 0.4) return 'volumeLow'
  return 'volumeHigh'
})

</script>

<style scoped>
.music-bar-actions {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  flex-shrink: 0;
  width: auto;
  justify-content: flex-end;
}

.music-bar-btn {
  display: flex;
  height: 1.875rem;
  width: 1.875rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  border: none;
  background: none;
  color: hsl(var(--foreground) / 0.6);
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
  position: relative;
}

.music-bar-btn:hover {
  background: hsl(var(--muted) / 0.6);
  color: hsl(var(--foreground));
}

.music-bar-btn--liked {
  color: hsl(var(--primary));
}

.music-bar-volume {
  display: flex;
  align-items: center;
  gap: 0.125rem;
}

.music-bar-range {
  -webkit-appearance: none;
  appearance: none;
  height: 3px;
  width: 4.25rem;
  border-radius: 9999px;
  background: linear-gradient(to right, hsl(var(--foreground) / 0.8) var(--slider-progress, 0%), hsl(var(--border) / 0.4) var(--slider-progress, 0%));
  outline: none;
  cursor: pointer;
  transition: height 0.15s ease;
}

.music-bar-range:hover {
  height: 5px;
}

.music-bar-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  background: hsl(var(--foreground));
  border: 2px solid hsl(var(--background));
  opacity: 0;
  transition: opacity 0.15s ease;
  box-shadow: 0 2px 6px hsl(var(--foreground) / 0.2);
}

.music-bar-range:hover::-webkit-slider-thumb {
  opacity: 1;
}

.music-bar-badge {
  position: absolute;
  top: 0;
  right: 0;
  font-size: 0.5rem;
  line-height: 1;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  padding: 2px 4px;
  border-radius: 9999px;
  font-weight: 700;
}

@media (max-width: 768px) {
  .music-bar-actions {
    flex: 1;
    width: auto;
    justify-content: flex-end;
  }

  .music-bar-volume {
    display: none;
  }
}
</style>
