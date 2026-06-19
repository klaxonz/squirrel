<template>
  <div v-if="fullscreen && visible" class="sp-sleep-badge">
    <PlayerIcon name="sleepTimer" />
    <span>{{ remainingText }}</span>
  </div>
</template>

<script setup lang="ts">
import PlayerIcon from './PlayerIcon.vue'

defineProps<{
  fullscreen: boolean
  visible: boolean
  remainingText: string
}>()
</script>
