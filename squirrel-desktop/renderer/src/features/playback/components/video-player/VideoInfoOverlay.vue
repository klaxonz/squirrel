<template>
  <transition name="sp-info-fade">
    <div v-if="visible && fullscreen" class="sp-video-info-overlay">
      <div class="sp-video-info-title">{{ title || 'Untitled' }}</div>
      <div v-if="uploader" class="sp-video-info-meta">{{ uploader }}</div>
    </div>
  </transition>
</template>

<script setup lang="ts">
defineProps<{
  visible: boolean
  fullscreen: boolean
  title: string
  uploader?: string
}>()
</script>
