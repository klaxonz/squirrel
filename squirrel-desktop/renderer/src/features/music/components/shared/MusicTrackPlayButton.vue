<template>
  <Button
    outlined rounded
    size="sm" icon-only
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
import { Spinner as AppSpinner } from '@/shared/ui/skeleton'
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
