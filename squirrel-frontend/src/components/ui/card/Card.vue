<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <div
    :class="
      cn(
        'rounded-[calc(var(--radius-2xl)-2px)] border border-border/75 bg-card/92 text-card-foreground shadow-[0_20px_46px_hsl(var(--surface-shadow))] backdrop-blur-[6px]',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
