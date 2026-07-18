<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import {
  DialogContent as RekaDialogContent,
  DialogOverlay,
  DialogPortal,
} from 'reka-ui'
import { cn } from '@/shared/lib/utils'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  class?: HTMLAttributes['class']
  contentClass?: HTMLAttributes['class']
  scrollable?: boolean
}>()
</script>

<template>
  <DialogPortal>
    <DialogOverlay class="sq-dialog-overlay" />
    <RekaDialogContent
      v-bind="$attrs"
      :class="cn('sq-dialog', props.scrollable && 'sq-dialog--scrollable', props.class, props.contentClass)"
    >
      <slot />
    </RekaDialogContent>
  </DialogPortal>
</template>
