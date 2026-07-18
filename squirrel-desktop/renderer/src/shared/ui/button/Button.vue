<script setup lang="ts">
import type { Component, HTMLAttributes } from 'vue'
import { computed } from 'vue'
import PrimeButton from 'primevue/button'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import { cn } from '@/shared/lib/utils'
import type { ButtonSize, ButtonVariant } from '.'

const props = withDefaults(defineProps<{
  variant?: ButtonVariant
  size?: ButtonSize
  class?: HTMLAttributes['class']
  loading?: boolean
  disabled?: boolean
  unstyled?: boolean
  as?: string | Component
  asChild?: boolean
}>(), {
  variant: 'default',
  size: 'default',
  loading: false,
  disabled: false,
  unstyled: false,
  as: 'button',
  asChild: false,
})

const severity = computed(() => {
  if (props.variant === 'destructive') return 'danger'
  if (props.variant === 'secondary' || props.variant === 'outline' || props.variant === 'ghost') return 'secondary'
  if (props.variant === 'contrast') return 'contrast'
  return undefined
})

const primeSize = computed(() => {
  if (props.size === 'lg') return 'large'
  if (props.size === 'xs' || props.size === 'sm') return 'small'
  return undefined
})

const classes = computed(() => cn(
  `app-prime-button--${props.size}`,
  `app-prime-button--${props.variant}`,
  props.unstyled && 'app-prime-button--unstyled',
  props.class,
))
</script>

<template>
  <component
    :is="as"
    v-if="unstyled"
    v-bind="$attrs"
    :disabled="disabled || loading"
    :class="classes"
  >
    <AppSpinner v-if="loading" size="sm" />
    <slot />
  </component>

  <PrimeButton
    v-else
    v-bind="$attrs"
    :as="as"
    :as-child="asChild"
    :disabled="disabled || loading"
    :severity="severity"
    :size="primeSize"
    :text="variant === 'ghost'"
    :outlined="variant === 'outline' || variant === 'player'"
    :rounded="variant === 'player' || size === 'player-sm' || size === 'player-lg'"
    :link="variant === 'link'"
    :class="classes"
  >
    <AppSpinner v-if="loading" size="sm" />
    <slot />
  </PrimeButton>
</template>
