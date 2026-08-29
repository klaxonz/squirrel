<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { DropdownMenuItem as RekaDropdownMenuItem } from 'reka-ui'
import { cn } from '@/shared/lib/utils'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  class?: HTMLAttributes['class']
  /** Danger semantic — destructive actions render in the destructive color. */
  danger?: boolean
  disabled?: boolean
}>(), {
  danger: false,
  disabled: false,
})
</script>

<template>
  <RekaDropdownMenuItem
    v-bind="$attrs"
    :disabled="props.disabled"
    :class="cn('sq-menu__item', props.danger && 'sq-menu__item--danger', props.class)"
  >
    <slot />
  </RekaDropdownMenuItem>
</template>
