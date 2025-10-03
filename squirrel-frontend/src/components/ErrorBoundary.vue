<template>
  <div class="error-boundary-wrapper">
    <div v-if="error" class="error-container">
      <div class="error-content">
        <Icon icon="material-symbols:error-outline" class="error-icon" />
        <p class="error-message">{{ errorMessage }}</p>
        <button 
          v-if="showRetry"
          @click="handleRetry" 
          class="retry-button"
        >
          重试
        </button>
      </div>
    </div>
    <slot v-else />
  </div>
</template>

<script setup>
import { ref, computed, onErrorCaptured } from 'vue';
import { Icon } from '@iconify/vue';

const props = defineProps({
  fallbackMessage: {
    type: String,
    default: '加载失败，请稍后重试'
  },
  showRetry: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['retry', 'error']);

const error = ref(null);

const errorMessage = computed(() => {
  if (!error.value) return '';
  return error.value.message || props.fallbackMessage;
});

onErrorCaptured((err) => {
  error.value = err;
  emit('error', err);
  // 阻止错误继续传播
  return false;
});

const handleRetry = () => {
  error.value = null;
  emit('retry');
};

// 对外暴露方法
defineExpose({
  reset: () => { error.value = null; },
  setError: (err) => { error.value = err; }
});
</script>

<style scoped>
.error-boundary-wrapper {
  @apply w-full h-full;
}

.error-container {
  @apply flex items-center justify-center min-h-[200px] p-6;
}

.error-content {
  @apply flex flex-col items-center text-center max-w-md;
}

.error-icon {
  @apply text-5xl text-red-500 mb-4;
}

.error-message {
  @apply text-gray-300 mb-4;
}

.retry-button {
  @apply px-6 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg;
  @apply transition-colors duration-200 font-medium;
}
</style>

