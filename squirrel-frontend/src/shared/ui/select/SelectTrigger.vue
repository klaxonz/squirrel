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
      'flex h-9 w-full items-center justify-between gap-2 rounded-lg border border-border/40 bg-background px-3 py-2 text-[13px] font-medium text-foreground transition-all duration-200 hover:bg-accent focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50 [&>span]:truncate text-start',
      props.class,
    )"
  >
    <slot />
    <SelectIcon as-child>
      <AppIcon name="chevronDown" class="w-3.5 h-3.5 opacity-30 shrink-0" />
    </SelectIcon>
  </SelectTrigger>
</template>
