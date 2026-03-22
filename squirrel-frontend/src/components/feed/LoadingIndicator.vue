<template>
  <div v-if="loading" class="loading-container" :class="sizeClass">
    <div class="loading-spinner">
      <div 
        v-for="i in 3" 
        :key="i" 
        class="bounce-dot" 
        :style="{ animationDelay: `${(i - 1) * 0.2}s` }" 
      />
    </div>
    <p v-if="text" class="loading-text">{{ text }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  loading: { 
    type: Boolean, 
    default: true 
  },
  text: { 
    type: String, 
    default: '' 
  },
  size: { 
    type: String, 
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  }
});

const sizeClass = computed(() => `size-${props.size}`);
</script>

<style scoped>
.loading-container {
  @apply flex flex-col items-center justify-center;
}

.loading-container.size-sm {
  @apply py-2;
}

.loading-container.size-md {
  @apply py-4;
}

.loading-container.size-lg {
  @apply py-8;
}

.loading-spinner {
  @apply flex items-center space-x-2;
}

.size-sm .bounce-dot {
  @apply w-1.5 h-1.5;
}

.size-md .bounce-dot {
  @apply w-2 h-2;
}

.size-lg .bounce-dot {
  @apply w-3 h-3;
}

.bounce-dot {
  @apply bg-destructive rounded-full;
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-text {
  @apply mt-2 text-sm text-muted-foreground;
}

@keyframes bounce {
  0%, 80%, 100% { 
    transform: scale(0);
    opacity: 0.5;
  }
  40% { 
    transform: scale(1);
    opacity: 1;
  }
}
</style>

