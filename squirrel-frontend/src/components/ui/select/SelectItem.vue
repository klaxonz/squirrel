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
        'relative flex w-full cursor-pointer select-none items-center py-2 px-3 rounded-md text-[13px] font-medium text-muted-foreground outline-none transition-all duration-200 focus:bg-accent focus:text-foreground data-[state=checked]:text-foreground data-[state=checked]:font-bold',
        props.class,
      )
    "
  >
    <SelectItemText>
      <slot />
    </SelectItemText>

    <SelectItemIndicator class="absolute right-3 flex items-center justify-center">
      <Check class="w-3.5 h-3.5" stroke-width="3" />
    </SelectItemIndicator>
  </SelectItem>

</template>
