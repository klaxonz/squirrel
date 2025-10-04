<template>
  <div v-if="isVisible" class="progress-indicator">
    <!-- 紧凑模式 -->
    <div v-if="compact" class="compact-mode">
      <div class="flex items-center gap-2">
        <div class="spinner-container">
          <svg class="spinner" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" />
          </svg>
        </div>
        <span class="text-xs text-gray-600 dark:text-gray-400">
          {{ statusText }}
        </span>
        <span v-if="showPercentage && progress.progress_percentage" class="text-xs font-medium text-blue-600 dark:text-blue-400">
          {{ progress.progress_percentage }}%
        </span>
      </div>
    </div>

    <!-- 完整模式 -->
    <div v-else class="full-mode">
      <!-- 状态头部 -->
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center gap-2">
          <div v-if="isProcessing" class="spinner-container">
            <svg class="spinner" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" />
            </svg>
          </div>
          <div v-else-if="isError" class="text-red-500">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div v-else-if="isCompleted" class="text-green-500">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
            {{ statusText }}
          </span>
        </div>
        <span v-if="progress.progress_percentage" class="text-sm font-semibold text-blue-600 dark:text-blue-400">
          {{ progress.progress_percentage }}%
        </span>
      </div>

      <!-- 进度条 -->
      <div v-if="showProgressBar && progress.total_count > 0" class="progress-bar-container">
        <div class="progress-bar-bg">
          <div 
            class="progress-bar-fill"
            :style="{ width: `${progress.progress_percentage || 0}%` }"
            :class="{
              'bg-blue-500': isProcessing,
              'bg-green-500': isCompleted,
              'bg-red-500': isError
            }"
          />
        </div>
        <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
          <span>{{ progress.current_count || 0 }} / {{ progress.total_count }}</span>
          <span v-if="progress.message">{{ progress.message }}</span>
        </div>
      </div>

      <!-- 消息 -->
      <div v-if="progress.message && !showProgressBar" class="text-xs text-gray-600 dark:text-gray-400 mt-1">
        {{ progress.message }}
      </div>

      <!-- 错误信息 -->
      <div v-if="progress.error_message" class="text-xs text-red-500 mt-1 truncate" :title="progress.error_message">
        {{ progress.error_message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  progress: {
    type: Object,
    default: null
  },
  compact: {
    type: Boolean,
    default: false
  },
  showPercentage: {
    type: Boolean,
    default: true
  },
  showProgressBar: {
    type: Boolean,
    default: true
  },
  hideWhenIdle: {
    type: Boolean,
    default: false
  }
});

const isVisible = computed(() => {
  if (!props.progress) return false;
  if (props.hideWhenIdle && !isProcessing.value) return false;
  return true;
});

const isProcessing = computed(() => {
  if (!props.progress || !props.progress.event_type) return false;
  const eventType = props.progress.event_type;
  return eventType.includes('_start') || eventType.includes('_progress');
});

const isCompleted = computed(() => {
  if (!props.progress || !props.progress.event_type) return false;
  return props.progress.event_type.includes('_complete');
});

const isError = computed(() => {
  if (!props.progress || !props.progress.event_type) return false;
  return props.progress.event_type.includes('_error') || !!props.progress.error_message;
});

const statusText = computed(() => {
  if (!props.progress) return '';
  
  const eventType = props.progress.event_type;
  
  if (eventType.includes('subscription_update_start')) return '正在更新订阅...';
  if (eventType.includes('subscription_update_complete')) return '更新完成';
  if (eventType.includes('subscription_update_error')) return '更新失败';
  if (eventType.includes('batch_process_progress')) return '处理中...';
  if (eventType.includes('video_extraction_start')) return '正在提取视频...';
  if (eventType.includes('video_extraction_complete')) return '提取完成';
  if (eventType.includes('video_extraction_error')) return '提取失败';
  
  return '处理中...';
});
</script>

<style scoped>
.progress-indicator {
  @apply rounded-lg;
}

.compact-mode {
  @apply py-1;
}

.full-mode {
  @apply p-3 bg-gray-50 dark:bg-gray-800 rounded-lg;
}

.spinner-container {
  @apply w-4 h-4;
}

.spinner {
  @apply w-full h-full animate-spin;
}

.spinner circle {
  @apply fill-none stroke-blue-500 dark:stroke-blue-400;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-dasharray: 50;
  stroke-dashoffset: 25;
  animation: spinner-dash 1.5s ease-in-out infinite;
}

@keyframes spinner-dash {
  0% {
    stroke-dasharray: 1, 150;
    stroke-dashoffset: 0;
  }
  50% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -35;
  }
  100% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -124;
  }
}

.progress-bar-container {
  @apply mt-2;
}

.progress-bar-bg {
  @apply w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden;
}

.progress-bar-fill {
  @apply h-full transition-all duration-300 ease-out rounded-full;
}
</style>

