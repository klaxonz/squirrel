<script setup lang="ts">
import type { SelectTriggerProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { SelectIcon, SelectTrigger, useForwardProps } from "reka-ui"
import AppIcon from '@/shared/icons/AppIcon.vue'
import { cn } from '@/shared/lib/utils'

const props = defineProps<SelectTriggerProps & { class?: HTMLAttributes["class"] }>()

const delegatedProps = reactiveOmit(props, "class")

const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <SelectTrigger
    v-bind="forwardedProps"
    :class="cn(
      'flex h-9 w-full items-center justify-between gap-2 rounded-md border border-border/65 bg-card/60 px-3 py-2 text-start text-sm font-medium text-foreground shadow-surface transition-[border-color,background-color,box-shadow] duration-fast ease-default hover:border-border/85 hover:bg-card/72 focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/25 disabled:cursor-not-allowed disabled:opacity-40 motion-reduce:transition-none [&>span]:truncate',
      props.class,
    )"
  >
    <slot />
    <SelectIcon as-child>
      <AppIcon name="chevronDown" class="w-3.5 h-3.5 opacity-30 shrink-0" />
    </SelectIcon>
  </SelectTrigger>
</template>
