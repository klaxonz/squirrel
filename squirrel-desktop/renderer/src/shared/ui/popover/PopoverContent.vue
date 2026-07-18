<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { PopoverContent as RekaPopoverContent, PopoverPortal } from 'reka-ui'
import { cn } from '@/shared/lib/utils'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  class?: HTMLAttributes['class']
  side?: 'top' | 'right' | 'bottom' | 'left'
  align?: 'start' | 'center' | 'end'
  sideOffset?: number
}>(), {
  side: 'bottom',
  align: 'end',
  sideOffset: 8,
})
</script>

<template>
  <PopoverPortal>
    <RekaPopoverContent
      v-bind="$attrs"
      :side="props.side"
      :align="props.align"
      :side-offset="props.sideOffset"
      :class="cn('sq-popover', props.class)"
    >
      <slot />
    </RekaPopoverContent>
  </PopoverPortal>
</template>
