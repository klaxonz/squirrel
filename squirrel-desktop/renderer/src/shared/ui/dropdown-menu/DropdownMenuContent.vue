<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { DropdownMenuContent as RekaDropdownMenuContent, DropdownMenuPortal } from 'reka-ui'
import { cn } from '@/shared/lib/utils'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  class?: HTMLAttributes['class']
  side?: 'top' | 'right' | 'bottom' | 'left'
  align?: 'start' | 'center' | 'end'
  sideOffset?: number
}>(), {
  side: 'bottom',
  align: 'start',
  sideOffset: 6,
})
</script>

<template>
  <DropdownMenuPortal>
    <RekaDropdownMenuContent
      v-bind="$attrs"
      :side="props.side"
      :align="props.align"
      :side-offset="props.sideOffset"
      :class="cn('sq-menu', props.class)"
    >
      <slot />
    </RekaDropdownMenuContent>
  </DropdownMenuPortal>
</template>
