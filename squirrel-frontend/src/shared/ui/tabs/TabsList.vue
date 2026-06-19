<script setup lang="ts">
import type { TabsListProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { TabsList } from "reka-ui"
import { cn } from '@/shared/lib/utils'

const props = defineProps<TabsListProps & { class?: HTMLAttributes["class"] }>()

const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <TabsList
    v-bind="delegatedProps"
    :class="cn(
      'inline-flex min-h-8 items-center justify-center gap-0.5 rounded-md border border-border/70 bg-muted/55 p-0.5 text-muted-foreground shadow-sm',
      props.class,
    )"
  >
    <slot />
  </TabsList>
</template>
