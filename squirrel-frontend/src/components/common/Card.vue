<template>
  <div
    :class="[
      'card rounded-lg border overflow-hidden transition-all duration-200',
      variantClasses,
      hoverEffect && 'hover:shadow-md hover:transform hover:-translate-y-0.5'
    ]"
  >
    <slot />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'elevated', 'outlined'].includes(value)
  },
  hoverEffect: {
    type: Boolean,
    default: false
  }
})

const variantClasses = computed(() => {
  switch (props.variant) {
    case 'elevated':
      return 'bg-bg-elevated border-border-secondary shadow-md'
    case 'outlined':
      return 'bg-transparent border-border-primary'
    default:
      return 'bg-bg-card border-border-primary'
  }
})
</script>
