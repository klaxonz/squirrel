<script setup lang="ts">
import type { SelectItemProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import {
  SelectItem,
  SelectItemIndicator,
  SelectItemText,
  useForwardProps,
} from "reka-ui"
import AppIcon from '@/shared/icons/AppIcon.vue'
import { cn } from '@/shared/lib/utils'

const props = defineProps<SelectItemProps & { class?: HTMLAttributes["class"] }>()

const delegatedProps = reactiveOmit(props, "class")

const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <SelectItem
    v-bind="forwardedProps"
    :class="
      cn(
        'relative flex w-full cursor-pointer select-none items-center rounded-md py-2 pl-3 pr-8 text-sm font-medium text-muted-foreground outline-none transition-colors duration-fast ease-default focus:bg-accent focus:text-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-40 data-[state=checked]:font-semibold data-[state=checked]:text-foreground',
        props.class,
      )
    "
  >
    <SelectItemText>
      <slot />
    </SelectItemText>

    <SelectItemIndicator class="absolute right-3 flex items-center justify-center">
      <AppIcon name="check" class="w-3.5 h-3.5" :stroke-width="3" />
    </SelectItemIndicator>
  </SelectItem>

</template>
