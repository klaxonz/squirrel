<script setup lang="ts">
import type { ButtonHTMLAttributes, HTMLAttributes } from 'vue'
import { computed } from 'vue'
import { cn } from '@/shared/lib/utils'
import type { ButtonSize, ButtonVariant } from '.'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  type?: ButtonHTMLAttributes['type']
  variant?: ButtonVariant
  severity?: 'secondary' | 'danger' | 'contrast' | 'help' | 'info' | 'success' | 'warn'
  size?: ButtonSize
  class?: HTMLAttributes['class']
  loading?: boolean
  disabled?: boolean
  iconOnly?: boolean
  rounded?: boolean
  text?: boolean
  outlined?: boolean
  link?: boolean
  fluid?: boolean
}>(), {
  type: 'button',
  variant: 'default',
  size: 'default',
  loading: false,
  disabled: false,
  iconOnly: false,
  rounded: false,
  text: false,
  outlined: false,
  link: false,
  fluid: false,
})

const resolvedVariant = computed<ButtonVariant>(() => {
  if (props.link) return 'link'
  if (props.text) return 'ghost'
  if (props.outlined) return 'outline'
  if (props.severity === 'danger') return 'destructive'
  if (props.severity === 'secondary') return 'secondary'
  if (props.severity === 'contrast') return 'contrast'
  return props.variant
})

const classes = computed(() => cn(
  'sq-button',
  `sq-button--${resolvedVariant.value}`,
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
