<template>
  <transition name="sp-info-fade">
    <div v-if="visible" class="sp-upnext-overlay" role="status" aria-live="polite" @click.stop>
      <div class="sp-upnext-label">{{ label }}</div>
      <div class="sp-upnext-title">{{ nextTitle }}</div>
      <div class="sp-upnext-countdown">{{ countdown }} 秒后自动播放</div>
      <Button size="sm" class="sp-upnext-btn" @click.stop="$emit('startNow')">{{ startNowLabel }}</Button>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { Button } from '@/shared/ui/button'

defineProps<{
  visible: boolean
  label: string
  nextTitle: string
  countdown: number
  startNowLabel: string
}>()

defineEmits<{
  startNow: []
}>()
</script>

<style scoped>
.sp-upnext-overlay {
  position: absolute;
  right: 12px;
  bottom: 72px;
  z-index: 30;
  width: min(280px, calc(100% - 24px));
  padding: 14px;
  border: 1px solid var(--sp-menu-border);
  border-radius: var(--sp-radius-lg);
  background: var(--sp-menu-bg);
  box-shadow: var(--sp-menu-shadow);
  cursor: default;
}

.sp-upnext-label {
  margin-bottom: 4px;
  color: var(--sp-text-muted);
  font-family: var(--sp-font-mono);
  font-size: 11px;
  font-weight: 600;
}

.sp-upnext-title {
  margin-bottom: 8px;
  color: var(--sp-text-strong);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.3;
}

.sp-upnext-countdown {
  margin-bottom: 10px;
  color: var(--sp-primary);
  font-family: var(--sp-font-mono);
  font-size: 11px;
}

.sp-upnext-btn {
  width: 100%;
  min-height: 32px;
  border-color: transparent;
  border-radius: var(--sp-radius-md);
  background: var(--sp-primary);
  box-shadow: none;
  color: #fff;
  font-size: 12px;
}

.sp-upnext-btn:hover {
  background: var(--sp-primary-hover);
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
  .sp-upnext-overlay {
    bottom: 60px;
  }
}
</style>
