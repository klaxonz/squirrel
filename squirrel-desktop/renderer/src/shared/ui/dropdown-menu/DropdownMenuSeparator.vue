<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { DropdownMenuSeparator as RekaDropdownMenuSeparator } from 'reka-ui'
import { cn } from '@/shared/lib/utils'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <RekaDropdownMenuSeparator :class="cn('sq-menu__separator', props.class)" />
</template>
