<script setup lang="ts">
import type { TabsListProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { TabsList } from "reka-ui"
import { cn } from "@/lib/utils"

const props = defineProps<TabsListProps & { class?: HTMLAttributes["class"] }>()

const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <TabsList
    v-bind="delegatedProps"
    :class="cn(
      'inline-flex min-h-11 items-center justify-center gap-1 rounded-full border border-border/70 bg-card/80 p-1 text-muted-foreground shadow-[0_12px_30px_hsl(var(--surface-shadow))] backdrop-blur-[6px]',
      props.class,
    )"
  >
    <slot />
  </TabsList>
</template>
