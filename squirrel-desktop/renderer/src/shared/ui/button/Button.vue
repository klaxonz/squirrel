<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed } from 'vue'
import PrimeButton from 'primevue/button'
import { cn } from '@/shared/lib/utils'
import type { ButtonSize, ButtonVariant } from '.'

const props = withDefaults(defineProps<{
  variant?: ButtonVariant
  size?: ButtonSize
  class?: HTMLAttributes['class']
  loading?: boolean
  disabled?: boolean
  iconOnly?: boolean
  rounded?: boolean
}>(), {
  variant: 'default',
  size: 'default',
  loading: false,
  disabled: false,
  iconOnly: false,
  rounded: false,
})

const severity = computed(() => {
  if (props.variant === 'destructive') return 'danger'
  if (props.variant === 'secondary' || props.variant === 'outline' || props.variant === 'ghost') return 'secondary'
  if (props.variant === 'contrast') return 'contrast'
  return undefined
})

const primeSize = computed(() => {
  if (props.size === 'lg') return 'large'
  if (props.size === 'sm') return 'small'
  return undefined
})

const classes = computed(() => cn(
  props.iconOnly && 'p-button-icon-only',
  props.class,
))
</script>

<template>
  <PrimeButton
    v-bind="$attrs"
    :disabled="disabled || loading"
    :severity="severity"
    :size="primeSize"
    :text="variant === 'ghost'"
    :outlined="variant === 'outline'"
    :rounded="rounded"
    :link="variant === 'link'"
    :class="classes"
  >
    <slot />
  </PrimeButton>
</template>
