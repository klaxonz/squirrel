<script setup lang="ts">
import type { TabsTriggerProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { TabsTrigger, useForwardProps } from "reka-ui"
import { cn } from '@/shared/lib/utils'

const props = defineProps<TabsTriggerProps & { class?: HTMLAttributes["class"] }>()

const delegatedProps = reactiveOmit(props, "class")

const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <TabsTrigger
    v-bind="forwardedProps"
    :class="cn(
      'inline-flex min-h-7 items-center justify-center whitespace-nowrap rounded-sm px-2.5 py-0.5 text-xs font-medium text-muted-foreground ring-offset-background transition-colors duration-fast ease-default focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/45 focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-40 data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-xs motion-reduce:transition-none',
      props.class,
    )"
  >
    <span class="truncate">
      <slot />
    </span>
  </TabsTrigger>
</template>
