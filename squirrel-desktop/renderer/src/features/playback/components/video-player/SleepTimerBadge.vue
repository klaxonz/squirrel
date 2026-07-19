<template>
  <div v-if="fullscreen && visible" class="sp-sleep-badge" role="status">
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

<style scoped>
.sp-sleep-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 1px solid var(--sp-menu-border);
  border-radius: var(--sp-radius-md);
  background: var(--sp-menu-bg);
  box-shadow: var(--sp-menu-shadow);
  color: var(--sp-text-secondary);
  font-family: var(--sp-font-mono);
  font-size: 12px;
  font-weight: 700;
}

.sp-sleep-badge :deep(svg) {
  width: 14px;
  height: 14px;
}
</style>
