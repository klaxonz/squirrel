<template>
  <div class="progress-bar">
    <div
      :class="[
        'progress-track rounded-full overflow-hidden',
        sizeClasses
      ]"
      :style="{ backgroundColor: trackColor }"
    >
      <div
        class="progress-indicator rounded-full transition-all duration-300 ease-out"
        :style="{
          width: `${Math.min(100, Math.max(0, percent))}%`,
          backgroundColor: indicatorColor
        }"
      />
    </div>

    <div v-if="showLabel" class="progress-label mt-1 text-xs text-text-secondary">
      {{ Math.round(percent) }}%
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  percent: {
    type: Number,
    default: 0,
    validator: (value) => value >= 0 && value <= 100
  },
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'success', 'error', 'warning'].includes(value)
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  },
  showLabel: {
    type: Boolean,
    default: false
  }
})

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'h-1'
    case 'lg':
      return 'h-3'
    default:
      return 'h-2'
  }
})

const trackColor = computed(() => {
  return 'var(--bg-tertiary)'
})

const indicatorColor = computed(() => {
  switch (props.variant) {
    case 'success':
      return 'var(--color-success)'
    case 'error':
      return 'var(--color-error)'
    case 'warning':
      return 'var(--color-warning)'
    default:
      return '#f00' // 保持原有红色
  }
})
</script>
