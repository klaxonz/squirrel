<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/shared/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <div
    :class="
      cn(
        'rounded-lg border border-border/60 bg-card/72 text-card-foreground shadow-[0_1px_0_hsl(var(--foreground)/0.04)_inset]',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
