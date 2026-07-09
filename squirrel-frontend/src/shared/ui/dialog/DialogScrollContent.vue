<script setup lang="ts">
import type { DialogContentEmits, DialogContentProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import {
  DialogClose,
  DialogContent,
  DialogOverlay,
  DialogPortal,
  useForwardPropsEmits,
} from "reka-ui"
import AppIcon from '@/shared/icons/AppIcon.vue'
import { cn } from '@/shared/lib/utils'

const props = defineProps<DialogContentProps & { class?: HTMLAttributes["class"] }>()
const emits = defineEmits<DialogContentEmits>()

const delegatedProps = reactiveOmit(props, "class")

const forwarded = useForwardPropsEmits(delegatedProps, emits)

type PointerDownOutsideEvent = CustomEvent<{ originalEvent: PointerEvent }>

const handlePointerDownOutside = (event: PointerDownOutsideEvent) => {
  const originalEvent = event.detail.originalEvent
  const target = originalEvent.target as HTMLElement
  if (originalEvent.offsetX > target.clientWidth || originalEvent.offsetY > target.clientHeight) {
    event.preventDefault()
  }
}
</script>

<template>
  <DialogPortal>
    <DialogOverlay
      class="fixed inset-0 z-dialog grid place-items-center overflow-y-auto bg-overlay-strong data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 duration-base ease-out"
    >
      <DialogContent
        :class="
          cn(
            'relative z-dialog my-8 grid w-full max-w-lg gap-4 rounded-lg border border-border/80 bg-card p-6 shadow-dialog duration-base ease-out md:w-full',
            props.class,
          )
        "
        v-bind="forwarded"
        @pointer-down-outside="handlePointerDownOutside"
      >
        <slot />

        <DialogClose
          class="absolute top-4 right-4 rounded-md p-0.5 transition-colors duration-fast ease-default hover:bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/45"
        >
          <AppIcon name="close" class="w-4 h-4" />
          <span class="sr-only">关闭</span>
        </DialogClose>
      </DialogContent>
    </DialogOverlay>
  </DialogPortal>
</template>
