<script setup lang="ts">
import type { HTMLAttributes, InputHTMLAttributes } from 'vue'
import { cn } from '@/shared/lib/utils'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  modelValue?: string | number | null
  type?: InputHTMLAttributes['type']
  class?: HTMLAttributes['class']
  fluid?: boolean
  size?: 'default' | 'lg'
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function updateValue(event: Event) {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <input
    v-bind="$attrs"
    :type="props.type || 'text'"
    :value="props.modelValue ?? ''"
    :class="cn(
      'sq-input',
      props.fluid && 'sq-input--fluid',
      props.size === 'lg' && 'sq-input--lg',
      props.class,
    )"
    @input="updateValue"
  />
</template>
