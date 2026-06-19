<template>
  <Transition name="sp-loading-fade">
    <div v-if="visible" class="sp-error-overlay" @click.stop>
      <div class="sp-error-content">
        <div class="sp-error-icon">
          <PlayerIcon name="error" class="sp-error-icon-svg" />
        </div>
        <div class="sp-error-title">{{ title || fallbackTitle }}</div>
        <div class="sp-error-message">{{ message }}</div>
        <div class="sp-error-actions">
          <button v-if="canRetry" class="sp-error-retry-btn" @click.stop="$emit('retry')">
            {{ retryLabel }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import PlayerIcon from './PlayerIcon.vue'

interface Props {
  visible: boolean
  title?: string
  message?: string
  canRetry?: boolean
  fallbackTitle: string
  retryLabel: string
}

defineProps<Props>()
defineEmits<{ retry: [] }>()
</script>

<style scoped>
.sp-loading-fade-enter-active,
.sp-loading-fade-leave-active {
  transition: opacity var(--duration-slow) var(--ease-default);
}

.sp-loading-fade-enter-from,
.sp-loading-fade-leave-to {
  opacity: 0;
}

/* Error overlay */
.sp-error-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
}

.sp-error-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 32px 24px;
  max-width: 320px;
  text-align: center;
}

.sp-error-icon-svg {
  width: 36px;
  height: 36px;
  color: var(--sp-primary, #d3d4d8);
  opacity: 0.7;
}

.sp-error-title {
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.sp-error-message {
  color: rgba(255, 255, 255, 0.55);
  font-size: 12px;
  line-height: 1.5;
}

.sp-error-actions {
  margin-top: 4px;
}

.sp-error-retry-btn {
  padding: 6px 18px;
  background: var(--sp-primary, #d3d4d8);
  color: #000;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity var(--duration-fast) var(--ease-default);
  letter-spacing: 0.03em;
}

.sp-error-retry-btn:hover {
  opacity: 0.85;
}
</style>
