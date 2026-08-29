<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { TabsList as RekaTabsList } from 'reka-ui'
import { cn } from '@/shared/lib/utils'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <RekaTabsList v-bind="$attrs" :class="cn('sq-tabs__list', props.class)">
    <slot />
  </RekaTabsList>
</template>
