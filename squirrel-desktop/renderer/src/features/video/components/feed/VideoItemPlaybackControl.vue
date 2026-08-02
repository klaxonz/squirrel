<template>
  <Button
    text
    class="video-item__playback-control"
    :aria-label="`播放：${title}`"
    data-playback-control
    @click="emit('activate')"
  >
    <span class="video-item__playback-label">播放：{{ title }}</span>
  </Button>
</template>

<script setup lang="ts">
import { Button } from '@/shared/ui/button'

defineProps<{ title: string }>()
const emit = defineEmits<{ activate: [] }>()
</script>
