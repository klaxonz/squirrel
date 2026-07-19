<template>
  <transition name="sp-info-fade">
    <div v-if="visible && fullscreen" class="sp-video-info-overlay">
      <div class="sp-video-info-title">{{ title || '未命名视频' }}</div>
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

<style scoped>
.sp-video-info-overlay {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 30;
  max-width: min(620px, 60%);
  pointer-events: none;
}

.sp-video-info-title {
  margin-bottom: 4px;
  color: #fff;
  font-family: var(--sp-font-family);
  font-size: clamp(16px, 1.6vw, 20px);
  font-weight: 650;
  line-height: 1.3;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.8);
}

.sp-video-info-meta {
  color: var(--sp-text-secondary);
  font-family: var(--sp-font-family);
  font-size: 12px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
}

.sp-info-fade-enter-active,
.sp-info-fade-leave-active {
  transition: opacity 0.4s ease;
}

.sp-info-fade-enter-from,
.sp-info-fade-leave-to {
  opacity: 0;
}

@container video-player (max-width: 560px) {
  .sp-video-info-overlay {
    top: 12px;
    left: 12px;
    max-width: calc(100% - 84px);
  }

  .sp-video-info-title {
    font-size: 15px;
  }
}
</style>
