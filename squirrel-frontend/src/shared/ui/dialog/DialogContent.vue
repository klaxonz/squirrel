<script setup lang="ts">
import type { DialogContentEmits, DialogContentProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import {
  DialogContent,
  DialogOverlay,
  DialogPortal,
  useForwardPropsEmits,
} from "reka-ui"
import { cn } from '@/shared/lib/utils'

const props = defineProps<DialogContentProps & { class?: HTMLAttributes["class"] }>()
const emits = defineEmits<DialogContentEmits>()

const delegatedProps = reactiveOmit(props, "class")
const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <DialogPortal>
    <DialogOverlay
      class="fixed inset-0 z-dialog bg-overlay-strong data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 duration-base ease-out"
    />
    <div class="fixed inset-0 z-dialog grid place-items-center p-4 pointer-events-none">
      <DialogContent
        v-bind="forwarded"
        :class="cn(
          'pointer-events-auto w-full max-w-[380px] overflow-hidden rounded-lg border border-border/80 bg-card shadow-dialog outline-none',
          'data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 duration-base ease-out',
          props.class,
        )"
      >
        <slot />
      </DialogContent>
    </div>
  </DialogPortal>
</template>
