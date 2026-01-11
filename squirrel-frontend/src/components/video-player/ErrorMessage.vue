<template>
  <div class="error-message">
    <div class="error-content">
      <Icon icon="material-symbols:error" class="error-icon" />
      <div class="error-text">
        <h3 class="error-title">{{ errorInfo?.title || '播放错误' }}</h3>
        <p class="error-description">{{ errorInfo?.message || '视频播放出现问题' }}</p>
        <div v-if="errorInfo?.suggestions" class="error-suggestions">
          <p class="suggestions-title">建议解决方案：</p>
          <ul class="suggestions-list">
            <li v-for="suggestion in errorInfo.suggestions" :key="suggestion">
              {{ suggestion }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <div class="error-actions">
      <button
        v-if="errorState.canRetry"
        @click="$emit('retry')"
        class="retry-button"
        :disabled="errorState.retryCount >= errorState.maxRetries"
      >
        <Icon icon="material-symbols:refresh" />
        重试 ({{ errorState.retryCount }}/{{ errorState.maxRetries }})
      </button>

      <button @click="$emit('report')" class="report-button">
        <Icon icon="material-symbols:bug-report" />
        报告问题
      </button>

      <button @click="$emit('dismiss')" class="dismiss-button">
        <Icon icon="material-symbols:close" />
        关闭
      </button>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

const props = defineProps({
  errorState: Object,
  errorInfo: Object
})

const emit = defineEmits(['retry', 'report', 'dismiss'])
</script>

<style scoped>
.error-message {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    rounded-xl p-6 max-w-md w-full mx-4
    z-40;
  background: var(--sp-surface);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(var(--sp-primary-rgb), 0.3);
  box-shadow: var(--sp-shadow-lg);
  animation: errorMessageShow 0.3s ease-out;
}

.error-content {
  @apply flex items-start gap-4 mb-6;
}

.error-icon {
  @apply text-3xl flex-shrink-0 mt-1;
  color: var(--sp-error);
  filter: drop-shadow(var(--sp-drop-shadow-md));
}

.error-text {
  @apply flex-1;
}

.error-title {
  @apply font-semibold text-lg mb-2;
  color: var(--sp-text);
  font-family: var(--sp-font-family);
}

.error-description {
  @apply text-sm mb-3;
  color: var(--sp-text-secondary);
  font-family: var(--sp-font-family);
  line-height: 1.5;
}

.error-suggestions {
  @apply mt-4;
}

.suggestions-title {
  @apply text-sm font-medium mb-2;
  color: var(--sp-text-strong);
  font-family: var(--sp-font-family);
}

.suggestions-list {
  @apply text-sm space-y-1 pl-4;
  color: var(--sp-text-secondary);
  font-family: var(--sp-font-family);
}

.suggestions-list li {
  @apply list-disc;
}

.error-actions {
  @apply flex flex-wrap gap-3 justify-end;
}

.retry-button,
.report-button,
.dismiss-button {
  @apply px-4 py-2 rounded-lg text-sm font-medium
    transition-all duration-200 flex items-center gap-2;
  font-family: var(--sp-font-family);
  color: var(--sp-text);
}

.retry-button {
  @apply disabled:opacity-50 disabled:cursor-not-allowed;
  background: var(--sp-error);
}

.retry-button:hover:not(:disabled) {
  background: var(--sp-error-hover);
  transform: translateY(-1px);
  box-shadow: var(--sp-shadow-md);
}

.report-button {
  background: var(--sp-info);
}

.report-button:hover {
  background: var(--sp-info-hover);
  transform: translateY(-1px);
  box-shadow: var(--sp-shadow-md);
}

.dismiss-button {
  background: var(--sp-bg-elevated);
}

.dismiss-button:hover {
  background: var(--sp-bg-hover);
  transform: translateY(-1px);
  box-shadow: var(--sp-shadow-md);
}

@keyframes errorMessageShow {
  0% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.9);
  }
  100% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}
</style>
