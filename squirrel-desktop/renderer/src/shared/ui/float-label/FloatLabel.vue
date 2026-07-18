<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/shared/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
  variant?: string
}>()
</script>

<template>
  <div :class="cn('sq-float-label', props.class)"><slot /></div>
</template>
