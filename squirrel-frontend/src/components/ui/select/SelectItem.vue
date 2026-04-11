<script setup lang="ts">
import type { SelectItemProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { Check } from "lucide-vue-next"
import {
  SelectItem,
  SelectItemIndicator,
  SelectItemText,
  useForwardProps,
} from "reka-ui"
import { cn } from "@/lib/utils"

const props = defineProps<SelectItemProps & { class?: HTMLAttributes["class"] }>()

const delegatedProps = reactiveOmit(props, "class")

const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <SelectItem
    v-bind="forwardedProps"
    :class="
      cn(
        'relative flex w-full cursor-pointer select-none items-center py-2.5 pl-6 pr-3 text-[0.7rem] font-medium uppercase tracking-[0.12em] outline-none transition-all duration-300 focus:bg-accent/10 data-[state=checked]:bg-gradient-to-r data-[state=checked]:from-primary/10 data-[state=checked]:to-transparent data-[state=checked]:text-foreground',
        props.class,
      )
    "
  >
    <SelectItemIndicator class="absolute left-0 top-0 bottom-0 w-[2px] bg-primary shadow-[0_0_12px_hsl(var(--primary))]" />

    <SelectItemText>
      <slot />
    </SelectItemText>
  </SelectItem>

</template>
