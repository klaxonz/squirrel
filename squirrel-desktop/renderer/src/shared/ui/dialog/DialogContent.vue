<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { inject } from 'vue'
import PrimeDialog from 'primevue/dialog'
import { cn } from '@/shared/lib/utils'
import { dialogContextKey } from './context'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  class?: HTMLAttributes['class']
  contentClass?: HTMLAttributes['class']
}>()

const dialog = inject(dialogContextKey)
if (!dialog) throw new Error('DialogContent must be nested inside Dialog')
</script>

<template>
  <PrimeDialog
    v-bind="$attrs"
    :visible="dialog.open.value"
    modal
    :closable="false"
    :draggable="false"
    :dismissable-mask="true"
    append-to="body"
    :class="cn('app-prime-dialog w-full max-w-lg', props.class)"
    :pt="{ content: { class: cn('app-prime-dialog__content', props.contentClass) } }"
    @update:visible="dialog.setOpen(Boolean($event))"
  >
    <slot />
  </PrimeDialog>
</template>
