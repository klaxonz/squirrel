<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { TabsTrigger as RekaTabsTrigger } from 'reka-ui'
import { cn } from '@/shared/lib/utils'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  value: string
  disabled?: boolean
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <RekaTabsTrigger
    v-bind="$attrs"
    :value="props.value"
    :disabled="props.disabled"
    :class="cn('sq-tabs__trigger', props.class)"
  >
    <slot />
  </RekaTabsTrigger>
</template>
