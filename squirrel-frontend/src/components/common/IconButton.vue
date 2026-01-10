<template>
  <button
    :class="[
      'inline-flex items-center justify-center rounded-full transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-bg-primary disabled:opacity-50 disabled:cursor-not-allowed',
      sizeClasses,
      variantClasses,
      customClass
    ]"
    :type="type"
    :disabled="disabled"
    :title="title"
    :aria-label="ariaLabel || title"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'ghost',
    validator: (value) => ['ghost', 'default'].includes(value)
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  },
  disabled: {
    type: Boolean,
    default: false
  },
  type: {
    type: String,
    default: 'button',
    validator: (value) => ['button', 'submit', 'reset'].includes(value)
  },
  title: {
    type: String,
    default: ''
  },
  ariaLabel: {
    type: String,
    default: ''
  },
  customClass: {
    type: String,
    default: ''
  }
})

defineEmits(['click'])

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'p-1.5'
    case 'lg':
      return 'p-2.5'
    default:
      return 'p-2'
  }
})

const variantClasses = computed(() => {
  switch (props.variant) {
    case 'default':
      return 'bg-bg-tertiary text-text-accent hover:bg-bg-elevated border border-border-primary'
    default:
      return 'bg-transparent text-text-accent hover:bg-bg-elevated border border-transparent'
  }
})
</script>
