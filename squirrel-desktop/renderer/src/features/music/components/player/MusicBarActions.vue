<template>
  <div class="music-bar-actions">
    <div class="music-bar-volume">
      <Button variant="ghost" size="icon-sm" title="音量" aria-label="静音/取消静音" @click="$emit('toggle-mute')">
        <AppIcon :name="volumeIcon" class="h-4 w-4" />
      </Button>
      <input
        class="music-bar-range"
        type="range"
        min="0"
        max="1"
        step="0.05"
        :value="volume"
        aria-label="音量"
        :style="{ '--slider-progress': `${volume * 100}%` }"
        @input="$emit('volume', Number(($event.target as HTMLInputElement).value))"
      />
    </div>

    <Button class="relative" variant="ghost" size="icon-sm" title="播放队列" aria-label="播放队列" @click="$emit('queue')">
      <AppIcon name="playlistMusic" class="h-4 w-4" />
      <Badge v-if="queueCount" class="music-bar-badge">
        {{ queueCount > 99 ? '99+' : queueCount }}
      </Badge>
    </Button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'

const props = withDefaults(defineProps<{
  volume?: number
  queueCount?: number
}>(), {
  volume: 0.7,
  queueCount: 0,
})

defineEmits<{
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
  top: -0.125rem;
  right: -0.25rem;
  font-size: 0.5rem;
  line-height: 1;
  padding: 0.0625rem 0.25rem;
}
</style>
