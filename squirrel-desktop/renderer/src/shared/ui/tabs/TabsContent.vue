<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { TabsContent as RekaTabsContent } from 'reka-ui'
import { cn } from '@/shared/lib/utils'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  value: string
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <RekaTabsContent v-bind="$attrs" :value="props.value" :class="cn('sq-tabs__content', props.class)">
    <slot />
  </RekaTabsContent>
</template>
