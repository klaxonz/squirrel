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
      class="fixed inset-0 z-[100] bg-black/60 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 duration-200"
    />
    <div class="fixed inset-0 z-[100] grid place-items-center p-4 pointer-events-none">
      <DialogContent
        v-bind="forwarded"
        :class="cn(
          'pointer-events-auto w-full max-w-[380px] bg-background border border-border/20 rounded-xl shadow-[0_24px_48px_-12px_rgba(0,0,0,0.5)] outline-none overflow-hidden',
          'data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-98 data-[state=open]:zoom-in-100 duration-150 ease-out',
          props.class,
        )"
      >
        <slot />
      </DialogContent>
    </div>
  </DialogPortal>
</template>
