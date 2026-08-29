<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { TooltipContent as RekaTooltipContent, TooltipPortal } from 'reka-ui'
import { cn } from '@/shared/lib/utils'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  class?: HTMLAttributes['class']
  side?: 'top' | 'right' | 'bottom' | 'left'
  sideOffset?: number
}>(), {
  side: 'top',
  sideOffset: 6,
})
</script>

<template>
  <TooltipPortal>
    <RekaTooltipContent
      v-bind="$attrs"
      :side="props.side"
      :side-offset="props.sideOffset"
      :class="cn('sq-tooltip', props.class)"
    >
      <slot />
    </RekaTooltipContent>
  </TooltipPortal>
</template>
