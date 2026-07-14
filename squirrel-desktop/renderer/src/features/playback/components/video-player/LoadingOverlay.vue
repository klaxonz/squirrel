<template>
  <Transition name="sp-loading-fade">
    <div v-if="visible" class="sp-loading">
      <div class="sp-loader">
        <div class="sp-loader-ring"></div>
      </div>
      <div v-if="stageText" class="sp-loading-text">{{ stageText }}</div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
interface Props {
  visible: boolean
  stageText?: string | null
}

defineProps<Props>()
</script>

<style scoped>
.sp-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  z-index: 50;
  /* Loading overlay is purely presentational; let pointer events (click/dblclick)
     pass through to the video/container underneath so fullscreen toggling still
     works while the video is loading. */
  pointer-events: none;
}

.sp-loader {
  width: 28px;
  height: 28px;
  position: relative;
}

.sp-loader-ring {
  position: absolute;
  inset: 0;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-top-color: rgba(255, 255, 255, 0.6);
  border-radius: 50%;
  animation: sp-loader-spin 0.8s linear infinite;
}

.sp-loading-text {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  font-family: var(--sp-font-family);
  margin-top: 8px;
}

@keyframes sp-loader-spin {
  to { transform: rotate(360deg); }
}

/* 加载遮罩淡入淡出 */
.sp-loading-fade-enter-active,
.sp-loading-fade-leave-active {
  transition: opacity var(--duration-slow) var(--ease-default);
}

.sp-loading-fade-enter-from,
.sp-loading-fade-leave-to {
  opacity: 0;
}
</style>
