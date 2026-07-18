<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/shared/lib/utils'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  modelValue?: boolean
  class?: HTMLAttributes['class']
  binary?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>

<template>
  <span :class="cn('sq-checkbox', props.class)">
    <input
      v-bind="$attrs"
      class="sq-checkbox__input"
      type="checkbox"
      :checked="Boolean(props.modelValue)"
      @change="emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
    />
    <span class="sq-checkbox__box" aria-hidden="true">
      <svg viewBox="0 0 16 16" fill="none"><path d="m3.5 8 3 3 6-6" /></svg>
    </span>
  </span>
</template>
