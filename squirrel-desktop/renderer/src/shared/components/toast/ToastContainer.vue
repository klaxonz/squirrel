<template>
  <div
    class="app-toast"
    :class="[`app-toast--${toast.variant}`]"
    :role="toast.variant === 'error' ? 'alert' : 'status'"
    :aria-live="toast.variant === 'error' ? 'assertive' : 'polite'"
    aria-atomic="true"
  >
    <AppIcon :name="iconName" class="app-toast__icon" />
    <span class="app-toast__message">{{ toast.message }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'
import type { ToastItem } from './useToast'

const props = defineProps<{
  toast: ToastItem
}>()

const iconNames: Record<ToastItem['variant'], AppIconName> = {
  error: 'warning',
  info: 'info',
  success: 'statusSuccess',
}
const iconName = computed(() => iconNames[props.toast.variant])
</script>

<style scoped>
.app-toast {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: var(--app-toast-padding);
  border-radius: var(--app-toast-radius);
  font-size: var(--app-toast-font-size);
  font-weight: 500;
  box-shadow: var(--app-toast-shadow);
  pointer-events: auto;
  max-width: min(24rem, calc(100vw - 3rem));
}

.app-toast--success {
  background: var(--app-toast-success-bg);
  color: var(--app-toast-success-fg);
}

.app-toast--error {
  background: var(--app-toast-error-bg);
  color: var(--app-toast-error-fg);
  border: 1px solid var(--app-toast-error-border);
}

.app-toast--info {
  background: var(--app-toast-info-bg);
  color: var(--app-toast-info-fg);
  border: 1px solid var(--app-toast-info-border);
}

.app-toast__icon {
  width: 1rem;
  height: 1rem;
  flex: none;
}

.app-toast__message {
  line-height: 1.4;
}
</style>
