<script setup lang="ts">
import type { HTMLAttributes } from "vue"
import { cn } from "@/lib/utils"

const props = defineProps<{
  class?: HTMLAttributes["class"]
}>()
</script>

<template>
  <tr :class="cn('border-b transition-colors hover:bg-muted/30 data-[state=selected]:bg-muted/50', props.class)">
    <slot />
  </tr>
</template>
