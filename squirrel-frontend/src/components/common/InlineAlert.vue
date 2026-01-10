<template>
  <div
    :class="[
      'inline-alert mt-2 mb-2 px-3 py-2 rounded border text-sm flex items-center justify-between gap-3',
      variantClasses
    ]"
  >
    <div class="min-w-0">
      <slot>
        <span>{{ message }}</span>
      </slot>
    </div>
    <Button
      v-if="actionLabel"
      size="xs"
      shape="pill"
      variant="ghost"
      @click="$emit('action')"
    >
      {{ actionLabel }}
    </Button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import Button from './Button.vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'error',
    validator: (value) => ['default', 'success', 'error', 'warning', 'info'].includes(value)
  },
  message: {
    type: String,
    default: ''
  },
  actionLabel: {
    type: String,
    default: ''
  }
})

defineEmits(['action'])

const variantClasses = computed(() => {
  switch (props.variant) {
    case 'success':
      return 'bg-color-success/10 text-color-success border-color-success/20'
    case 'warning':
      return 'bg-color-warning/10 text-color-warning border-color-warning/20'
    case 'info':
      return 'bg-color-info/10 text-color-info border-color-info/20'
    case 'default':
      return 'bg-bg-elevated text-text-secondary border-border-primary'
    default:
      return 'bg-color-error/10 text-color-error border-color-error/20'
  }
})
</script>
