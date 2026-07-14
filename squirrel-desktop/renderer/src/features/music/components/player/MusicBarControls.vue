<template>
  <div class="music-bar-controls">
    <slot name="time" />

    <div class="music-bar-buttons">
      <Button
        variant="ghost"
        size="icon-sm"
        :class="{ 'text-primary': shuffle }"
        title="随机播放"
        aria-label="随机播放"
        :aria-pressed="shuffle"
        @click="$emit('shuffle')"
      >
        <AppIcon name="shuffle" class="h-4 w-4" />
      </Button>

      <Button
        variant="ghost"
        size="icon-sm"
        :disabled="!canStep"
        title="上一首"
        aria-label="上一首"
        @click="$emit('previous')"
      >
        <AppIcon name="previous" class="h-4 w-4" />
      </Button>

      <Button
        variant="player"
        size="player-sm"
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
        variant="ghost"
        size="icon-sm"
        :disabled="!canStep"
        title="下一首"
        aria-label="下一首"
        @click="$emit('next')"
      >
        <AppIcon name="next" class="h-4 w-4" />
      </Button>

      <Button
        variant="ghost"
        size="icon-sm"
        :class="{ 'text-primary': repeat !== 'none' }"
        :title="repeatTitle"
        :aria-label="repeatTitle"
        :aria-pressed="repeat !== 'none'"
        @click="$emit('repeat')"
      >
        <AppIcon v-if="repeat === 'one'" name="repeatOne" class="h-4 w-4" />
        <AppIcon v-else name="refresh" class="h-4 w-4" />
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
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

</style>
