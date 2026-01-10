<template>
  <button
    :class="[
      'button inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-bg-primary disabled:opacity-50 disabled:cursor-not-allowed',
      shapeClasses,
      sizeClasses,
      variantClasses,
      fullWidth && 'w-full'
    ]"
    :type="type"
    :disabled="disabled || loading"
    @click="handleClick"
  >
    <ArrowPathIcon v-if="loading" class="animate-spin h-4 w-4 mr-2" />
    <slot />
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowPathIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'primary', 'secondary', 'danger', 'ghost'].includes(value)
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['xs', 'sm', 'md', 'lg', 'xl'].includes(value)
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  fullWidth: {
    type: Boolean,
    default: false
  },
  shape: {
    type: String,
    default: 'md',
    validator: (value) => ['md', 'pill'].includes(value)
  },
  type: {
    type: String,
    default: 'button',
    validator: (value) => ['button', 'submit', 'reset'].includes(value)
  }
})

const emit = defineEmits(['click'])

const handleClick = (event) => {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'xs':
      return 'px-2 py-1 text-xs'
    case 'sm':
      return 'px-3 py-1.5 text-sm'
    case 'lg':
      return 'px-4 py-2.5 text-lg'
    case 'xl':
      return 'px-6 py-3 text-xl'
    default:
      return 'px-4 py-2 text-base'
  }
})

const shapeClasses = computed(() => {
  switch (props.shape) {
    case 'pill':
      return 'rounded-full'
    default:
      return 'rounded-md'
  }
})

const variantClasses = computed(() => {
  switch (props.variant) {
    case 'primary':
      return 'bg-color-info text-text-accent hover:bg-color-info-hover focus:ring-color-info'
    case 'secondary':
      return 'bg-bg-elevated text-text-primary hover:bg-bg-card focus:ring-text-muted border border-border-primary'
    case 'danger':
      return 'bg-color-error text-text-accent hover:bg-color-error-hover focus:ring-color-error'
    case 'ghost':
      return 'bg-transparent text-text-primary hover:bg-bg-elevated focus:ring-text-muted'
    default:
      return 'bg-bg-tertiary text-text-primary hover:bg-bg-elevated focus:ring-text-muted'
  }
})
</script>
