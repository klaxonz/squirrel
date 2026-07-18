<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed } from 'vue'
import PrimeTag from 'primevue/tag'
import type { BadgeVariant } from '.'

const props = withDefaults(defineProps<{
  variant?: BadgeVariant
  class?: HTMLAttributes['class']
}>(), {
  variant: 'default',
})

const severity = computed(() => {
  if (props.variant === 'success') return 'success'
  if (props.variant === 'warning') return 'warn'
  if (props.variant === 'destructive' || props.variant === 'error') return 'danger'
  if (props.variant === 'secondary' || props.variant === 'muted' || props.variant === 'outline') return 'secondary'
  return 'primary'
})
</script>

<template>
  <PrimeTag :severity="severity" :class="props.class">
    <slot />
  </PrimeTag>
</template>
