<template>
  <Transition name="sp-loading-fade">
    <div v-if="visible" class="sp-error-overlay" role="alert" aria-live="assertive" @click.stop>
      <div class="sp-error-content">
        <div class="sp-error-icon">
          <PlayerIcon name="error" class="sp-error-icon-svg" />
        </div>
        <div class="sp-error-title">{{ title || fallbackTitle }}</div>
        <div class="sp-error-message">{{ message }}</div>
        <div class="sp-error-actions">
          <Button
            v-if="requiresAuth"
            size="sm"
            severity="secondary"
            outlined
            class="sp-error-auth-btn"
            @click.stop="$emit('auth')"
          >
            {{ authLabel }}
          </Button>
          <Button v-if="canRetry" size="sm" class="sp-error-retry-btn" @click.stop="$emit('retry')">
            {{ retryLabel }}
          </Button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import PlayerIcon from './PlayerIcon.vue'
import { Button } from '@/shared/ui/button'

interface Props {
  visible: boolean
  title?: string
  message?: string
  canRetry?: boolean
  requiresAuth?: boolean
  fallbackTitle: string
  retryLabel: string
  authLabel: string
}

defineProps<Props>()
defineEmits<{ retry: []; auth: [] }>()
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
  padding: 20px;
  background: var(--sp-error-bg, rgba(10, 10, 10, 0.9));
}

.sp-error-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  width: min(320px, 100%);
  padding: 24px;
  border: 1px solid var(--sp-menu-border);
  border-radius: var(--sp-radius-lg);
  background: var(--sp-menu-bg);
  box-shadow: var(--sp-menu-shadow);
  text-align: center;
}

.sp-error-icon-svg {
  width: 32px;
  height: 32px;
  color: var(--sp-error);
}

.sp-error-title {
  color: var(--sp-text-strong);
  font-family: var(--sp-font-family);
  font-size: 15px;
  font-weight: 650;
  letter-spacing: 0;
}

.sp-error-message {
  color: var(--sp-text-muted);
  font-family: var(--sp-font-family);
  font-size: 12px;
  line-height: 1.5;
}

.sp-error-actions {
  display: flex;
  margin-top: 6px;
  gap: 8px;
}

.sp-error-auth-btn {
  min-width: 92px;
  border-radius: var(--sp-radius-md);
  box-shadow: none;
}

.sp-error-retry-btn {
  min-width: 92px;
  background: var(--sp-primary);
  color: #fff;
  border-color: transparent;
  border-radius: var(--sp-radius-md);
  box-shadow: none;
}

.sp-error-retry-btn:hover {
  background: var(--sp-primary-hover);
}
</style>
