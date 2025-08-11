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
    border border-red-500/30 shadow-2xl z-40;
  background: rgba(40, 40, 40, 0.95);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
  animation: errorMessageShow 0.3s ease-out;
}

.error-content {
  @apply flex items-start gap-4 mb-6;
}

.error-icon {
  @apply text-red-500 text-3xl flex-shrink-0 mt-1;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
}

.error-text {
  @apply flex-1;
}

.error-title {
  @apply text-white font-semibold text-lg mb-2;
  font-family: 'Roboto', sans-serif;
}

.error-description {
  @apply text-white/80 text-sm mb-3;
  font-family: 'Roboto', sans-serif;
  line-height: 1.5;
}

.error-suggestions {
  @apply mt-4;
}

.suggestions-title {
  @apply text-white/90 text-sm font-medium mb-2;
  font-family: 'Roboto', sans-serif;
}

.suggestions-list {
  @apply text-white/70 text-sm space-y-1 pl-4;
  font-family: 'Roboto', sans-serif;
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
  font-family: 'Roboto', sans-serif;
}

.retry-button {
  @apply text-white
    disabled:opacity-50 disabled:cursor-not-allowed;
  background: #ff0000;
}

.retry-button:hover:not(:disabled) {
  background: #cc0000;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(255, 0, 0, 0.3);
}

.report-button {
  @apply bg-blue-600 hover:bg-blue-700 text-white;
}

.report-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.dismiss-button {
  @apply bg-gray-600 hover:bg-gray-700 text-white;
}

.dismiss-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(75, 85, 99, 0.3);
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
