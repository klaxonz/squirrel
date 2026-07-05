<template>
  <Button
    variant="player"
    size="player-sm"
    :class="{ 'bg-primary/10': isPlaying }"
    :aria-label="isPlaying ? '暂停' : '播放'"
    :aria-pressed="isPlaying"
    @click="$emit('click')"
  >
    <AppSpinner v-if="loading" size="sm" />
    <AppIcon v-else-if="isPlaying" name="pause" class="h-4 w-4" />
    <AppIcon v-else name="play" class="h-4 w-4" />
  </Button>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import { Button } from '@/shared/ui/button'

withDefaults(defineProps<{
  isPlaying?: boolean
  loading?: boolean
}>(), {
  isPlaying: false,
  loading: false,
})

defineEmits<{
  click: []
}>()
</script>
