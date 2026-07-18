<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/shared/lib/utils'
import type { AlertVariant } from '.'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  class?: HTMLAttributes['class']
  variant?: AlertVariant
}>(), {
  variant: 'default',
})
</script>

<template>
  <div
    v-bind="$attrs"
    role="alert"
    :class="cn('sq-alert', `sq-alert--${props.variant}`, props.class)"
  >
    <slot />
  </div>
</template>
