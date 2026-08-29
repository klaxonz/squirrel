<template>
  <div class="music-bar-actions">
    <div class="music-bar-volume">
      <Button variant="secondary" size="sm" icon-only title="音量" aria-label="静音/取消静音" @click="$emit('toggle-mute')">
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

    <PopoverTrigger as-child>
      <Button class="music-bar-queue" variant="secondary" size="sm" title="播放队列" aria-label="播放队列">
        <AppIcon name="playlistMusic" class="h-4 w-4" />
        <span v-if="queueCount" class="music-bar-queue-count" aria-hidden="true">
          {{ queueCount > 99 ? '99+' : queueCount }}
        </span>
      </Button>
    </PopoverTrigger>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { PopoverTrigger } from 'reka-ui'
import AppIcon from '@/shared/icons/AppIcon.vue'
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
  width: 100%;
  min-width: 0;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}

.music-bar-volume {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  min-width: 0;
}

.music-bar-range {
  -webkit-appearance: none;
  appearance: none;
  height: 3px;
  width: 5.5rem;
  max-width: 30vw;
  border-radius: 9999px;
  background: linear-gradient(
    to right,
    hsl(var(--primary)) var(--slider-progress, 0%),
    hsl(var(--border) / 0.4) var(--slider-progress, 0%)
  );
  outline: none;
  cursor: pointer;
  transition: height 0.15s ease;
}

.music-bar-range:hover,
.music-bar-range:focus-visible {
  height: 5px;
}

.music-bar-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  background: hsl(var(--primary));
  border: 2px solid hsl(var(--background));
  opacity: 0;
  transition: opacity 0.15s ease;
}

.music-bar-range:hover::-webkit-slider-thumb,
.music-bar-range:focus-visible::-webkit-slider-thumb {
  opacity: 1;
}

.music-bar-queue {
  --sq-button-height: 2rem;
  border-left: 1px solid var(--app-hairline);
  border-radius: 0;
  padding-left: var(--space-3);
}

.music-bar-queue-count {
  min-width: 1rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-badge-size);
  font-variant-numeric: tabular-nums;
  text-align: left;
}

@media (max-width: 680px) {
  .music-bar-queue {
    border-left: 0;
    padding-left: 0.5rem;
  }

  .music-bar-queue-count {
    display: none;
  }
}
</style>
