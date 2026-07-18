<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/shared/lib/utils'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  modelValue?: boolean
  class?: HTMLAttributes['class']
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>

<template>
  <button
    v-bind="$attrs"
    type="button"
    role="switch"
    :aria-checked="Boolean(props.modelValue)"
    :disabled="props.disabled"
    :class="cn('sq-switch', props.modelValue && 'is-checked', props.class)"
    @click="emit('update:modelValue', !props.modelValue)"
  >
    <span class="sq-switch__thumb" aria-hidden="true" />
  </button>
</template>
