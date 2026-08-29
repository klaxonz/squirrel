<template>
  <div class="music-bar-controls">
    <div class="music-bar-buttons">
      <Button
        text variant="secondary"
        size="sm" icon-only
        class="music-bar-mode-button"
        :class="{ 'app-selection-active': shuffle }"
        title="随机播放"
        aria-label="随机播放"
        :aria-pressed="shuffle"
        @click="$emit('shuffle')"
      >
        <AppIcon name="shuffle" class="h-4 w-4" />
      </Button>

      <Button
        text variant="secondary"
        size="sm" icon-only
        class="music-bar-step-button"
        :disabled="!canStep"
        title="上一首"
        aria-label="上一首"
        @click="$emit('previous')"
      >
        <AppIcon name="previous" class="h-4 w-4" />
      </Button>

      <Button
        rounded
        size="sm" icon-only
        class="music-bar-primary-button"
        :disabled="loading"
        :title="playing ? '暂停' : '播放'"
        :aria-label="playing ? '暂停' : '播放'"
        :aria-pressed="playing"
        @click="$emit('toggle')"
      >
        <AppSpinner v-if="loading" size="md" />
        <AppIcon v-else-if="playing" name="pause" class="h-5 w-5" />
        <AppIcon v-else name="play" class="h-5 w-5" />
      </Button>

      <Button
        text variant="secondary"
        size="sm" icon-only
        class="music-bar-step-button"
        :disabled="!canStep"
        title="下一首"
        aria-label="下一首"
        @click="$emit('next')"
      >
        <AppIcon name="next" class="h-4 w-4" />
      </Button>

      <Button
        text variant="secondary"
        size="sm" icon-only
        class="music-bar-mode-button"
        :class="{ 'app-selection-active': repeat !== 'none' }"
        :title="repeatTitle"
        :aria-label="repeatTitle"
        :aria-pressed="repeat !== 'none'"
        @click="$emit('repeat')"
      >
        <AppIcon v-if="repeat === 'one'" name="repeatOne" class="h-4 w-4" />
        <AppIcon v-else name="refresh" class="h-4 w-4" />
      </Button>
    </div>

    <slot name="time" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Spinner as AppSpinner } from '@/shared/ui/skeleton'
import { Button } from '@/shared/ui/button'

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
  width: 100%;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.125rem;
}

.music-bar-buttons {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
}

.music-bar-mode-button {
  --sq-button-height: 1.75rem;
}

.music-bar-step-button {
  --sq-button-height: 2rem;
}

.music-bar-primary-button {
  --sq-button-height: 2.5rem;
  margin-inline: 0.125rem;
}

@media (max-width: 680px) {
  .music-bar-mode-button {
    display: none;
  }
}
</style>
