<template>
  <div class="music-bar-controls">
    <slot name="time" />

    <div class="music-bar-buttons">
      <button
        class="music-bar-btn"
        :class="{ 'music-bar-btn--active': shuffle }"
        title="随机播放"
        @click="$emit('shuffle')"
      >
        <AppIcon name="shuffle" class="h-4 w-4" />
      </button>

      <button
        class="music-bar-btn"
        :disabled="!canStep"
        title="上一首"
        @click="$emit('previous')"
      >
        <AppIcon name="previous" class="h-4 w-4" />
      </button>

      <button
        class="music-bar-btn music-bar-btn--play"
        :disabled="loading"
        title="播放/暂停"
        @click="$emit('toggle')"
      >
        <AppIcon v-if="loading" name="loadingSpinner" class="h-5 w-5 animate-spin" />
        <AppIcon v-else-if="playing" name="pause" class="h-5 w-5" />
        <AppIcon v-else name="play" class="h-5 w-5" />
      </button>

      <button
        class="music-bar-btn"
        :disabled="!canStep"
        title="下一首"
        @click="$emit('next')"
      >
        <AppIcon name="next" class="h-4 w-4" />
      </button>

      <button
        class="music-bar-btn"
        :class="{ 'music-bar-btn--active': repeat !== 'none' }"
        :title="repeatTitle"
        @click="$emit('repeat')"
      >
        <AppIcon v-if="repeat === 'one'" name="repeatOne" class="h-4 w-4" />
        <AppIcon v-else name="refresh" class="h-4 w-4" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'

const props = withDefaults(defineProps<{
  playing?: boolean
  shuffle?: boolean
  repeat?: 'none' | 'all' | 'one'
  canStep?: boolean
  loading?: boolean
}>(), {
  playing: false,
  shuffle: false,
  repeat: 'none',
  canStep: false,
  loading: false,
})

defineEmits<{
  toggle: []
  previous: []
  next: []
  shuffle: []
  repeat: []
}>()

const repeatTitle = computed(() => {
  if (props.repeat === 'all') return '列表循环'
  if (props.repeat === 'one') return '单曲循环'
  return '顺序播放'
})
</script>

<style scoped>
.music-bar-controls {
  display: flex;
  flex: 1;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 0.625rem;
}

.music-bar-buttons {
  display: flex;
  align-items: center;
  gap: 0.1875rem;
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
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
}

.music-bar-btn:hover {
  background: hsl(var(--muted) / 0.6);
  color: hsl(var(--foreground));
}

.music-bar-btn:disabled {
  opacity: 0.25;
  cursor: not-allowed;
}

.music-bar-btn--active {
  color: hsl(var(--primary));
}

.music-bar-btn--play {
  width: 2rem;
  height: 2rem;
  border-radius: 9999px;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  box-shadow: 0 3px 10px hsl(var(--foreground) / 0.14);
}

.music-bar-btn--play:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 14px hsl(var(--foreground) / 0.18);
}

.music-bar-btn--play:active {
  transform: scale(0.96);
}

.music-bar-btn--play:disabled {
  background: hsl(var(--muted-foreground) / 0.2);
  color: hsl(var(--muted-foreground) / 0.4);
  box-shadow: none;
}
</style>
