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
    bg-black/90 backdrop-blur-sm rounded-lg p-6 max-w-md w-full mx-4
    border border-red-500/20 shadow-xl z-40;
}

.error-content {
  @apply flex items-start gap-4 mb-6;
}

.error-icon {
  @apply text-red-500 text-2xl flex-shrink-0 mt-1;
}

.error-text {
  @apply flex-1;
}

.error-title {
  @apply text-white font-semibold text-lg mb-2;
}

.error-description {
  @apply text-white/80 text-sm mb-3;
}

.error-suggestions {
  @apply mt-3;
}

.suggestions-title {
  @apply text-white/90 text-sm font-medium mb-2;
}

.suggestions-list {
  @apply text-white/70 text-sm space-y-1 pl-4;
}

.suggestions-list li {
  @apply list-disc;
}

.error-actions {
  @apply flex flex-wrap gap-2 justify-end;
}

.retry-button,
.report-button,
.dismiss-button {
  @apply px-4 py-2 rounded-lg text-sm font-medium
    transition-colors duration-200 flex items-center gap-2;
}

.retry-button {
  @apply bg-red-600 hover:bg-red-700 text-white
    disabled:bg-gray-600 disabled:cursor-not-allowed;
}

.report-button {
  @apply bg-blue-600 hover:bg-blue-700 text-white;
}

.dismiss-button {
  @apply bg-gray-600 hover:bg-gray-700 text-white;
}
</style>
