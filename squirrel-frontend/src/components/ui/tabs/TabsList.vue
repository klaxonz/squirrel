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
      'inline-flex min-h-9 items-center justify-center gap-1 rounded-lg border border-border/70 bg-muted/55 p-1 text-muted-foreground shadow-sm',
      props.class,
    )"
  >
    <slot />
  </TabsList>
</template>
