<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/shared/lib/utils'
import type { BadgeVariant } from '.'

const props = withDefaults(defineProps<{
  variant?: BadgeVariant
  class?: HTMLAttributes['class']
}>(), {
  variant: 'default',
})
</script>

<template>
  <span :class="cn('sq-badge', `sq-badge--${props.variant}`, props.class)"><slot /></span>
</template>
