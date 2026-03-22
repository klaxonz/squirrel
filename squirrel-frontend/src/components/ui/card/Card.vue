<script setup lang="ts">
import type { HTMLAttributes } from "vue"
import { cn } from "@/lib/utils"

const props = defineProps<{
  class?: HTMLAttributes["class"]
}>()
</script>

<template>
  <div
    :class="
      cn(
        'rounded-[calc(var(--radius-xl)+2px)] border bg-card text-card-foreground shadow-md backdrop-blur-[1px]',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
