<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/shared/lib/utils'
import Button from './Button.vue'
import type { ButtonSize, ButtonVariant } from '.'

/**
 * Icon-only button. Thin policy wrapper over Button: forces the square
 * icon-only shape and requires an accessible `label` (icon-only buttons have
 * no text content for screen readers or tooltips).
 */
defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  /** Accessible name, rendered as aria-label + title. */
  label: string
  variant?: ButtonVariant
  size?: ButtonSize
  class?: HTMLAttributes['class']
  loading?: boolean
  disabled?: boolean
}>(), {
  variant: 'ghost',
  size: 'default',
})
</script>

<template>
  <Button
    v-bind="$attrs"
    :variant="props.variant"
    :size="props.size"
    icon-only
    :loading="props.loading"
    :disabled="props.disabled"
    :aria-label="props.label"
    :title="props.label"
    :class="cn(props.class)"
  >
    <slot />
  </Button>
</template>
