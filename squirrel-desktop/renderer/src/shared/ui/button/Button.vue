<script setup lang="ts">
import type { ButtonHTMLAttributes, HTMLAttributes } from 'vue'
import { computed } from 'vue'
import { cn } from '@/shared/lib/utils'
import type { ButtonSize, ButtonVariant } from '.'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  type?: ButtonHTMLAttributes['type']
  variant?: ButtonVariant
  size?: ButtonSize
  class?: HTMLAttributes['class']
  loading?: boolean
  disabled?: boolean
  iconOnly?: boolean
  rounded?: boolean
  fluid?: boolean
}>(), {
  type: 'button',
  variant: 'default',
  size: 'default',
  loading: false,
  disabled: false,
  iconOnly: false,
  rounded: false,
  fluid: false,
})

const classes = computed(() => cn(
  'sq-button',
  `sq-button--${props.variant}`,
  `sq-button--${props.size}`,
  props.iconOnly && 'sq-button--icon-only',
  props.rounded && 'sq-button--rounded',
  props.fluid && 'sq-button--fluid',
  props.loading && 'is-loading',
  props.class,
))
</script>

<template>
  <button
    v-bind="$attrs"
    :type="type"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    :class="classes"
  >
    <span v-if="loading" class="sq-button__spinner" aria-hidden="true" />
    <span class="sq-button__content" :class="{ 'is-hidden': loading && iconOnly }">
      <slot />
    </span>
  </button>
</template>
