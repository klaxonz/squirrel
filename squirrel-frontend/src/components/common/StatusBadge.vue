<template>
  <span
    :class="[
      'status-badge inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
      sizeClasses,
      variantClasses
    ]"
  >
    <span
      v-if="showDot"
      :class="[
        'w-1.5 h-1.5 rounded-full mr-1.5',
        dotColor
      ]"
    />
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'success', 'error', 'warning', 'info'].includes(value)
  },
  size: {
    type: String,
    default: 'sm',
    validator: (value) => ['xs', 'sm', 'md'].includes(value)
  },
  label: {
    type: String,
    default: ''
  },
  showDot: {
    type: Boolean,
    default: true
  }
})

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'xs':
      return 'text-2xs px-1.5 py-0.5'
    case 'md':
      return 'text-sm px-2.5 py-1'
    default:
      return 'text-xs px-2 py-0.5'
  }
})

const variantClasses = computed(() => {
  switch (props.variant) {
    case 'success':
      return 'bg-color-success/10 text-color-success'
    case 'error':
      return 'bg-color-error/10 text-color-error'
    case 'warning':
      return 'bg-color-warning/10 text-color-warning'
    case 'info':
      return 'bg-color-info/10 text-color-info'
    default:
      return 'bg-bg-elevated text-text-secondary'
  }
})

const dotColor = computed(() => {
  switch (props.variant) {
    case 'success':
      return 'bg-color-success'
    case 'error':
      return 'bg-color-error'
    case 'warning':
      return 'bg-color-warning'
    case 'info':
      return 'bg-color-info'
    default:
      return 'bg-text-muted'
  }
})
</script>
